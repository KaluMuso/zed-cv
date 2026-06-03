"""Web Push delivery via VAPID (pywebpush)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pywebpush import WebPushException, webpush
from supabase import Client

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

HIGH_MATCH_PUSH_THRESHOLD = 85.0
PUSH_CHANNEL = "web_push_high_match"


def vapid_configured(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return bool(cfg.vapid_private_key and cfg.vapid_public_key and cfg.vapid_claims_email)


def _vapid_claims(settings: Settings) -> dict[str, str]:
    return {"sub": f"mailto:{settings.vapid_claims_email}"}


def build_high_match_payload(
    *,
    match_id: str,
    job_title: str,
    score: float,
    app_url: str,
) -> dict[str, Any]:
    rounded = round(score)
    path = f"/matches/{match_id}"
    return {
        "title": f"Strong match: {job_title[:80]}",
        "body": f"{rounded}% match — tap to view",
        "url": path,
        "match_id": match_id,
        "score": rounded,
        "tag": f"high-match-{match_id}",
        "icon": "/icons/icon-192.svg",
        "badge": "/icons/icon-192.svg",
        "data": {"url": path, "match_id": match_id},
    }


def send_web_push(
    subscription: dict[str, Any],
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> None:
    cfg = settings or get_settings()
    if not vapid_configured(cfg):
        raise RuntimeError("VAPID keys are not configured")

    webpush(
        subscription_info={
            "endpoint": subscription["endpoint"],
            "keys": {
                "p256dh": subscription["p256dh"],
                "auth": subscription["auth_secret"],
            },
        },
        data=json.dumps(payload, separators=(",", ":")),
        vapid_private_key=cfg.vapid_private_key,
        vapid_claims=_vapid_claims(cfg),
    )


async def upsert_subscription(
    user_id: str,
    endpoint: str,
    p256dh: str,
    auth_secret: str,
    supabase: Client,
    *,
    user_agent: str | None = None,
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    row = {
        "user_id": user_id,
        "endpoint": endpoint,
        "p256dh": p256dh,
        "auth_secret": auth_secret,
        "user_agent": user_agent,
        "updated_at": now_iso,
    }
    supabase.table("web_push_subscriptions").upsert(
        row,
        on_conflict="endpoint",
    ).execute()


async def delete_subscription_by_endpoint(endpoint: str, supabase: Client) -> None:
    supabase.table("web_push_subscriptions").delete().eq("endpoint", endpoint).execute()


async def list_user_subscriptions(user_id: str, supabase: Client) -> list[dict[str, Any]]:
    result = (
        supabase.table("web_push_subscriptions")
        .select("id, endpoint, p256dh, auth_secret")
        .eq("user_id", user_id)
        .execute()
    )
    return [row for row in (result.data or []) if isinstance(row, dict)]


async def send_payload_to_user(
    user_id: str,
    payload: dict[str, Any],
    supabase: Client,
    *,
    settings: Settings | None = None,
) -> int:
    """Send payload to all subscriptions for a user. Returns delivery count."""
    cfg = settings or get_settings()
    if not vapid_configured(cfg):
        logger.debug("web push skipped — VAPID not configured")
        return 0

    subs = await list_user_subscriptions(user_id, supabase)
    if not subs:
        return 0

    sent = 0
    for sub in subs:
        endpoint = str(sub.get("endpoint") or "")
        try:
            send_web_push(sub, payload, settings=cfg)
            sent += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None) if exc.response else None
            if status in (404, 410):
                await delete_subscription_by_endpoint(endpoint, supabase)
            logger.warning(
                "web push failed user=%s endpoint=%s status=%s",
                user_id,
                endpoint[:48],
                status,
                exc_info=True,
            )
        except Exception:
            logger.warning(
                "web push failed user=%s endpoint=%s",
                user_id,
                endpoint[:48],
                exc_info=True,
            )
    return sent


async def send_high_match_push(
    user_id: str,
    match_id: str,
    job_title: str,
    score: float,
    supabase: Client,
    *,
    settings: Settings | None = None,
) -> int:
    cfg = settings or get_settings()
    payload = build_high_match_payload(
        match_id=match_id,
        job_title=job_title or "New role",
        score=score,
        app_url=cfg.app_url,
    )
    sent = await send_payload_to_user(user_id, payload, supabase, settings=cfg)
    if sent > 0:
        from app.services.in_app_notifications import record_in_app_notification

        await record_in_app_notification(
            user_id,
            "web_push",
            {
                "title": payload["title"],
                "body": payload["body"],
                "url": payload["url"],
                "match_id": match_id,
                "score": payload.get("score"),
            },
            supabase,
        )
    return sent


async def send_test_push(user_id: str, supabase: Client, *, settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    payload = {
        "title": "ZedApply test notification",
        "body": "Web Push is working. Tap to open your matches.",
        "url": "/matches",
        "tag": "zedapply-push-test",
        "icon": "/icons/icon-192.svg",
        "data": {"url": "/matches"},
    }
    sent = await send_payload_to_user(user_id, payload, supabase, settings=cfg)
    if sent > 0:
        from app.services.in_app_notifications import record_in_app_notification

        await record_in_app_notification(
            user_id,
            "web_push",
            {
                "title": payload["title"],
                "body": payload["body"],
                "url": payload["url"],
            },
            supabase,
        )
    return sent
