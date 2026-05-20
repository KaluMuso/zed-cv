"""Experience-gap soft penalty for job matching (mirrors migration 032 RPC)."""

EXPERIENCE_PENALTY_FLOOR = 0.5
EXPERIENCE_PENALTY_STEP = 0.075


def experience_score_multiplier(
    user_years: int | None,
    job_min_years: int | None,
) -> float:
    """Return multiplier in [0.5, 1.0] — never filters, only scales final score."""
    if job_min_years is None:
        return 1.0
    user = user_years if user_years is not None else 0
    if user >= job_min_years:
        return 1.0
    gap = job_min_years - user
    return max(
        EXPERIENCE_PENALTY_FLOOR,
        1.0 - EXPERIENCE_PENALTY_STEP * gap,
    )
