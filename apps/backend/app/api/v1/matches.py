"""Matching routes."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from app.core.deps import get_supabase, get_current_user_id, get_current_user, is_superadmin
from app.core.rate_limit import limiter
from app.schemas.matching import MatchResult, MatchList
from app.schemas.jobs import Job
from app.services.matching import run_matching_for_user, store_matches, check_match_quota
from app.services.matching import apply_preferences_to_match
from app.services.email import send_match_digest_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["Matching"])


@router.get("", response_model=MatchList)
async def get_matches(
    min_score: float = Query(50, ge=0, le=100), limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id), supabase=Depends(get_supabase),
):
    has_quota, remaining = await check_match_quota(user_id, supabase)
    # Pull a wider candidate set than `limit` so the preferences-aware
    # re-rank below can actually move things around. Without this, a
    # 10-row LIMIT means re-ranking can only shuffle within 10 rows,
    # which defeats the purpose. 50 is a reasonable upper bound — the
    # RPC writes at most 20 per run today.
    candidate_limit = max(limit * 3, 30)
    result = (
        supabase.table("matches").select("*, jobs(*)").eq("user_id", user_id)
        .gte("score", min_score).order("score", desc=True).limit(candidate_limit).execute()
    )

    # Phase 2 Initiative #4 — preference-aware re-rank. Read the user's
    # row (None on fresh accounts; harmless — apply_preferences_to_match
    # treats None as no adjustment). Wrapped so a DB hiccup on the
    # preferences table never breaks /matches itself.
    preferences = None
    try:
        pref_res = (
            supabase.table("user_preferences")
            .select("target_roles, salary_min, salary_max, salary_frequency, "
                    "preferred_work_arrangement, acceptable_regions")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if pref_res.data:
            preferences = pref_res.data[0]
    except Exception:
        logger.warning("user_preferences read failed in /matches", exc_info=True)

    matches: list[MatchResult] = []
    for m in result.data or []:
        job_data = m.pop("jobs", {})
        adjusted_score, adjusted_bonus, adjustment_note = apply_preferences_to_match(
            base_score=m["score"],
            base_bonus=m["bonus_score"],
            job=job_data,
            preferences=preferences,
        )
        explanation = m.get("explanation") or ""
        if adjustment_note and adjustment_note not in explanation:
            explanation = (explanation + " " + adjustment_note).strip()
        matches.append(MatchResult(
            id=m["id"], job=Job(**job_data), score=adjusted_score,
            vector_score=m["vector_score"], skill_score=m["skill_score"],
            bonus_score=adjusted_bonus,
            matched_skills=m.get("matched_skills", []), missing_skills=m.get("missing_skills", []),
            explanation=explanation or None, created_at=m["created_at"],
        ))

    # Re-sort by the adjusted score and trim to the requested limit.
    matches.sort(key=lambda mr: mr.score, reverse=True)
    return MatchList(matches=matches[:limit], remaining_quota=remaining)


@router.post("/trigger")
@limiter.limit("3/minute")
async def trigger_matching(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    user_id = current_user["id"]

    # Superadmin bypasses quota check
    if not is_superadmin(current_user):
        has_quota, remaining = await check_match_quota(user_id, supabase)
        if not has_quota:
            raise HTTPException(status_code=403, detail="Monthly match quota exceeded. Upgrade your plan.")

    cv_result = supabase.table("cvs").select("id").eq("user_id", user_id).eq("is_primary", True).limit(1).execute()
    if not cv_result.data:
        raise HTTPException(status_code=422, detail="Upload a CV first before matching")

    background_tasks.add_task(_run_matching_task, user_id, cv_result.data[0]["id"], supabase)
    return {"message": "Matching started. Results will be available shortly.", "estimated_seconds": 15}


async def _run_matching_task(user_id: str, cv_id: str, supabase):
    # Background task: must not propagate exceptions (would crash the
    # worker silently). But we MUST log them — a silent except-pass here
    # is what hid the match_jobs_for_user 42804 type-mismatch in prod for
    # weeks (slice 2D-1f).
    try:
        matches = await run_matching_for_user(user_id, supabase)
        await store_matches(user_id, cv_id, matches, supabase)
        sub = supabase.table("subscriptions").select("matches_used").eq("user_id", user_id).single().execute()
        if sub.data:
            supabase.table("subscriptions").update({"matches_used": sub.data["matches_used"] + 1}).eq("user_id", user_id).execute()
        if matches:
            digest_rows = (
                supabase.table("matches")
                .select("score, jobs(title, company)")
                .eq("user_id", user_id)
                .order("score", desc=True)
                .limit(5)
                .execute()
            )
            try:
                await send_match_digest_email(user_id, digest_rows.data or [], supabase)
            except Exception:
                logger.warning(
                    "match digest email failed for user=%s", user_id, exc_info=True
                )
    except Exception:
        logger.error(
            "matching task failed for user=%s cv=%s", user_id, cv_id, exc_info=True
        )
