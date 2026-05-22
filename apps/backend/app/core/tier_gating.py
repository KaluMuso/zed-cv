"""Subscription tier limits and feature gates (Free / Starter / Professional / Super Standard)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from supabase import Client

# Monthly match views per tier (99999 = unlimited).
TIER_MATCH_LIMITS: dict[str, int] = {
    "free": 10,
    "starter": 50,
    "professional": 125,
    "super_standard": 99999,
}

TIER_DISPLAY: dict[str, str] = {
    "free": "Free",
    "starter": "Starter",
    "professional": "Professional",
    "super_standard": "Super Standard",
}

UNLIMITED_MATCHES = 99999

FEATURE_COVER_LETTER = "cover_letter"
FEATURE_JOB_MATCHES = "job_matches"

_COVER_LETTER_TIERS = frozenset({"professional", "super_standard"})


def normalize_tier(raw: str | None) -> str:
    """Return canonical tier key; unknown values fall back to free."""
    key = (raw or "free").strip().lower()
    if key in TIER_MATCH_LIMITS:
        return key
    return "free"


def match_limit_for_tier(tier: str) -> int:
    return TIER_MATCH_LIMITS.get(normalize_tier(tier), TIER_MATCH_LIMITS["free"])


def _first_of_next_month(today: date) -> date:
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


def _parse_reset_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


async def load_user_gating_row(user_id: str, supabase: Client) -> dict[str, Any]:
    result = (
        supabase.table("users")
        .select(
            "id, subscription_tier, matches_viewed_this_month, billing_cycle_reset, role"
        )
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    row = _first_row(result.data)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return row


async def ensure_billing_cycle_current(
    user_id: str, row: dict[str, Any], supabase: Client, *, today: date | None = None
) -> dict[str, Any]:
    """Reset matches_viewed_this_month when billing_cycle_reset has passed."""
    current_day = today or datetime.now(timezone.utc).date()
    reset_on = _parse_reset_date(row.get("billing_cycle_reset"))
    viewed = int(row.get("matches_viewed_this_month") or 0)

    if reset_on is None or current_day >= reset_on:
        next_reset = _first_of_next_month(current_day)
        supabase.table("users").update(
            {
                "matches_viewed_this_month": 0,
                "billing_cycle_reset": next_reset.isoformat(),
            }
        ).eq("id", user_id).execute()
        row = {**row, "matches_viewed_this_month": 0, "billing_cycle_reset": next_reset.isoformat()}
    return row


async def increment_matches_viewed(
    user_id: str, supabase: Client, *, count: int = 1
) -> int:
    """Add count to matches_viewed_this_month; returns new total."""
    if count <= 0:
        row = await load_user_gating_row(user_id, supabase)
        return int(row.get("matches_viewed_this_month") or 0)

    row = await load_user_gating_row(user_id, supabase)
    row = await ensure_billing_cycle_current(user_id, row, supabase)
    new_total = int(row.get("matches_viewed_this_month") or 0) + count
    supabase.table("users").update({"matches_viewed_this_month": new_total}).eq(
        "id", user_id
    ).execute()
    return new_total


def _cover_letter_allowed(canonical: str) -> bool:
    return canonical in _COVER_LETTER_TIERS


def _job_matches_allowed(canonical: str, viewed: int) -> bool:
    limit = match_limit_for_tier(canonical)
    if limit >= UNLIMITED_MATCHES:
        return True
    return viewed < limit


async def verify_tier_access(
    required_feature: str,
    user_id: str,
    supabase: Client,
    *,
    increment_match_views: int = 0,
    is_superadmin: bool = False,
) -> str:
    """Enforce tier gates. Returns canonical tier when allowed."""
    if is_superadmin:
        return "super_standard"

    row = await load_user_gating_row(user_id, supabase)
    row = await ensure_billing_cycle_current(user_id, row, supabase)
    canonical = normalize_tier(row.get("subscription_tier"))
    viewed = int(row.get("matches_viewed_this_month") or 0)

    if required_feature == FEATURE_COVER_LETTER:
        if not _cover_letter_allowed(canonical):
            detail = (
                "Upgrade to Professional or Super Standard to generate cover letters."
                if canonical in ("free", "starter")
                else "Upgrade to Professional to generate cover letters."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
    elif required_feature == FEATURE_JOB_MATCHES:
        if not _job_matches_allowed(canonical, viewed):
            limit = match_limit_for_tier(canonical)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Monthly match limit reached ({limit} on "
                    f"{TIER_DISPLAY.get(canonical, canonical)}). "
                    "Upgrade for more matches."
                ),
            )
        if increment_match_views > 0:
            new_viewed = viewed + increment_match_views
            limit = match_limit_for_tier(canonical)
            if limit < UNLIMITED_MATCHES and new_viewed > limit:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Monthly match limit reached ({limit} on "
                        f"{TIER_DISPLAY.get(canonical, canonical)})."
                    ),
                )
            await increment_matches_viewed(
                user_id, supabase, count=increment_match_views
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown tier feature: {required_feature}",
        )

    return canonical
