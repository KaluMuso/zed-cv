"""Human-readable match explanations for v2 weighted scoring."""


def build_match_explanation(
    *,
    semantic_score: float,
    skills_score: float,
    experience_score: float,
    location_score: float,
    recency_score: float,
    matched_skills: list[str] | None = None,
) -> str:
    """Summarise all five score components for UI / stored explanation."""
    parts = [
        f"Semantic fit {semantic_score:.0f}/50",
        f"required skills {skills_score:.0f}/20",
        f"experience {experience_score:.0f}/15",
        f"location {location_score:.0f}/10",
        f"recency {recency_score:.0f}/5",
    ]
    base = "; ".join(parts) + "."
    matched = matched_skills or []
    if matched:
        shown = ", ".join(matched[:5])
        suffix = f" Matched on: {shown}."
        if len(matched) > 5:
            suffix = f" Matched on: {shown}, and {len(matched) - 5} more."
        return base + suffix
    if semantic_score >= 25:
        return base + " Strong CV–job similarity despite few overlapping skill tags."
    return base
