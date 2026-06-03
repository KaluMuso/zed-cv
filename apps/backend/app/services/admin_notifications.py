"""Admin broadcast Web Push campaigns — queue rows and deliver."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import Client

from app.core.config import Settings
from app.schemas.admin_notifications import (
    AdminNotificationCreate,
    AdminNotificationCreateResponse,
    AdminNotificationDispatchResponse,
    NotificationTargetAudience,
)
from app.services.in_app_notifications import record_in_app_notification
from app.services.web_push import send_payload_to_user, vapid_configured

logger = logging.getLogger(__name__)

_USER_PAGE_SIZE = 500


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _should_send_immediately(scheduled_at: datetime | None, now: datetime) -> bool:
    if scheduled_at is None:
        return True
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    return scheduled_at <= now


def _fetch_target_user_ids(
    supabase: Client,
    *,
    target_audience: NotificationTargetAudience,
    target_tier: str | None,
) -> list[str]:
    user_ids: list[str] = []
    offset = 0
    while True:
        query = supabase.table("users").select("id")
        if target_audience == NotificationTargetAudience.tier:
            query = query.eq("subscription_tier", target_tier)
        result = query.range(offset, offset + _USER_PAGE_SIZE - 1).execute()
        rows = result.data or []
        if not rows:
            break
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                user_ids.append(str(row["id"]))
        if len(rows) < _USER_PAGE_SIZE:
            break
        offset += _USER_PAGE_SIZE
    return user_ids


def _insert_recipient_rows(
    supabase: Client,
    campaign_id: str,
    user_ids: list[str],
) -> None:
    if not user_ids:
        return
    chunk_size = 200
    for start in range(0, len(user_ids), chunk_size):
        chunk = user_ids[start : start + chunk_size]
        rows = [
            {"campaign_id": campaign_id, "user_id": uid, "status": "pending"}
            for uid in chunk
        ]
        supabase.table("admin_notification_recipients").insert(rows).execute()


def _build_push_payload(campaign: dict[str, Any]) -> dict[str, Any]:
    url = (campaign.get("url") or "/matches").strip() or "/matches"
    if not url.startswith("/"):
        url = f"/{url.lstrip('/')}"
    title = str(campaign.get("title") or "Zed Apply")
    body = str(campaign.get("body") or "")
    campaign_id = str(campaign.get("id") or "")
    return {
        "title": title[:120],
        "body": body[:500],
        "url": url,
        "tag": f"admin-broadcast-{campaign_id}",
        "icon": "/icons/icon-192.svg",
        "badge": "/icons/icon-192.svg",
        "data": {"url": url, "campaign_id": campaign_id},
    }


async def deliver_campaign(
    campaign_id: str,
    supabase: Client,
    *,
    settings: Settings,
) -> dict[str, int]:
    """Send pending recipient rows for one campaign."""
    campaign_res = (
        supabase.table("admin_notification_campaigns")
        .select("id, title, body, url, status")
        .eq("id", campaign_id)
        .limit(1)
        .execute()
    )
    rows = campaign_res.data or []
    if not rows or not isinstance(rows[0], dict):
        return {"sent": 0, "failed": 0}

    campaign = rows[0]
    if campaign.get("status") in ("completed", "cancelled"):
        return {"sent": 0, "failed": 0}

    now = _utc_now()
    supabase.table("admin_notification_campaigns").update(
        {"status": "sending", "started_at": _iso(now)}
    ).eq("id", campaign_id).execute()

    if not vapid_configured(settings):
        supabase.table("admin_notification_campaigns").update(
            {
                "status": "failed",
                "completed_at": _iso(now),
            }
        ).eq("id", campaign_id).execute()
        return {"sent": 0, "failed": 0}

    payload = _build_push_payload(campaign)
    pending_res = (
        supabase.table("admin_notification_recipients")
        .select("id, user_id")
        .eq("campaign_id", campaign_id)
        .eq("status", "pending")
        .execute()
    )
    pending = [r for r in (pending_res.data or []) if isinstance(r, dict)]

    sent_count = 0
    failed_count = 0
    for row in pending:
        recipient_id = str(row.get("id") or "")
        user_id = str(row.get("user_id") or "")
        if not recipient_id or not user_id:
            continue
        try:
            devices = await send_payload_to_user(
                user_id, payload, supabase, settings=settings
            )
            if devices > 0:
                sent_count += 1
                supabase.table("admin_notification_recipients").update(
                    {
                        "status": "sent",
                        "devices_sent": devices,
                        "sent_at": _iso(_utc_now()),
                    }
                ).eq("id", recipient_id).execute()
                await record_in_app_notification(
                    user_id,
                    "admin_broadcast",
                    {
                        "title": payload["title"],
                        "body": payload["body"],
                        "url": payload["url"],
                        "campaign_id": campaign_id,
                    },
                    supabase,
                )
            else:
                failed_count += 1
                supabase.table("admin_notification_recipients").update(
                    {
                        "status": "skipped",
                        "skip_reason": "no_active_subscriptions",
                    }
                ).eq("id", recipient_id).execute()
        except Exception as exc:
            failed_count += 1
            supabase.table("admin_notification_recipients").update(
                {
                    "status": "failed",
                    "error": str(exc)[:500],
                }
            ).eq("id", recipient_id).execute()
            logger.warning(
                "admin notification delivery failed campaign=%s user=%s",
                campaign_id,
                user_id,
                exc_info=True,
            )

    finished = _utc_now()
    supabase.table("admin_notification_campaigns").update(
        {
            "status": "completed",
            "completed_at": _iso(finished),
            "recipients_sent": sent_count,
            "recipients_failed": failed_count,
        }
    ).eq("id", campaign_id).execute()
    return {"sent": sent_count, "failed": failed_count}


async def create_admin_notification_campaign(
    body: AdminNotificationCreate,
    supabase: Client,
    *,
    settings: Settings,
    created_by: str | None = None,
) -> AdminNotificationCreateResponse:
    now = _utc_now()
    send_now = _should_send_immediately(body.scheduled_at, now)
    initial_status = "pending" if send_now else "scheduled"

    tier_value = body.target_tier.value if body.target_tier else None
    campaign_row = {
        "title": body.title.strip(),
        "body": body.body.strip(),
        "url": body.url.strip() if body.url else None,
        "target_audience": body.target_audience.value,
        "target_tier": tier_value,
        "scheduled_at": _iso(body.scheduled_at),
        "status": initial_status,
        "created_by": created_by,
    }
    insert_res = (
        supabase.table("admin_notification_campaigns")
        .insert(campaign_row)
        .execute()
    )
    inserted = insert_res.data
    if isinstance(inserted, list):
        campaign = inserted[0] if inserted else {}
    elif isinstance(inserted, dict):
        campaign = inserted
    else:
        campaign = {}
    campaign_id = str(campaign.get("id") or "")

    user_ids = _fetch_target_user_ids(
        supabase,
        target_audience=body.target_audience,
        target_tier=tier_value,
    )
    _insert_recipient_rows(supabase, campaign_id, user_ids)

    supabase.table("admin_notification_campaigns").update(
        {"recipients_queued": len(user_ids)}
    ).eq("id", campaign_id).execute()

    response_status: str
    message: str
    if send_now:
        if not vapid_configured(settings):
            supabase.table("admin_notification_campaigns").update(
                {"status": "failed", "completed_at": _iso(_utc_now())}
            ).eq("id", campaign_id).execute()
            response_status = "completed"
            message = (
                f"Queued {len(user_ids)} recipient(s); VAPID not configured — "
                "delivery skipped"
            )
        else:
            counts = await deliver_campaign(campaign_id, supabase, settings=settings)
            response_status = "completed"
            message = (
                f"Delivered to {counts['sent']} user(s); "
                f"{counts['failed']} skipped or failed"
            )
    else:
        response_status = "scheduled"
        message = f"Scheduled for {body.scheduled_at.isoformat() if body.scheduled_at else 'later'}"

    return AdminNotificationCreateResponse(
        campaign_id=campaign_id,
        status=response_status,  # type: ignore[arg-type]
        target_audience=body.target_audience,
        target_tier=body.target_tier,
        recipients_queued=len(user_ids),
        scheduled_at=body.scheduled_at,
        message=message,
    )


async def dispatch_due_campaigns(
    supabase: Client,
    *,
    settings: Settings,
) -> AdminNotificationDispatchResponse:
    """Cron helper: send campaigns whose scheduled_at is due."""
    now_iso = _iso(_utc_now())
    due_res = (
        supabase.table("admin_notification_campaigns")
        .select("id")
        .in_("status", ["pending", "scheduled"])
        .lte("scheduled_at", now_iso)
        .execute()
    )
    campaigns = [str(r["id"]) for r in (due_res.data or []) if isinstance(r, dict) and r.get("id")]

    total_sent = 0
    total_failed = 0
    for campaign_id in campaigns:
        counts = await deliver_campaign(campaign_id, supabase, settings=settings)
        total_sent += counts["sent"]
        total_failed += counts["failed"]

    return AdminNotificationDispatchResponse(
        campaigns_processed=len(campaigns),
        recipients_sent=total_sent,
        recipients_failed=total_failed,
    )
