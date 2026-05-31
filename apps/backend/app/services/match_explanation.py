"""Human-readable match explanations for v2 weighted scoring.

Explanations are rule-built (no LLM) so they stay free and cache-friendly.
The score breakdown chart in the UI carries the numeric detail; this text
should name concrete skills and one plain-language takeaway.
"""


def _format_skill_list(skills: list[str], *, max_shown: int = 4) -> str:
    cleaned = [s.strip() for s in skills if isinstance(s, str) and s.strip()]
    if not cleaned:
        return ""
    shown = cleaned[:max_shown]
    if len(cleaned) <= max_shown:
        return ", ".join(shown)
    extra = len(cleaned) - max_shown
    return f"{', '.join(shown)}, and {extra} more"


def _strength_phrase(
    *,
    semantic_score: float,
    skills_score: float,
    matched_skills: list[str],
) -> str:
    if matched_skills:
        skills_text = _format_skill_list(matched_skills)
        if skills_score >= 12:
            return f"Strong skill overlap on {skills_text}."
        return f"Your CV lines up on {skills_text}; semantic fit carries the rest of the score."
    if semantic_score >= 35:
        return "Your CV reads like a strong semantic fit for this role even without overlapping skill tags."
    if semantic_score >= 25:
        return "Solid CV–job similarity; add more role-specific keywords to lift the score."
    return "Moderate fit — consider tailoring your CV toward the job description."


def _gap_phrase(missing_skills: list[str] | None) -> str:
    missing = [s for s in (missing_skills or []) if isinstance(s, str) and s.strip()]
    if not missing:
        return ""
    gap = _format_skill_list(missing, max_shown=3)
    return f" To strengthen the match, highlight or build: {gap}."


def build_match_explanation(
    *,
    semantic_score: float,
    skills_score: float,
    experience_score: float,
    location_score: float,
    recency_score: float,
    matched_skills: list[str] | None = None,
    missing_skills: list[str] | None = None,
) -> str:
    """Concise, skill-first explanation for stored rows and API responses."""
    matched = list(matched_skills or [])
    lead = _strength_phrase(
        semantic_score=semantic_score,
        skills_score=skills_score,
        matched_skills=matched,
    )
    gap = _gap_phrase(missing_skills)

    # One compact line for power users who read the modal without opening breakdown.
    components = (
        f"Score mix: semantic {semantic_score:.0f}/50, skills {skills_score:.0f}/20, "
        f"experience {experience_score:.0f}/15, location {location_score:.0f}/10, "
        f"recency {recency_score:.0f}/5."
    )
    return f"{lead}{gap} {components}".strip()
