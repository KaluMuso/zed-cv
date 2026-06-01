"""Bwana chat orchestration — FAQ, escalation, LLM, optional n8n webhook."""
import asyncio
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass
from html import escape
from typing import Any, Literal

import httpx
from openai import APIError, AuthenticationError, OpenAI, RateLimitError
from supabase import Client

from app.core.config import get_settings
from app.schemas.bwana_config import BwanaConfig, BwanaEscalationReason
from app.schemas.db_enums import CacheType, validate_cache_type
from app.lib.retry import DEGRADED_LLM_USER_MESSAGE, circuit_is_open
from app.services.bwana_config import (
    build_bwana_system_prompt,
    get_bwana_config,
    render_template,
)
from app.services.bwana_faq import (
    is_contact_admin_request,
    is_escalation_request,
    is_unsatisfied_request,
    match_faq,
    wants_callback,
)
from app.services.bwana_faq_custom import match_custom_faq
from app.services.email import _send
from app.services.llm import FEATURE_BWANA, LlmLogContext
from app.services.openrouter_helpers import (
    create_chat_completion_with_retries,
    get_completion_content,
)
from app.services.prompt_safety import wrap_user_content
from app.services.whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)

BwanaSource = Literal["faq", "llm", "escalated"]


@dataclass(frozen=True)
class BwanaTurnResult:
    response: str
    source: BwanaSource
    intent_id: str | None = None
    escalation_ticket_id: str | None = None


def _new_escalation_ticket_id() -> str:
    return f"ZD-{uuid.uuid4().hex[:8].upper()}"


def session_cache_key(user_id: str, session_id: str) -> str:
    raw = f"bwana:{user_id}:{session_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def load_conversation_history(
    supabase: Client, user_id: str, session_id: str
) -> list[dict[str, str]]:
    key = session_cache_key(user_id, session_id)
    row = (
        supabase.table("ai_cache")
        .select("result")
        .eq("cache_key", key)
        .eq("cache_type", CacheType.bwana_chat.value)
        .limit(1)
        .execute()
    )
    if not row.data:
        return []
    messages = row.data[0].get("result", {}).get("messages", [])
    if not isinstance(messages, list):
        return []
    out: list[dict[str, str]] = []
    for m in messages[-10:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
            out.append(
                {
                    "role": m["role"],
                    "content": str(m.get("content", ""))[:4000],
                }
            )
    return out[-5:]


def append_and_persist_history(
    supabase: Client,
    *,
    user_id: str,
    session_id: str,
    user_message: str,
    assistant_message: str,
    source: BwanaSource,
) -> None:
    key = session_cache_key(user_id, session_id)
    existing = load_conversation_history(supabase, user_id, session_id)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    transcript = existing + [
        {"role": "user", "content": user_message, "ts": stamp},
        {
            "role": "assistant",
            "content": assistant_message,
            "source": source,
            "ts": stamp,
        },
    ]
    payload = {
        "session_id": session_id,
        "user_id": user_id,
        "messages": transcript[-20:],
    }
    cache_type = validate_cache_type(CacheType.bwana_chat.value)
    row = (
        supabase.table("ai_cache")
        .select("id")
        .eq("cache_key", key)
        .limit(1)
        .execute()
    )
    record = {
        "cache_key": key,
        "cache_type": cache_type,
        "input_hash": hashlib.sha256(
            (user_id + session_id + user_message).encode()
        ).hexdigest(),
        "result": payload,
        "model": "bwana_chat",
    }
    if row.data:
        supabase.table("ai_cache").update({"result": payload}).eq(
            "cache_key", key
        ).execute()
    else:
        supabase.table("ai_cache").insert(record).execute()


def _log_escalation(
    supabase: Client,
    *,
    ticket_id: str,
    user_id: str,
    session_id: str,
    message: str,
    reason: BwanaEscalationReason,
    channels: list[str],
) -> None:
    try:
        supabase.table("bwana_escalation_log").insert(
            {
                "ticket_id": ticket_id,
                "user_id": user_id,
                "session_id": session_id,
                "message_excerpt": message[:500],
                "reason": reason,
                "channels": channels,
            }
        ).execute()
    except Exception as exc:
        logger.warning("bwana_escalation_log insert failed: %s", exc)


def _fetch_user_email(supabase: Client, user_id: str) -> str | None:
    try:
        row = (
            supabase.table("users")
            .select("email")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if not row.data:
            return None
        email = row.data[0].get("email")
        if not email or not str(email).strip():
            return None
        return str(email).strip().lower()
    except Exception as exc:
        logger.warning("bwana user email lookup failed: %s", exc)
        return None


async def _send_user_escalation_ack(
    config: BwanaConfig,
    *,
    ticket_id: str,
    user_email: str,
) -> bool:
    if not config.enable_user_escalation_ack:
        return False
    subject = f"ZedApply support — reference {ticket_id}"
    body = render_template(config.user_escalation_ack_template, config, ticket_id=ticket_id)
    html = f"<p>{escape(body)}</p>"
    idem = f"bwana-user-ack-{ticket_id}"
    return _send(user_email, subject, html, idempotency_key=idem)


async def _send_escalation_email(
    config: BwanaConfig,
    *,
    ticket_id: str,
    user_id: str,
    message: str,
    reason: BwanaEscalationReason,
) -> bool:
    if not config.enable_email_escalation:
        return False
    subject = f"[Bwana {ticket_id}] {reason} — user {user_id[:8]}…"
    html = (
        f"<p>Bwana escalation <b>{escape(ticket_id)}</b> (<b>{escape(reason)}</b>)</p>"
        f"<p>User ID: <code>{escape(user_id)}</code></p>"
        f"<p>Message excerpt:</p><pre>{escape(message[:500])}</pre>"
    )
    idem = f"bwana-esc-{ticket_id}"
    return _send(config.support_email, subject, html, idempotency_key=idem)


async def _notify_escalation(
    supabase: Client,
    config: BwanaConfig,
    *,
    user_id: str,
    session_id: str,
    message: str,
    reason: BwanaEscalationReason,
    notify_whatsapp: bool = True,
) -> tuple[str, list[str]]:
    """WAHA + optional email + audit log. Returns (ticket_id, channels used)."""
    ticket_id = _new_escalation_ticket_id()
    channels: list[str] = []
    phone = config.escalation_whatsapp_phone.strip()
    if notify_whatsapp and phone:
        text = (
            f"Bwana {ticket_id} [{reason}] from user {user_id}: {message[:480]}"
        )
        try:
            await send_whatsapp_message(phone, text)
            channels.append("whatsapp")
        except Exception as exc:
            logger.warning("Bwana escalation WAHA failed: %s", exc)

    if await _send_escalation_email(
        config,
        ticket_id=ticket_id,
        user_id=user_id,
        message=message,
        reason=reason,
    ):
        channels.append("email")

    user_email = _fetch_user_email(supabase, user_id)
    if user_email and await _send_user_escalation_ack(
        config, ticket_id=ticket_id, user_email=user_email
    ):
        channels.append("user_email")

    _log_escalation(
        supabase,
        ticket_id=ticket_id,
        user_id=user_id,
        session_id=session_id,
        message=message,
        reason=reason,
        channels=channels,
    )
    return ticket_id, channels


def _escalation_reply(
    config: BwanaConfig,
    reason: BwanaEscalationReason,
    *,
    ticket_id: str | None = None,
) -> str:
    if reason == "unsatisfied":
        tpl = config.unsatisfied_reply_template
    elif reason == "contact_admin":
        tpl = config.contact_admin_reply_template
    else:
        tpl = config.human_escalation_reply_template
    return render_template(tpl, config, ticket_id=ticket_id)


def _log_chat_event(
    supabase: Client,
    *,
    user_id: str,
    session_id: str,
    source: BwanaSource,
    intent_id: str | None,
) -> None:
    try:
        supabase.table("bwana_event_log").insert(
            {
                "user_id": user_id,
                "session_id": session_id,
                "source": source,
                "intent_id": intent_id,
            }
        ).execute()
    except Exception as exc:
        logger.warning("bwana_event_log insert failed: %s", exc)


async def _call_openrouter_llm(
    message: str,
    history: list[dict[str, str]],
    *,
    user_id: str | None = None,
    supabase: Client | None = None,
    config: BwanaConfig | None = None,
) -> str:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("Bwana AI is temporarily unavailable. Try a FAQ question.")
    if circuit_is_open():
        return DEGRADED_LLM_USER_MESSAGE

    if supabase is None or config is None:
        raise ValueError("Bwana config required for LLM")

    system_prompt = await build_bwana_system_prompt(config, supabase)
    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
    ]
    for turn in history:
        messages.append(
            {
                "role": turn["role"],
                "content": wrap_user_content(turn["content"]),
            }
        )
    messages.append({"role": "user", "content": wrap_user_content(message)})

    def _sync_call() -> str:
        try:
            response = create_chat_completion_with_retries(
                client,
                log_prefix="bwana_chat",
                log_context=LlmLogContext(
                    feature=FEATURE_BWANA,
                    route="POST /api/v1/bwana/chat",
                    user_id=user_id,
                ),
                supabase=supabase,
                model=settings.llm_model,
                max_tokens=400,
                messages=messages,
            )
            content = get_completion_content(response, default="")
            if not content or not str(content).strip():
                raise ValueError("Empty response from Bwana AI")
            return str(content).strip()
        except AuthenticationError:
            logger.error("OpenRouter key invalid for Bwana chat")
            raise ValueError("Bwana AI is not configured.")
        except RateLimitError:
            logger.warning("OpenRouter rate limit for Bwana chat")
            raise ValueError("Bwana is busy — please try again in a minute.")
        except APIError as exc:
            logger.error("OpenRouter error for Bwana: %s", exc)
            raise ValueError("Bwana AI is temporarily unavailable.")

    return await asyncio.to_thread(_sync_call)


async def process_bwana_message(
    *,
    user_id: str,
    message: str,
    session_id: str,
    supabase: Client,
    history: list[dict[str, str]] | None = None,
) -> BwanaTurnResult:
    """Run FAQ → escalate → LLM pipeline (in-process)."""
    text = message.strip()
    if not text:
        raise ValueError("Message cannot be empty")

    config = get_bwana_config(supabase)

    faq = match_faq(text)
    if faq:
        return BwanaTurnResult(faq.response, "faq", intent_id=faq.intent_id)

    custom = match_custom_faq(text, config.faq_intents_json)
    if custom:
        return BwanaTurnResult(custom.response, "faq", intent_id=custom.intent_id)

    if is_contact_admin_request(text):
        if wants_callback(text):
            ticket_id, _ = await _notify_escalation(
                supabase,
                config,
                user_id=user_id,
                session_id=session_id,
                message=text,
                reason="contact_admin",
            )
            reply = _escalation_reply(
                config, "contact_admin", ticket_id=ticket_id
            )
            return BwanaTurnResult(
                reply, "escalated", escalation_ticket_id=ticket_id
            )
        reply = _escalation_reply(config, "contact_admin")
        return BwanaTurnResult(reply, "faq", intent_id="contact_admin")

    if is_unsatisfied_request(text):
        ticket_id, _ = await _notify_escalation(
            supabase,
            config,
            user_id=user_id,
            session_id=session_id,
            message=text,
            reason="unsatisfied",
        )
        return BwanaTurnResult(
            _escalation_reply(config, "unsatisfied", ticket_id=ticket_id),
            "escalated",
            escalation_ticket_id=ticket_id,
        )

    if is_escalation_request(text):
        ticket_id, _ = await _notify_escalation(
            supabase,
            config,
            user_id=user_id,
            session_id=session_id,
            message=text,
            reason="human_request",
        )
        return BwanaTurnResult(
            _escalation_reply(config, "human_request", ticket_id=ticket_id),
            "escalated",
            escalation_ticket_id=ticket_id,
        )

    hist = history if history is not None else load_conversation_history(
        supabase, user_id, session_id
    )
    reply = await _call_openrouter_llm(
        text, hist, user_id=user_id, supabase=supabase, config=config
    )
    return BwanaTurnResult(reply, "llm")


async def call_n8n_bwana_webhook(
    *,
    user_id: str,
    message: str,
    session_id: str,
    history: list[dict[str, str]],
) -> dict[str, Any]:
    """POST to n8n ZedApply - Bwana Chat Pipeline webhook."""
    settings = get_settings()
    url = (settings.bwana_n8n_webhook_url or "").strip()
    if not url:
        raise ValueError("BWANA_N8N_WEBHOOK_URL is not configured")

    payload = {
        "user_id": user_id,
        "message": message,
        "session_id": session_id,
        "history": history,
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError("Invalid Bwana pipeline response")
    return data


async def handle_bwana_chat(
    *,
    user_id: str,
    message: str,
    session_id: str,
    supabase: Client,
) -> tuple[str, BwanaSource, int, str | None, str | None]:
    """Full handler: pipeline + ai_cache persistence. Returns ticket_id if escalated."""
    started = time.perf_counter()
    history = load_conversation_history(supabase, user_id, session_id)
    settings = get_settings()
    turn: BwanaTurnResult

    if settings.bwana_n8n_webhook_url:
        try:
            data = await call_n8n_bwana_webhook(
                user_id=user_id,
                message=message,
                session_id=session_id,
                history=history,
            )
            response = str(data.get("response", "")).strip()
            source = data.get("source", "llm")
            if source not in ("faq", "llm", "escalated"):
                source = "llm"
            if not response:
                raise ValueError("Empty Bwana pipeline response")
            turn = BwanaTurnResult(
                response,
                source,  # type: ignore[arg-type]
                intent_id=str(data.get("intent_id") or "") or None,
                escalation_ticket_id=str(data.get("escalation_ticket_id") or "")
                or None,
            )
        except Exception as exc:
            logger.warning("n8n Bwana webhook failed, local fallback: %s", exc)
            turn = await process_bwana_message(
                user_id=user_id,
                message=message,
                session_id=session_id,
                supabase=supabase,
                history=history,
            )
    else:
        turn = await process_bwana_message(
            user_id=user_id,
            message=message,
            session_id=session_id,
            supabase=supabase,
            history=history,
        )

    _log_chat_event(
        supabase,
        user_id=user_id,
        session_id=session_id,
        source=turn.source,
        intent_id=turn.intent_id,
    )

    append_and_persist_history(
        supabase,
        user_id=user_id,
        session_id=session_id,
        user_message=message,
        assistant_message=turn.response,
        source=turn.source,
    )
    took_ms = int((time.perf_counter() - started) * 1000)
    return (
        turn.response,
        turn.source,
        took_ms,
        turn.escalation_ticket_id,
        turn.intent_id,
    )


async def send_test_escalation_whatsapp(supabase: Client) -> None:
    """Admin smoke: ping escalation WhatsApp with a test message."""
    config = get_bwana_config(supabase, force=True)
    test_id = str(uuid.uuid4())[:8]
    await send_whatsapp_message(
        config.escalation_whatsapp_phone,
        f"Bwana test escalation (admin) — id {test_id}",
    )
