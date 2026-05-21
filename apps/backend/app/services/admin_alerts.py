"""Admin WhatsApp alerts for operational queues (review backlog, etc.)."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.core.config import Settings, get_settings
from app.schemas.db_enums import CacheType, validate_cache_type

logger = logging.getLogger(__name__)

REVIEW_QUEUE_THRESHOLDS: tuple[int, ...] = (10, 25, 50, 100)
REVIEW_QUEUE_CACHE_KEY = "admin_alerts:review_queue_last_count"
REVIEW_JOBS_ADMIN_URL = "https://www.zedapply.com/admin/review-jobs"
DEFAULT_ADMIN_CHAT_ID = "260761359005@c.us"


def _admin_chat_id(settings: Settings) -> str:
    phone = (settings.admin_alert_phone or "+260761359005").strip()
    digits = phone.lstrip("+").replace(" ", "")
    return f"{digits}@c.us"


def threshold_for_review_count(count: int) -> Optional[int]:
    """Highest crossed threshold, or None when count is below 10."""
    if count < REVIEW_QUEUE_THRESHOLDS[0]:
        return None
    crossed = REVIEW_QUEUE_THRESHOLDS[0]
    for value in REVIEW_QUEUE_THRESHOLDS:
        if count >= value:
            crossed = value
    return crossed


def _format_alert_timestamp(iso_value: str | None) -> str:
    if not iso_value:
        return "never"
    try:
        parsed = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso_value


def build_review_queue_alert_message(
    *,
    current_count: int,
    previous_alert_at: str | None,
    previous_alert_count: int | None,
) -> str:
    lines = [
        "ZedApply Admin Alert",
        f"Review queue has {current_count} jobs needing attention.",
        f"Visit: {REVIEW_JOBS_ADMIN_URL}",
    ]
    if previous_alert_at or previous_alert_count is not None:
        prev_count = previous_alert_count if previous_alert_count is not None else "?"
        lines.append(
            "Last alert: "
            f"{_format_alert_timestamp(previous_alert_at)} ({prev_count} jobs)"
        )
    return "\n".join(lines)


async def send_admin_whatsapp(text: str, settings: Settings | None = None) -> dict:
    """POST a plain-text message to the admin WhatsApp via WAHA."""
    cfg = settings or get_settings()
    if not cfg.waha_api_url:
        raise RuntimeError("WAHA_API_URL is not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{cfg.waha_api_url.rstrip('/')}/api/sendText",
            json={
                "chatId": _admin_chat_id(cfg),
                "text": text,
                "session": cfg.waha_session_name,
            },
            headers={"X-Api-Key": cfg.waha_api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


def _load_review_queue_state(supabase) -> dict[str, Any]:
    try:
        rows = (
            supabase.table("ai_cache")
            .select("result")
            .eq("cache_key", REVIEW_QUEUE_CACHE_KEY)
            .limit(1)
            .execute()
        )
        if rows.data:
            result = rows.data[0].get("result")
            if isinstance(result, dict):
                return result
    except Exception:
        logger.warning("admin_alerts: failed to read ai_cache state", exc_info=True)
    return {}


def _save_review_queue_state(supabase, state: dict[str, Any]) -> None:
    payload = {
        "cache_key": REVIEW_QUEUE_CACHE_KEY,
        "cache_type": validate_cache_type(CacheType.admin_alert.value),
        "input_hash": hashlib.sha256(REVIEW_QUEUE_CACHE_KEY.encode()).hexdigest(),
        "result": state,
        "model": "system",
    }
    try:
        existing = (
            supabase.table("ai_cache")
            .select("id")
            .eq("cache_key", REVIEW_QUEUE_CACHE_KEY)
            .limit(1)
            .execute()
        )
        if existing.data:
            supabase.table("ai_cache").update({"result": state}).eq(
                "cache_key", REVIEW_QUEUE_CACHE_KEY
            ).execute()
        else:
            supabase.table("ai_cache").insert(payload).execute()
    except Exception:
        logger.warning("admin_alerts: failed to persist ai_cache state", exc_info=True)


async def count_review_required_jobs(supabase) -> int:
    res = (
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_review_required", True)
        .execute()
    )
    return int(res.count or 0)


async def check_review_queue_and_alert(
    supabase,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Count review backlog and WhatsApp-alert admin when a new threshold is crossed."""
    cfg = settings or get_settings()
    count = await count_review_required_jobs(supabase)
    current_threshold = threshold_for_review_count(count)
    prior = _load_review_queue_state(supabase)
    last_threshold = prior.get("last_threshold")
    last_alert_at = prior.get("last_alert_at")
    last_alert_count = prior.get("last_alert_count")

    base = {
        "review_count": count,
        "current_threshold": current_threshold,
        "last_threshold": last_threshold,
        "alerts_enabled": cfg.enable_admin_whatsapp_alerts,
    }

    if current_threshold is None:
        return {**base, "alerted": False, "reason": "below_threshold"}

    if last_threshold is not None and current_threshold <= last_threshold:
        return {**base, "alerted": False, "reason": "already_alerted_for_threshold"}

    if not cfg.enable_admin_whatsapp_alerts:
        return {**base, "alerted": False, "reason": "disabled"}

    message = build_review_queue_alert_message(
        current_count=count,
        previous_alert_at=last_alert_at,
        previous_alert_count=last_alert_count,
    )
    await send_admin_whatsapp(message, cfg)

    now_iso = datetime.now(timezone.utc).isoformat()
    _save_review_queue_state(
        supabase,
        {
            "last_threshold": current_threshold,
            "last_alert_at": now_iso,
            "last_alert_count": count,
        },
    )
    return {
        **base,
        "alerted": True,
        "reason": "threshold_crossed",
        "threshold_alerted": current_threshold,
    }
