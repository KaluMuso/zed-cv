"""Referral code generation and signup attribution."""
from __future__ import annotations

import logging
import re
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

REFERRAL_CODE_LEN = 8
REFERRAL_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


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


REFERRAL_QUALIFY_BONUS_MATCHES = 5
UNLIMITED_MATCHES = 99_999


def qualify_referral_on_cv_upload(referred_user_id: str, supabase: Any) -> bool:
    """
    When a referred user uploads their first CV, mark the event qualified and
  grant the referrer bonus matches for the current billing period.
    Returns True if a reward was applied.
    """
    event_res = (
        supabase.table("referral_events")
        .select("id, referrer_user_id, status")
        .eq("referred_user_id", referred_user_id)
        .limit(1)
        .execute()
    )
    if not event_res.data:
        return False

    row = event_res.data[0]
    if row.get("status") not in ("signed_up",):
        return False

    referrer_id = row["referrer_user_id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    supabase.table("referral_events").update({
        "status": "qualified",
        "qualified_at": now_iso,
    }).eq("id", row["id"]).execute()

    rewarded = _grant_referrer_match_bonus(referrer_id, supabase)
    if rewarded:
        supabase.table("referral_events").update({
            "status": "rewarded",
            "rewarded_at": now_iso,
        }).eq("id", row["id"]).execute()
    return rewarded


def _grant_referrer_match_bonus(referrer_user_id: str, supabase: Any) -> bool:
    """Add REFERRAL_QUALIFY_BONUS_MATCHES to referrer subscription quota."""
    sub_res = (
        supabase.table("subscriptions")
        .select("id, matches_limit, matches_used")
        .eq("user_id", referrer_user_id)
        .limit(1)
        .execute()
    )
    if not sub_res.data:
        return False

    sub = sub_res.data[0]
    current_limit = int(sub.get("matches_limit") or 0)
    if current_limit >= UNLIMITED_MATCHES:
        return True

    new_limit = min(current_limit + REFERRAL_QUALIFY_BONUS_MATCHES, UNLIMITED_MATCHES)
    supabase.table("subscriptions").update({
        "matches_limit": new_limit,
    }).eq("id", sub["id"]).execute()
    log.info(
        "referral bonus: referrer=%s matches_limit %s -> %s",
        referrer_user_id,
        current_limit,
        new_limit,
    )
    return True


def count_referral_qualified(referrer_user_id: str, supabase: Any) -> int:
    """Referrals that uploaded a CV (qualified or rewarded)."""
    result = (
        supabase.table("referral_events")
        .select("id", count="exact")
        .eq("referrer_user_id", referrer_user_id)
        .in_("status", ["qualified", "rewarded"])
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
