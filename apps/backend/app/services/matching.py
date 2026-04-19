"""Job matching service — hybrid vector + skill overlap scoring."""

from supabase import Client

from app.core.config import get_settings


async def run_matching_for_user(
    user_id: str,
    supabase: Client,
    limit: int = 20,
    min_score: float = 50.0,
) -> list[dict]:
    """Execute hybrid matching via Supabase RPC function.

    The heavy lifting (vector similarity + skill overlap + bonus signals)
    happens in PostgreSQL via the match_jobs_for_user() function.
    This keeps latency low and avoids pulling all jobs to Python.
    """
    result = supabase.rpc(
        "match_jobs_for_user",
        {
            "p_user_id": user_id,
            "p_limit": limit,
            "p_min_score": min_score,
        },
    ).execute()

    if not result.data:
        return []

    return result.data


async def store_matches(
    user_id: str,
    cv_id: str,
    matches: list[dict],
    supabase: Client,
) -> int:
    """Store match results in the matches table.

    Uses upsert to handle re-matching after CV updates.
    Returns count of matches stored.
    """
    rows = []
    for m in matches:
        rows.append(
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
        )

    if not rows:
        return 0

    result = supabase.table("matches").upsert(
        rows, on_conflict="user_id,job_id"
    ).execute()

    return len(result.data) if result.data else 0


async def check_match_quota(user_id: str, supabase: Client) -> tuple[bool, int]:
    """Check if user has remaining match quota for their tier.

    Returns (has_quota, remaining_count).
    """
    result = (
        supabase.table("subscriptions")
        .select("matches_used, matches_limit")
        .eq("user_id", user_id)
        .eq("status", "active")
        .single()
        .execute()
    )

    if not result.data:
        # No subscription = free tier defaults
        return True, 5

    used = result.data["matches_used"]
    limit = result.data["matches_limit"]
    remaining = max(0, limit - used)

    return remaining > 0, remaining
