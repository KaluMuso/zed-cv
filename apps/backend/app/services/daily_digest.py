"""Daily match digest batching — email (Resend) and WhatsApp (Starter+)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client

from app.core.config import get_settings
from app.services.email import send_daily_digest_email
from app.services.matching import run_matching_for_user
from app.services.notification_channels import wants_email_digest, wants_whatsapp_digest
from app.services.quiet_hours import user_in_quiet_hours
from app.services.whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)

EMAIL_DAILY_DIGEST_CHANNEL = "email_digest"
WHATSAPP_DAILY_DIGEST_CHANNEL = "whatsapp_daily_digest"
DIGEST_MATCH_LIMIT = 15
DIGEST_TOP_N = 3
JOB_RECENCY_HOURS = 24

_USER_SELECT = (
    "id, phone, email, full_name, whatsapp_number, whatsapp_verified, "
    "alert_frequency, email_notifications_enabled, preferred_notification_channel, "
    "subscription_tier, quiet_hours_start, quiet_hours_end, display_timezone"
)


def _display_name(row: dict[str, Any]) -> str:
    name = (row.get("full_name") or "").strip()
    if name:
        first = name.split()[0]
        return first if first else "there"
    return "there"


def _delivery_phone(row: dict[str, Any]) -> str | None:
    if row.get("whatsapp_verified") and row.get("whatsapp_number"):
        return str(row["whatsapp_number"])
    phone = row.get("phone")
    return str(phone) if phone else None


def format_daily_digest_message(name: str, matches: list[dict[str, Any]]) -> str:
    """WhatsApp-friendly digest text."""
    lines = [
        f"Good morning {name}! Here are your {len(matches)} new matches for today:\n",
    ]
    for index, match in enumerate(matches, start=1):
        title = match.get("job_title") or "Role"
        company = match.get("job_company") or "Company"
        score = round(float(match.get("final_score") or match.get("score") or 0))
        lines.append(f"{index}. {title} at {company} ({score}% match)")
    lines.append(
        "\nReply 1, 2, or 3 to apply, or open ZedApply for details."
    )
    return "\n".join(lines)


async def _fetch_sent_job_ids(user_id: str, channel: str, supabase: Client) -> set[str]:
    result = (
        supabase.table("user_notifications")
        .select("job_id")
        .eq("user_id", user_id)
        .eq("channel", channel)
        .execute()
    )
    return {
        str(row["job_id"])
        for row in (result.data or [])
        if isinstance(row, dict) and row.get("job_id")
    }


async def _fetch_job_posted_at(job_ids: list[str], supabase: Client) -> dict[str, datetime]:
    if not job_ids:
        return {}
    result = (
        supabase.table("jobs")
        .select("id, posted_at, created_at")
        .in_("id", job_ids)
        .execute()
    )
    posted: dict[str, datetime] = {}
    for row in result.data or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        raw = row.get("posted_at") or row.get("created_at")
        if not raw:
            continue
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        posted[str(row["id"])] = parsed
    return posted


def _job_within_recency(
    job_id: str,
    posted_by_job: dict[str, datetime],
    *,
    cutoff: datetime,
) -> bool:
    posted = posted_by_job.get(job_id)
    if posted is None:
        return True
    return posted >= cutoff


async def _select_digest_matches(
    user_id: str,
    channel: str,
    supabase: Client,
    *,
    now: datetime,
    min_score: float,
) -> list[dict[str, Any]]:
    """Top N RPC matches from the last 24h not yet sent on the given channel."""
    try:
        rpc_rows = await run_matching_for_user(
            user_id,
            supabase,
            limit=DIGEST_MATCH_LIMIT,
            min_score=min_score,
        )
    except ValueError:
        return []
    except Exception:
        logger.warning("daily digest RPC failed for user=%s", user_id, exc_info=True)
        return []

    if not rpc_rows:
        return []

    sent_ids = await _fetch_sent_job_ids(user_id, channel, supabase)
    candidate_ids = [
        str(row["job_id"])
        for row in rpc_rows
        if isinstance(row, dict) and row.get("job_id") and str(row["job_id"]) not in sent_ids
    ]
    cutoff = now - timedelta(hours=JOB_RECENCY_HOURS)
    posted_by_job = await _fetch_job_posted_at(candidate_ids, supabase)

    selected: list[dict[str, Any]] = []
    for row in rpc_rows:
        if not isinstance(row, dict):
            continue
        job_id = row.get("job_id")
        if not job_id or str(job_id) in sent_ids:
            continue
        if not _job_within_recency(str(job_id), posted_by_job, cutoff=cutoff):
            continue
        selected.append(row)
        if len(selected) >= DIGEST_TOP_N:
            break
    return selected


async def record_digest_notifications(
    user_id: str,
    job_ids: list[str],
    channel: str,
    supabase: Client,
    *,
    now: datetime | None = None,
) -> None:
    unique_ids = list(dict.fromkeys(jid for jid in job_ids if jid))
    if not unique_ids:
        return
    sent_at = (now or datetime.now(timezone.utc)).isoformat()
    rows = [
        {
            "user_id": user_id,
            "job_id": job_id,
            "channel": channel,
            "sent_at": sent_at,
        }
        for job_id in unique_ids
    ]
    supabase.table("user_notifications").upsert(
        rows,
        on_conflict="user_id,job_id,channel",
    ).execute()


async def _eligible_daily_users(supabase: Client) -> list[dict[str, Any]]:
    users_res = (
        supabase.table("users")
        .select(_USER_SELECT)
        .eq("alert_frequency", "daily")
        .execute()
    )
    return [row for row in (users_res.data or []) if isinstance(row, dict)]


async def run_email_daily_digest(supabase: Client) -> dict[str, int]:
    """Send daily digests via Resend for users on the email channel."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    sent = skipped = failed = 0

    for user in await _eligible_daily_users(supabase):
        user_id = user.get("id")
        if not user_id or not wants_email_digest(user):
            continue

        matches = await _select_digest_matches(
            str(user_id),
            EMAIL_DAILY_DIGEST_CHANNEL,
            supabase,
            now=now,
            min_score=settings.min_match_score,
        )
        if not matches:
            skipped += 1
            continue

        ok = await send_daily_digest_email(
            str(user_id),
            user.get("email") or "",
            _display_name(user),
            matches,
            supabase,
            digest_date=now.date().isoformat(),
        )
        if ok:
            await record_digest_notifications(
                str(user_id),
                [str(m["job_id"]) for m in matches if m.get("job_id")],
                EMAIL_DAILY_DIGEST_CHANNEL,
                supabase,
                now=now,
            )
            sent += 1
        else:
            failed += 1

    return {"sent": sent, "skipped": skipped, "failed": failed}


async def run_whatsapp_daily_digest(supabase: Client) -> dict[str, int]:
    """Send daily digests via WAHA for Starter+ users on the WhatsApp channel."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    sent = skipped = failed = quiet_hours_skipped = 0

    for user in await _eligible_daily_users(supabase):
        user_id = user.get("id")
        phone = _delivery_phone(user) if user_id else None
        if not user_id or not phone or not wants_whatsapp_digest(user):
            continue

        if user_in_quiet_hours(user, now):
            quiet_hours_skipped += 1
            continue

        matches = await _select_digest_matches(
            str(user_id),
            WHATSAPP_DAILY_DIGEST_CHANNEL,
            supabase,
            now=now,
            min_score=settings.min_match_score,
        )
        if not matches:
            skipped += 1
            continue

        message = format_daily_digest_message(_display_name(user), matches)
        try:
            await send_whatsapp_message(phone, message)
        except Exception:
            logger.warning("WhatsApp daily digest failed for user=%s", user_id, exc_info=True)
            failed += 1
            continue

        await record_digest_notifications(
            str(user_id),
            [str(m["job_id"]) for m in matches if m.get("job_id")],
            WHATSAPP_DAILY_DIGEST_CHANNEL,
            supabase,
            now=now,
        )
        sent += 1

    return {
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "quiet_hours_skipped": quiet_hours_skipped,
    }


async def build_daily_digest_batch(supabase: Client) -> list[dict[str, str]]:
    """Legacy n8n shape: WhatsApp payloads without sending (prefer run_whatsapp_daily_digest)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payloads: list[dict[str, str]] = []

    for user in await _eligible_daily_users(supabase):
        if not wants_whatsapp_digest(user):
            continue
        user_id = user.get("id")
        phone = _delivery_phone(user)
        if not user_id or not phone:
            continue

        if user_in_quiet_hours(user, now):
            continue

        matches = await _select_digest_matches(
            str(user_id),
            WHATSAPP_DAILY_DIGEST_CHANNEL,
            supabase,
            now=now,
            min_score=settings.min_match_score,
        )
        if not matches:
            continue

        payloads.append(
            {
                "user_id": str(user_id),
                "phone": phone,
                "message": format_daily_digest_message(_display_name(user), matches),
            }
        )
        await record_digest_notifications(
            str(user_id),
            [str(m["job_id"]) for m in matches if m.get("job_id")],
            WHATSAPP_DAILY_DIGEST_CHANNEL,
            supabase,
            now=now,
        )

    return payloads
