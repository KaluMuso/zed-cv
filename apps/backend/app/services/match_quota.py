"""Match delivery quota fields for /matches list and refresh responses."""
from supabase import Client

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
