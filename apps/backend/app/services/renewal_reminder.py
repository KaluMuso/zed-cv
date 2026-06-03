"""Subscription renewal reminder emails (n8n cron)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client

from app.core.tier_gating import TIER_DISPLAY
from app.services.email import send_renewal_reminder_email

logger = logging.getLogger(__name__)

REMINDER_DAYS_AHEAD = 3


def _parse_dt(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _renewal_target(row: dict[str, Any]) -> datetime | None:
    """Prefer subscription_renews_at; fall back to subscription_expires_at."""
    return _parse_dt(row.get("subscription_renews_at")) or _parse_dt(
        row.get("subscription_expires_at")
    )


async def run_renewal_reminder_emails(supabase: Client) -> dict[str, int]:
    """Email paid users whose renewal date falls within the next REMINDER_DAYS_AHEAD days."""
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=REMINDER_DAYS_AHEAD)

    result = (
        supabase.table("users")
        .select(
            "id, email, full_name, subscription_tier, "
            "subscription_renews_at, subscription_expires_at, email_notifications_enabled"
        )
        .neq("subscription_tier", "free")
        .execute()
    )

    sent = skipped = failed = 0
    for row in result.data or []:
        if not row.get("email_notifications_enabled", True):
            skipped += 1
            continue
        email = (row.get("email") or "").strip()
        if not email:
            skipped += 1
            continue

        renew_at = _renewal_target(row)
        if renew_at is None or renew_at <= now or renew_at > window_end:
            skipped += 1
            continue

        tier = str(row.get("subscription_tier") or "starter")
        tier_label = TIER_DISPLAY.get(tier, tier.replace("_", " ").title())
        renew_date = renew_at.date().isoformat()
        display_name = (row.get("full_name") or "").strip() or "there"

        try:
            ok = await send_renewal_reminder_email(
                user_id=str(row["id"]),
                email=email,
                display_name=display_name,
                tier_label=tier_label,
                renew_at=renew_at,
            )
            if ok:
                from app.services.in_app_notifications import record_in_app_notification

                renew_date = renew_at.date().isoformat()
                await record_in_app_notification(
                    str(row["id"]),
                    "tier_expiry",
                    {
                        "title": f"Plan renews {renew_date}",
                        "body": f"Your {tier_label} subscription renews soon.",
                        "url": "/settings/billing",
                        "tier": tier,
                        "renew_at": renew_date,
                    },
                    supabase,
                )
                sent += 1
            else:
                skipped += 1
        except Exception:
            logger.exception("renewal reminder failed user_id=%s", row.get("id"))
            failed += 1

    logger.info(
        "renewal reminders: sent=%s skipped=%s failed=%s window_days=%s",
        sent,
        skipped,
        failed,
        REMINDER_DAYS_AHEAD,
    )
    return {"sent": sent, "skipped": skipped, "failed": failed}
