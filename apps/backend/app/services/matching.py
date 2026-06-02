"""Job matching — delegates to Supabase RPC for hybrid scoring."""
from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client
from app.core.config import get_settings
from app.core.tier_gating import get_effective_match_limit
from app.services.match_explanation import build_match_explanation


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
    """Return (tier, monthly quota, active). Quota respects welcome bonus on free."""
    quota = await get_effective_match_limit(user_id, supabase)
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
        return tier, quota, active

    user_res = (
        supabase.table("users")
        .select("subscription_tier")
        .eq("id", user_id)
        .single()
        .execute()
    )
    user = _first_row(user_res.data) or {}
    tier = user.get("subscription_tier") or "free"
    return tier, quota, True


async def _billing_period_start(
    user_id: str,
    supabase: Client,
    *,
    now: datetime | None = None,
) -> datetime:
    """Start of the current billing window for match quota counting.

    Uses subscriptions.current_period_start for active paid rows; falls back
    to calendar month start for free users without a period.
    """
    sub_res = (
        supabase.table("subscriptions")
        .select("current_period_start, status")
        .eq("user_id", user_id)
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    sub = _first_row(sub_res.data)
    period_start = _parse_period_start(sub.get("current_period_start") if sub else None)
    if period_start is not None:
        return period_start
    return _month_start(now)


def _parse_period_start(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


async def get_credited_match_count(
    user_id: str,
    supabase: Client,
    *,
    now: datetime | None = None,
) -> int:
    period_start = await _billing_period_start(user_id, supabase, now=now)
    result = (
        supabase.table("matches")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("credited_at", period_start.isoformat())
        .execute()
    )
    if result.count is not None:
        return int(result.count)
    return len(result.data or [])


def normalize_rpc_match_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map match_jobs_for_user RPC output to persisted match row shape."""
    semantic = float(row.get("semantic_score") or row.get("vector_score") or 0)
    skills = float(row.get("skills_score") or row.get("skill_score") or 0)
    experience = float(row.get("experience_score") or 0)
    location = float(row.get("location_score") or 0)
    recency = float(row.get("recency_score") or 0)
    if location == 0 and recency == 0:
        legacy_bonus = float(row.get("bonus_score") or 0)
        location = legacy_bonus
    final = float(
        row.get("score")
        or row.get("final_score")
        or semantic + skills + experience + location + recency
    )
    matched = list(row.get("matched_skills") or [])
    missing = list(row.get("missing_skills") or [])
    explanation = row.get("explanation") or build_match_explanation(
        semantic_score=semantic,
        skills_score=skills,
        experience_score=experience,
        location_score=location,
        recency_score=recency,
        matched_skills=matched,
        missing_skills=missing,
    )
    return {
        "job_id": row["job_id"],
        "final_score": final,
        "vector_score": semantic,
        "skill_score": skills,
        "bonus_score": location + recency,
        "experience_score": experience,
        "location_score": location,
        "recency_score": recency,
        "semantic_score": semantic,
        "skills_score": skills,
        "matched_skills": matched,
        "missing_skills": missing,
        "explanation": explanation,
    }


async def run_matching_for_user(
    user_id: str, supabase: Client, limit: int = 50, min_score: float = 50.0
) -> list[dict]:
    """Execute hybrid matching via the match_jobs_for_user() RPC function.

    The RPC hard-floors stored rows at score 35 (migration 060). Callers pass
    min_score (default 50 on HTTP routes) to filter what users see in feeds.
    """
    try:
        result = supabase.rpc(
            "match_jobs_for_user",
            {"p_user_id": user_id, "p_limit": limit, "p_min_score": min_score},
        ).execute()
    except Exception as exc:
        message = str(exc)
        if "no primary CV with embedding" in message.lower():
            raise ValueError("Upload a CV with a completed embedding before matching") from exc
        raise
    return [normalize_rpc_match_row(row) for row in (result.data or [])]


async def fetch_jobs_by_ids(job_ids: list[str], supabase: Client) -> dict[str, dict[str, Any]]:
    """Load active job rows keyed by id for RPC match hydration."""
    if not job_ids:
        return {}
    result = (
        supabase.table("jobs")
        .select("*")
        .in_("id", job_ids)
        .eq("is_active", True)
        .execute()
    )
    return {
        str(row["id"]): row
        for row in (result.data or [])
        if isinstance(row, dict) and row.get("id")
    }


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
    user_id: str,
    cv_id: str,
    matches: list[dict],
    supabase: Client,
    *,
    batch_run_id: str | None = None,
    batch_run_at: str | None = None,
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
            "experience_score": m.get("experience_score"),
            "location_score": m.get("location_score"),
            "recency_score": m.get("recency_score"),
            "matched_skills": m.get("matched_skills", []),
            "missing_skills": m.get("missing_skills", []),
            "explanation": m.get("explanation"),
            "status": "new",
            **(
                {"batch_run_id": batch_run_id, "batch_run_at": batch_run_at}
                if batch_run_id
                else {}
            ),
        }
        for m in matches
    ]
    if not rows:
        return 0

    dismissed_res = (
        supabase.table("matches")
        .select("job_id")
        .eq("user_id", user_id)
        .eq("status", "dismissed")
        .execute()
    )
    dismissed_job_ids = {
        str(r["job_id"]) for r in (dismissed_res.data or []) if r.get("job_id")
    }
    for row in rows:
        if str(row["job_id"]) in dismissed_job_ids:
            row["status"] = "dismissed"

    result = supabase.table("matches").upsert(rows, on_conflict="user_id,job_id").execute()
    return len(result.data) if result.data else 0


async def credit_matches_for_cycle(
    user_id: str,
    job_ids: list[str],
    supabase: Client,
    *,
    now: datetime | None = None,
) -> list[str]:
    """Mark newly-delivered unique job matches as credited for this month.

    Returns job_ids that received credited_at in this call (empty if none).
    """
    unique_job_ids = list(dict.fromkeys([jid for jid in job_ids if jid]))
    if not unique_job_ids:
        return []

    _, quota, active = await get_user_tier_limit(user_id, supabase)
    if not active:
        return []

    credited = await get_credited_match_count(user_id, supabase, now=now)
    remaining = max(0, quota - credited)
    if remaining <= 0:
        return []

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
    newly_credited_ids: list[str] = []
    for job_id in unique_job_ids:
        if len(newly_credited_ids) >= remaining:
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
        newly_credited_ids.append(job_id)
    return newly_credited_ids


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
