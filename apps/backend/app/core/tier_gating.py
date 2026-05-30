"""Subscription tier limits and feature gates (Free / Starter / Professional / Super Standard)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from supabase import Client

from app.services.pricing import _parse_promotion_until
from app.services.tier_config import get_tier_limits

# Monthly match views per tier (99999 = unlimited).
TIER_MATCH_LIMITS: dict[str, int] = {
    "free": 3,
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
FEATURE_INTERVIEW_PREP = "interview_prep"
FEATURE_MATCH_TAILORED_CV = "match_tailored_cv"

_COVER_LETTER_TIERS = frozenset({"professional", "super_standard"})
_INTERVIEW_PREP_TIERS = frozenset({"super_standard"})
_MATCH_TAILORED_CV_TIERS = frozenset({"professional", "super_standard"})

TIER_FEATURE_GATES: dict[str, frozenset[str]] = {
    FEATURE_COVER_LETTER: _COVER_LETTER_TIERS,
    FEATURE_INTERVIEW_PREP: _INTERVIEW_PREP_TIERS,
    FEATURE_MATCH_TAILORED_CV: _MATCH_TAILORED_CV_TIERS,
}


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


def welcome_bonus_active(
    welcome_match_bonus_until: Any,
    *,
    now: datetime | None = None,
) -> bool:
    """True when a free-tier user is still in the welcome match bonus window."""
    until = _parse_promotion_until(welcome_match_bonus_until)
    if until is None:
        return False
    current = now or datetime.now(timezone.utc)
    return current < until


def effective_free_match_limit(
    *,
    tier_config_limit: int,
    welcome_match_bonus: Any,
    welcome_match_bonus_until: Any,
    now: datetime | None = None,
) -> int:
    """Apply welcome bonus override for free tier when the window is active."""
    if welcome_bonus_active(welcome_match_bonus_until, now=now):
        bonus = welcome_match_bonus
        if bonus is None:
            return 7
        try:
            return max(0, int(bonus))
        except (TypeError, ValueError):
            return 7
    return tier_config_limit


async def load_user_welcome_fields(user_id: str, supabase: Client) -> dict[str, Any]:
    result = (
        supabase.table("users")
        .select(
            "subscription_tier, welcome_match_bonus, welcome_match_bonus_until, "
            "promotion_applied_until, referral_match_bonus"
        )
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    return _first_row(result.data) or {}


async def get_effective_match_limit(user_id: str, supabase: Client) -> int:
    """Monthly match quota: welcome bonus (free) or tier_config matches_limit."""
    welcome_row = await load_user_welcome_fields(user_id, supabase)
    tier_limits = await get_tier_limits(supabase)

    sub_res = (
        supabase.table("subscriptions")
        .select("tier, status")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    sub = _first_row(sub_res.data)
    if sub and sub.get("status") == "active":
        tier = normalize_tier(sub.get("tier"))
    else:
        tier = normalize_tier(welcome_row.get("subscription_tier") or "free")

    base_limit = tier_limits.get(tier, tier_limits.get("free", TIER_MATCH_LIMITS["free"]))
    referral_extra = 0
    try:
        referral_extra = max(0, int(welcome_row.get("referral_match_bonus") or 0))
    except (TypeError, ValueError):
        referral_extra = 0

    if tier != "free":
        return min(base_limit + referral_extra, 99_999)

    free_limit = effective_free_match_limit(
        tier_config_limit=base_limit,
        welcome_match_bonus=welcome_row.get("welcome_match_bonus"),
        welcome_match_bonus_until=welcome_row.get("welcome_match_bonus_until"),
    )
    return min(free_limit + referral_extra, 99_999)


async def load_user_gating_row(user_id: str, supabase: Client) -> dict[str, Any]:
    result = (
        supabase.table("users")
        .select(
            "id, subscription_tier, matches_viewed_this_month, billing_cycle_reset, role, "
            "welcome_match_bonus, welcome_match_bonus_until"
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


async def verify_tier_access(
    required_feature: str,
    user_id: str,
    supabase: Client,
    *,
    increment_match_views: int = 0,
    defer_match_view_increment: bool = False,
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
    elif required_feature == FEATURE_INTERVIEW_PREP:
        allowed = TIER_FEATURE_GATES.get(FEATURE_INTERVIEW_PREP, frozenset())
        if canonical not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Bwana Interview is included on the Super Standard plan (K500/mo). "
                    "Upgrade at /pricing."
                ),
            )
    elif required_feature == FEATURE_MATCH_TAILORED_CV:
        allowed = TIER_FEATURE_GATES.get(FEATURE_MATCH_TAILORED_CV, frozenset())
        if canonical not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Tailored CVs per match require the Professional or Super Standard plan. "
                    "Upgrade at /pricing."
                ),
            )
    elif required_feature == FEATURE_JOB_MATCHES:
        limit = await get_effective_match_limit(user_id, supabase)
        if limit < UNLIMITED_MATCHES and viewed >= limit:
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
            if limit < UNLIMITED_MATCHES and new_viewed > limit:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Monthly match limit reached ({limit} on "
                        f"{TIER_DISPLAY.get(canonical, canonical)})."
                    ),
                )
            if not defer_match_view_increment:
                await increment_matches_viewed(
                    user_id, supabase, count=increment_match_views
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown tier feature: {required_feature}",
        )

    return canonical
