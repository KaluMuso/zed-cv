"""Job matching — delegates to Supabase RPC for hybrid scoring."""
from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client
from app.core.config import get_settings
from app.schemas.subscription import TIER_LIMITS


# Phase 2 Initiative #4 — preference-aware re-rank weights.
# Caps are intentionally small. Preferences are a tie-breaker, not a
# replacement for the vector + skill scoring. Bonus is capped at
# PREFERENCE_BONUS_CAP so a perfect-preference job can move past a
# slightly-better-fit-on-skills job, but a poor-fit-on-skills job
# can't win on preferences alone.
PREFERENCE_BONUS_CAP = 6.0
ROLE_BONUS = 3.0
SALARY_BONUS = 1.5
ARRANGEMENT_BONUS = 1.5
REGION_BONUS = 1.0


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


def _month_start(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def get_user_tier_limit(user_id: str, supabase: Client) -> tuple[str, int, bool]:
    """Return (tier, monthly quota, active). Quotas come from TIER_LIMITS."""
    sub_res = (
        supabase.table("subscriptions")
        .select("tier, status")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    sub = _first_row(sub_res.data)
    if sub:
        active = sub.get("status") == "active"
        tier = sub.get("tier") or "free"
        return tier, TIER_LIMITS.get(tier, TIER_LIMITS["free"]), active

    user_res = (
        supabase.table("users")
        .select("subscription_tier")
        .eq("id", user_id)
        .single()
        .execute()
    )
    user = _first_row(user_res.data) or {}
    tier = user.get("subscription_tier") or "free"
    return tier, TIER_LIMITS.get(tier, TIER_LIMITS["free"]), True


async def get_credited_match_count(
    user_id: str,
    supabase: Client,
    *,
    now: datetime | None = None,
) -> int:
    result = (
        supabase.table("matches")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("credited_at", _month_start(now).isoformat())
        .execute()
    )
    if result.count is not None:
        return int(result.count)
    return len(result.data or [])


async def run_matching_for_user(
    user_id: str, supabase: Client, limit: int = 20, min_score: float = 50.0
) -> list[dict]:
    """Execute hybrid matching via the match_jobs_for_user() RPC function."""
    result = supabase.rpc(
        "match_jobs_for_user",
        {"p_user_id": user_id, "p_limit": limit, "p_min_score": min_score},
    ).execute()
    return result.data or []


def apply_preferences_to_match(
    *,
    base_score: float,
    base_bonus: float,
    job: dict[str, Any],
    preferences: Optional[dict[str, Any]],
) -> tuple[float, float, Optional[str]]:
    """Re-rank one match row by the user's job-search preferences.

    Returns (adjusted_score, adjusted_bonus, human_explanation_or_None).
    The adjustment is additive bonus, capped at PREFERENCE_BONUS_CAP, and
    the returned score is clamped to [0, 100]. When preferences is None
    or empty, returns (base_score, base_bonus, None) unchanged.

    The signals we look at (all soft, all summable up to the cap):
      - target_roles: does any role in the user's list appear in the
        job title? Case-insensitive substring match.
      - salary_min/max: does the job's salary band overlap the user's
        desired range? Either side may be missing — we only fire the
        bonus when both sides have *something* to compare.
      - preferred_work_arrangement: matches job.work_arrangement.
        'any' on the user side is a wildcard.
      - acceptable_regions: does the job location include any of the
        user's regions?
    """
    if not preferences:
        return base_score, base_bonus, None

    bonus = 0.0
    notes: list[str] = []

    title = (job.get("title") or "").lower()
    target_roles = preferences.get("target_roles") or []
    for role in target_roles:
        if not isinstance(role, str):
            continue
        if not role.strip():
            continue
        if role.lower() in title:
            bonus += ROLE_BONUS
            notes.append(f"target role match ({role})")
            break  # one role match is enough; don't compound

    arrangement = preferences.get("preferred_work_arrangement")
    if arrangement and arrangement != "any":
        job_arrangement = job.get("work_arrangement")
        # The jobs table uses "on_site" while preferences uses "onsite"
        # — handle both spellings so a hyphen difference doesn't break
        # the match.
        normalised = (job_arrangement or "").replace("_", "").lower()
        if normalised == arrangement.replace("_", "").lower():
            bonus += ARRANGEMENT_BONUS
            notes.append(f"{arrangement} arrangement")

    user_min = preferences.get("salary_min")
    user_max = preferences.get("salary_max")
    job_min = job.get("salary_min")
    job_max = job.get("salary_max")
    if (user_min or user_max) and (job_min or job_max):
        # Treat missing bounds as open-ended. Overlap is the
        # cheap-but-correct check: ranges overlap iff
        #   user_lo <= job_hi  AND  job_lo <= user_hi
        user_lo = user_min if user_min is not None else 0
        user_hi = user_max if user_max is not None else float("inf")
        job_lo = job_min if job_min is not None else 0
        job_hi = job_max if job_max is not None else float("inf")
        if user_lo <= job_hi and job_lo <= user_hi:
            bonus += SALARY_BONUS
            notes.append("salary range overlap")

    job_location = (job.get("location") or "").lower()
    acceptable_regions = preferences.get("acceptable_regions") or []
    for region in acceptable_regions:
        if not isinstance(region, str):
            continue
        if not region.strip():
            continue
        if region.lower() in job_location:
            bonus += REGION_BONUS
            notes.append(f"region match ({region})")
            break

    if bonus == 0.0:
        return base_score, base_bonus, None

    capped_bonus = min(bonus, PREFERENCE_BONUS_CAP)
    adjusted_score = max(0.0, min(base_score + capped_bonus, 100.0))
    adjusted_bonus = base_bonus + capped_bonus
    note = "Preferences match: " + ", ".join(notes) + "."
    return adjusted_score, adjusted_bonus, note


async def store_matches(
    user_id: str, cv_id: str, matches: list[dict], supabase: Client
) -> int:
    """Upsert match results (handles re-matching after CV updates)."""
    rows = [
        {
            "user_id": user_id,
            "job_id": m["job_id"],
            "cv_id": cv_id,
            "score": m["final_score"],
            "vector_score": m["vector_score"],
            "skill_score": m["skill_score"],
            "bonus_score": m["bonus_score"],
            "matched_skills": m.get("matched_skills", []),
            "missing_skills": m.get("missing_skills", []),
            "status": "new",
        }
        for m in matches
    ]
    if not rows:
        return 0
    result = supabase.table("matches").upsert(rows, on_conflict="user_id,job_id").execute()
    return len(result.data) if result.data else 0


async def credit_matches_for_cycle(
    user_id: str,
    job_ids: list[str],
    supabase: Client,
    *,
    now: datetime | None = None,
) -> int:
    """Mark newly-delivered unique job matches as credited for this month."""
    unique_job_ids = list(dict.fromkeys([jid for jid in job_ids if jid]))
    if not unique_job_ids:
        return 0

    _, quota, active = await get_user_tier_limit(user_id, supabase)
    if not active:
        return 0

    credited = await get_credited_match_count(user_id, supabase, now=now)
    remaining = max(0, quota - credited)
    if remaining <= 0:
        return 0

    match_rows = (
        supabase.table("matches")
        .select("id, job_id, credited_at")
        .eq("user_id", user_id)
        .in_("job_id", unique_job_ids)
        .execute()
    )
    rows_by_job = {
        row.get("job_id"): row
        for row in (match_rows.data or [])
        if isinstance(row, dict) and row.get("job_id")
    }

    now_iso = (now or datetime.now(timezone.utc)).isoformat()
    newly_credited = 0
    for job_id in unique_job_ids:
        if newly_credited >= remaining:
            break
        row = rows_by_job.get(job_id)
        if row and row.get("credited_at"):
            continue
        query = supabase.table("matches").update({"credited_at": now_iso})
        if row and row.get("id"):
            query = query.eq("id", row["id"])
        else:
            query = query.eq("user_id", user_id).eq("job_id", job_id)
        query.is_("credited_at", "null").execute()
        newly_credited += 1
    return newly_credited


async def check_match_quota(user_id: str, supabase: Client) -> tuple[bool, int]:
    """Check remaining match quota. Returns (has_quota, remaining).

    Quota is now based on credited unique matches this month, not the
    legacy subscriptions.matches_used refresh counter.
    """
    _, quota, active = await get_user_tier_limit(user_id, supabase)
    if not active:
        return False, 0
    used = await get_credited_match_count(user_id, supabase)
    remaining = max(0, quota - used)
    return remaining > 0, remaining
