"""Bwana chat orchestration — FAQ, escalation, LLM, optional n8n webhook."""
import asyncio
import hashlib
import logging
import time
from typing import Any, Literal

import httpx
from openai import APIError, AuthenticationError, OpenAI, RateLimitError
from supabase import Client

from app.core.config import get_settings
from app.schemas.db_enums import CacheType, validate_cache_type
from app.lib.retry import DEGRADED_LLM_USER_MESSAGE, circuit_is_open
from app.services.bwana_faq import is_escalation_request, match_faq
from app.services.llm import FEATURE_BWANA, LlmLogContext
from app.services.openrouter_helpers import (
    create_chat_completion_with_retries,
    get_completion_content,
)
from app.services.whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)

BwanaSource = Literal["faq", "llm", "escalated"]

BWANA_SYSTEM_PROMPT = """You are Bwana, ZedApply's AI career assistant for Zambian professionals.
You know the platform: matching algorithm (60% semantic + 30% skills + 10% bonus),
tiers (Free 10/mo, Starter K125 50/mo, Professional K250 125/mo, Super Standard K500 unlimited),
Lenco payments via MTN/Airtel, WhatsApp digest at 07:00, etc.
You can help with career questions, CV tips, interview prep.
Keep responses under 150 words. Suggest paid features (Tailored CV, Cover Letter) where relevant."""

_ESCALATION_USER_REPLY = (
    "I've flagged this for Kaluba — he'll WhatsApp you within 24h."
)


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


async def _call_openrouter_llm(
    message: str,
    history: list[dict[str, str]],
    *,
    user_id: str | None = None,
    supabase: Client | None = None,
) -> str:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("Bwana AI is temporarily unavailable. Try a FAQ question.")
    if circuit_is_open():
        return DEGRADED_LLM_USER_MESSAGE

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": BWANA_SYSTEM_PROMPT},
    ]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": message})

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


async def _notify_kaluba_escalation(user_id: str, message: str) -> None:
    settings = get_settings()
    phone = (settings.bwana_escalation_phone or "").strip() or settings.admin_alert_phone
    text = f"Bwana escalation from user {user_id}: {message[:500]}"
    try:
        await send_whatsapp_message(phone, text)
    except Exception as exc:
        logger.warning("Bwana escalation WAHA failed: %s", exc)


async def process_bwana_message(
    *,
    user_id: str,
    message: str,
    session_id: str,
    supabase: Client,
    history: list[dict[str, str]] | None = None,
) -> tuple[str, BwanaSource]:
    """Run FAQ → escalate → LLM pipeline (in-process)."""
    text = message.strip()
    if not text:
        raise ValueError("Message cannot be empty")

    faq = match_faq(text)
    if faq:
        return faq.response, "faq"

    if is_escalation_request(text):
        await _notify_kaluba_escalation(user_id, text)
        return _ESCALATION_USER_REPLY, "escalated"

    hist = history if history is not None else load_conversation_history(
        supabase, user_id, session_id
    )
    reply = await _call_openrouter_llm(
        text, hist, user_id=user_id, supabase=supabase
    )
    return reply, "llm"


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
) -> tuple[str, BwanaSource, int]:
    """Full handler: pipeline + ai_cache persistence."""
    started = time.perf_counter()
    history = load_conversation_history(supabase, user_id, session_id)
    settings = get_settings()

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
        except Exception as exc:
            logger.warning("n8n Bwana webhook failed, local fallback: %s", exc)
            response, source = await process_bwana_message(
                user_id=user_id,
                message=message,
                session_id=session_id,
                supabase=supabase,
                history=history,
            )
    else:
        response, source = await process_bwana_message(
            user_id=user_id,
            message=message,
            session_id=session_id,
            supabase=supabase,
            history=history,
        )

    append_and_persist_history(
        supabase,
        user_id=user_id,
        session_id=session_id,
        user_message=message,
        assistant_message=response,
        source=source,  # type: ignore[arg-type]
    )
    took_ms = int((time.perf_counter() - started) * 1000)
    return response, source, took_ms  # type: ignore[return-value]
