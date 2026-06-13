"""Referral code generation, signup attribution, and paid-subscription rewards."""
from __future__ import annotations

import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

log = logging.getLogger(__name__)

REFERRAL_CODE_LEN = 8
REFERRAL_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)

REFERRAL_REWARD_BONUS_MATCHES = 5
UNLIMITED_MATCHES = 99_999

# Legacy alias for tests and imports
REFERRAL_QUALIFY_BONUS_MATCHES = REFERRAL_REWARD_BONUS_MATCHES


def generate_referral_code(supabase: Any) -> str:
    """Create a unique referral code for a new user."""
    for _ in range(25):
        code = "".join(secrets.choice(REFERRAL_ALPHABET) for _ in range(REFERRAL_CODE_LEN))
        existing = (
            supabase.table("users")
            .select("id")
            .eq("referral_code", code)
            .limit(1)
            .execute()
        )
        if not existing.data:
            return code
    raise RuntimeError("Could not allocate unique referral_code")


def resolve_referrer_user_id(ref: str | None, supabase: Any) -> str | None:
    """Map invite ref (user id or referral_code) to referrer user id."""
    if not ref:
        return None
    trimmed = ref.strip()
    if not trimmed:
        return None

    if _UUID_RE.match(trimmed):
        result = (
            supabase.table("users")
            .select("id")
            .eq("id", trimmed)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["id"]
        return None

    code = trimmed.upper()
    result = (
        supabase.table("users")
        .select("id")
        .eq("referral_code", code)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]["id"]
    return None


def attach_referral_on_signup(
    new_user_id: str,
    referral_ref: str | None,
    supabase: Any,
) -> str | None:
    """
    Link a new user to their referrer and log referral_events.
    Returns referrer id when applied, else None.
    """
    referrer_id = resolve_referrer_user_id(referral_ref, supabase)
    if not referrer_id or referrer_id == new_user_id:
        return None

    supabase.table("users").update({
        "referred_by_user_id": referrer_id,
    }).eq("id", new_user_id).execute()

    try:
        supabase.table("referral_events").insert({
            "referrer_user_id": referrer_id,
            "referred_user_id": new_user_id,
            "status": "signed_up",
        }).execute()
    except Exception as exc:
        log.warning(
            "referral_events insert failed for %s -> %s: %s",
            referrer_id,
            new_user_id,
            exc,
        )

    return referrer_id


def count_referral_signups(referrer_user_id: str, supabase: Any) -> int:
    """Users who signed up with this referrer's link."""
    result = (
        supabase.table("users")
        .select("id", count="exact")
        .eq("referred_by_user_id", referrer_user_id)
        .execute()
    )
    if result.count is not None:
        return int(result.count)
    return len(result.data or [])


def qualify_referral_on_cv_upload(referred_user_id: str, supabase: Any) -> bool:
    """
    Optional funnel step: mark referral qualified when referred user uploads CV.
    Does not grant rewards — rewards fire on first paid subscription only.
    """
    event_res = (
        supabase.table("referral_events")
        .select("id, status")
        .eq("referred_user_id", referred_user_id)
        .limit(1)
        .execute()
    )
    if not event_res.data:
        return False

    row = event_res.data[0]
    if row.get("status") != "signed_up":
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    supabase.table("referral_events").update({
        "status": "qualified",
        "qualified_at": now_iso,
    }).eq("id", row["id"]).execute()
    return True


def reward_referral_on_first_paid_subscription(
    referred_user_id: str,
    new_tier: str,
    supabase: Any,
) -> bool:
    """
    Grant referrer +5 bonus matches when referee completes first paid subscription.
    Idempotent per referred_user_id (status rewarded). Returns True if reward applied.
    """
    tier = (new_tier or "free").lower()
    if tier == "free":
        return False

    event_res = (
        supabase.table("referral_events")
        .select("id, referrer_user_id, referred_user_id, status")
        .eq("referred_user_id", referred_user_id)
        .limit(1)
        .execute()
    )
    if not event_res.data:
        return False

    row = event_res.data[0]
    if row.get("status") == "rewarded":
        return False

    referrer_id = row["referrer_user_id"]
    if referrer_id == referred_user_id:
        log.warning(
            "referral reward blocked: self-referral user_id=%s",
            referred_user_id,
        )
        return False

    now_iso = datetime.now(timezone.utc).isoformat()

    if row.get("status") in ("signed_up", "qualified"):
        supabase.table("referral_events").update({
            "status": "paid",
            "paid_at": now_iso,
        }).eq("id", row["id"]).execute()
    elif row.get("status") == "paid":
        pass
    else:
        return False

    rewarded = _grant_referrer_match_bonus(referrer_id, supabase)
    if rewarded:
        supabase.table("referral_events").update({
            "status": "rewarded",
            "rewarded_at": now_iso,
        }).eq("id", row["id"]).execute()
    return rewarded


def _grant_referrer_match_bonus(referrer_user_id: str, supabase: Any) -> bool:
    """Add REFERRAL_REWARD_BONUS_MATCHES to the referrer's effective match quota.

    Paid-tier quota comes from tier_config; subscription.matches_limit was
    dropped in migration 036. Free-tier welcome bonus uses users.welcome_match_bonus.
    All tiers also accumulate users.referral_match_bonus (migration 084).
    """
    user_res = (
        supabase.table("users")
        .select(
            "id, subscription_tier, welcome_match_bonus, "
            "welcome_match_bonus_until, referral_match_bonus"
        )
        .eq("id", referrer_user_id)
        .limit(1)
        .execute()
    )
    if not user_res.data:
        return False

    user = user_res.data[0]
    tier = (user.get("subscription_tier") or "free").lower()
    referral_bonus = int(user.get("referral_match_bonus") or 0)
    new_referral_bonus = min(
        referral_bonus + REFERRAL_REWARD_BONUS_MATCHES,
        UNLIMITED_MATCHES,
    )

    update_payload: dict[str, Any] = {"referral_match_bonus": new_referral_bonus}

    if tier == "free":
        current_welcome = int(user.get("welcome_match_bonus") or 7)
        update_payload["welcome_match_bonus"] = min(
            current_welcome + REFERRAL_REWARD_BONUS_MATCHES,
            UNLIMITED_MATCHES,
        )
        if not user.get("welcome_match_bonus_until"):
            update_payload["welcome_match_bonus_until"] = (
                datetime.now(timezone.utc) + timedelta(days=60)
            ).isoformat()

    supabase.table("users").update(update_payload).eq("id", referrer_user_id).execute()
    log.info(
        "referral bonus: referrer=%s referral_match_bonus %s -> %s tier=%s",
        referrer_user_id,
        referral_bonus,
        new_referral_bonus,
        tier,
    )
    return True


def count_referral_qualified(referrer_user_id: str, supabase: Any) -> int:
    """Referrals where the referee subscribed (reward granted)."""
    result = (
        supabase.table("referral_events")
        .select("id", count="exact")
        .eq("referrer_user_id", referrer_user_id)
        .eq("status", "rewarded")
        .execute()
    )
    if result.count is not None:
        return int(result.count)
    return len(result.data or [])


def is_valid_referral_ref(ref: str | None) -> bool:
    """Lightweight client-side-ish validation before DB lookup."""
    if not ref or not ref.strip():
        return False
    trimmed = ref.strip()
    if _UUID_RE.match(trimmed):
        try:
            uuid.UUID(trimmed)
            return True
        except ValueError:
            return False
    return 1 <= len(trimmed) <= 36

def evaluate_referral_milestones(referrer_id: str, supabase: Any) -> None:
    """Evaluate complex referral milestones (e.g. 10 signups -> matches, 5 paid -> cash)."""
    # 1. Count total referred users
    res = supabase.table("referral_events").select("referred_user_id", count="exact").eq("referrer_user_id", referrer_id).execute()
    total_referred = res.count if res.count is not None else len(res.data or [])

    # 2. Count total paid referred users
    paid_res = (
        supabase.table("referral_events")
        .select("referred_user_id, users!inner(first_payment_at)")
        .eq("referrer_user_id", referrer_id)
        .not_.is_("users.first_payment_at", "null")
        .execute()
    )
    total_paid_referred = len(paid_res.data or [])

    # 3. Load active config
    config_res = supabase.table("referral_config").select("*").eq("is_active", True).execute()
    
    for conf in (config_res.data or []):
        r_type = conf["reward_type"]
        req_count = conf["required_count"]
        val = conf["reward_value"]
        
        milestones_hit = total_paid_referred // req_count if r_type == "cash" else total_referred // req_count
        
        for m_idx in range(1, milestones_hit + 1):
            try:
                supabase.table("referral_rewards").insert({
                    "user_id": referrer_id,
                    "reward_type": r_type,
                    "reward_value": val,
                    "milestone_count": m_idx,
                    "status": "pending_payout" if r_type == "cash" else "credited"
                }).execute()
                
                # Apply instantaneous rewards
                if r_type == "matches":
                    user_res = supabase.table("users").select("referral_match_bonus").eq("id", referrer_id).limit(1).execute()
                    if user_res.data:
                        current_bonus = int(user_res.data[0].get("referral_match_bonus") or 0)
                        supabase.table("users").update({
                            "referral_match_bonus": min(current_bonus + val, UNLIMITED_MATCHES)
                        }).eq("id", referrer_id).execute()
                elif r_type == "tier_promo":
                    from dateutil.relativedelta import relativedelta
                    user_res = supabase.table("users").select("subscription_tier, promotion_applied_until").eq("id", referrer_id).limit(1).execute()
                    if user_res.data:
                        tier = user_res.data[0].get("subscription_tier")
                        if tier == "free" or tier is None:
                            until = user_res.data[0].get("promotion_applied_until")
                            base_date = datetime.fromisoformat(until.replace('Z', '+00:00')) if until else datetime.now(timezone.utc)
                            new_until = (base_date + relativedelta(months=val)).isoformat()
                            supabase.table("users").update({
                                "subscription_tier": "starter",
                                "promotion_applied_until": new_until
                            }).eq("id", referrer_id).execute()
            except Exception as e:
                # Likely a unique constraint violation meaning already rewarded
                pass
