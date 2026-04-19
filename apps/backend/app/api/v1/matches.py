"""Matching routes — trigger and retrieve job matches."""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from app.core.deps import get_supabase, get_current_user_id
from app.schemas.matching import MatchResult, MatchList
from app.schemas.jobs import Job
from app.services.matching import run_matching_for_user, store_matches, check_match_quota

router = APIRouter(prefix="/matches", tags=["Matching"])


@router.get("", response_model=MatchList)
async def get_matches(
    min_score: float = Query(50, ge=0, le=100),
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Get stored job matches for the current user."""
    has_quota, remaining = await check_match_quota(user_id, supabase)

    result = (
        supabase.table("matches")
        .select("*, jobs(*)")
        .eq("user_id", user_id)
        .gte("score", min_score)
        .order("score", desc=True)
        .limit(limit)
        .execute()
    )

    matches = []
    for m in result.data or []:
        job_data = m.pop("jobs", {})
        matches.append(
            MatchResult(
                id=m["id"],
                job=Job(**job_data),
                score=m["score"],
                vector_score=m["vector_score"],
                skill_score=m["skill_score"],
                bonus_score=m["bonus_score"],
                matched_skills=m.get("matched_skills", []),
                missing_skills=m.get("missing_skills", []),
                explanation=m.get("explanation"),
                created_at=m["created_at"],
            )
        )

    return MatchList(matches=matches, remaining_quota=remaining)


@router.post("/trigger")
async def trigger_matching(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Trigger job matching for the current user.

    Runs in background to avoid timeout on large job databases.
    """
    has_quota, remaining = await check_match_quota(user_id, supabase)

    if not has_quota:
        raise HTTPException(
            status_code=403,
            detail="Monthly match quota exceeded. Upgrade your plan for more matches.",
        )

    # Check user has a primary CV
    cv_result = (
        supabase.table("cvs")
        .select("id")
        .eq("user_id", user_id)
        .eq("is_primary", True)
        .limit(1)
        .execute()
    )

    if not cv_result.data:
        raise HTTPException(
            status_code=422,
            detail="Upload a CV first before matching",
        )

    cv_id = cv_result.data[0]["id"]

    # Run matching in background
    background_tasks.add_task(_run_matching_task, user_id, cv_id, supabase)

    return {
        "message": "Matching started. Results will be available shortly.",
        "estimated_seconds": 15,
    }


async def _run_matching_task(user_id: str, cv_id: str, supabase):
    """Background task to run matching and store results."""
    matches = await run_matching_for_user(user_id, supabase)
    await store_matches(user_id, cv_id, matches, supabase)

    # Increment matches_used
    sub_result = (
        supabase.table("subscriptions")
        .select("matches_used")
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    if sub_result.data:
        new_count = sub_result.data["matches_used"] + 1
        supabase.table("subscriptions").update(
            {"matches_used": new_count}
        ).eq("user_id", user_id).execute()
