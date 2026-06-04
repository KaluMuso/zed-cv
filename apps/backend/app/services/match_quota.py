"""Match delivery quota fields for /matches list and refresh responses."""
from fastapi import HTTPException, status
from supabase import Client

from app.core.tier_gating import TIER_DISPLAY, normalize_tier
from app.schemas.tier_config import UNLIMITED_MATCHES
from app.services.matching import (
    check_match_quota,
    get_credited_match_count,
    get_user_tier_limit,
)


async def build_match_quota_snapshot(user_id: str, supabase: Client) -> dict[str, int | bool]:
    """Canonical quota block shared by GET /matches and POST /matches/refresh.

    matches_used mirrors credited unique jobs this billing period (not
    subscriptions.matches_used, which is legacy). matches_limit is the
    effective monthly cap from tier_config (+ welcome/referral bonuses).
    matches_unlimited is true when limit uses the 99999 sentinel.
    """
    _, remaining = await check_match_quota(user_id, supabase)
    _, matches_limit, _ = await get_user_tier_limit(user_id, supabase)
    matches_used = await get_credited_match_count(user_id, supabase)
    unlimited = matches_limit >= UNLIMITED_MATCHES
    return {
        "matches_used": matches_used,
        "credited_count": matches_used,
        "matches_limit": matches_limit,
        "matches_unlimited": unlimited,
        "remaining_quota": remaining,
    }


async def assert_match_delivery_quota(
    user_id: str,
    supabase: Client,
    *,
    is_superadmin: bool = False,
) -> None:
    """Raise 403 when monthly delivery quota is exhausted (Lusaka month + credited_at).

    Same rules as GET /matches and POST /matches/refresh — not
    users.matches_viewed_this_month (UTC legacy counter).
    """
    if is_superadmin:
        return
    has_quota, _remaining = await check_match_quota(user_id, supabase)
    if has_quota:
        return
    tier, limit, _active = await get_user_tier_limit(user_id, supabase)
    canonical = normalize_tier(tier)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            f"Monthly match limit reached ({limit} on "
            f"{TIER_DISPLAY.get(canonical, canonical)}). "
            "Upgrade for more matches."
        ),
    )
