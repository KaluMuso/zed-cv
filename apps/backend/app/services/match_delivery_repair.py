"""Superadmin repair: reset monthly delivery credits and restore welcome window."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client

from app.core.tier_gating import get_effective_match_limit, normalize_tier
from app.services.matching import (
    _billing_period_start,
    backfill_match_credits,
    get_credited_match_count,
)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


async def repair_user_match_delivery(
    user_id: str,
    supabase: Client,
    *,
    reset_month_credits: bool = True,
    apply_welcome: bool = True,
) -> dict[str, Any]:
    """Align a user's delivered matches with tier quota (fixes over-delivery bugs).

    Steps when ``reset_month_credits``:
      1. Clear ``credited_at`` for matches credited in the current billing month.
      2. Re-credit top scores up to remaining quota via ``backfill_match_credits``.

    When ``apply_welcome`` and user is on free tier:
      - Set ``welcome_match_bonus`` to 7 if unset.
      - Set ``welcome_match_bonus_until`` to created_at + 1 month if missing/expired.
    """
    user_res = (
        supabase.table("users")
        .select(
            "id, subscription_tier, created_at, welcome_match_bonus, welcome_match_bonus_until"
        )
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not user_res.data:
        raise ValueError("User not found")
    user = user_res.data[0]

    sub_res = (
        supabase.table("subscriptions")
        .select("tier, status")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    sub = sub_res.data[0] if sub_res.data else None
    tier = normalize_tier(
        (sub or {}).get("tier") if sub and sub.get("status") == "active" else user.get("subscription_tier")
    )

    credited_before = await get_credited_match_count(user_id, supabase)
    period_start = await _billing_period_start(user_id, supabase)
    reset_count = 0
    welcome_updated = False

    if apply_welcome and tier == "free":
        created = _parse_dt(user.get("created_at")) or datetime.now(timezone.utc)
        until = _parse_dt(user.get("welcome_match_bonus_until"))
        now = datetime.now(timezone.utc)
        patch: dict[str, Any] = {}
        if user.get("welcome_match_bonus") is None:
            patch["welcome_match_bonus"] = 7
        if until is None or until <= now:
            patch["welcome_match_bonus_until"] = (created + timedelta(days=31)).isoformat()
        if patch:
            supabase.table("users").update(patch).eq("id", user_id).execute()
            welcome_updated = True

    if reset_month_credits:
        cleared = (
            supabase.table("matches")
            .update({"credited_at": None})
            .eq("user_id", user_id)
            .gte("credited_at", period_start.isoformat())
            .execute()
        )
        reset_count = len(cleared.data or [])

    newly_credited: list[str] = []
    if reset_month_credits:
        newly_credited = await backfill_match_credits(user_id, supabase)

    credited_after = await get_credited_match_count(user_id, supabase)
    matches_limit = await get_effective_match_limit(user_id, supabase)

    return {
        "user_id": user_id,
        "tier": tier,
        "matches_limit": matches_limit,
        "credited_before": credited_before,
        "credited_after": credited_after,
        "credits_reset_this_month": reset_count,
        "newly_credited_job_ids": newly_credited,
        "welcome_bonus_updated": welcome_updated,
    }
