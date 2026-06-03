"""Normalize raw PostgREST `jobs` rows (with optional `job_skills` embed) into Job."""

from app.schemas.jobs import Job


def skills_from_job_embed(job: dict) -> list[str]:
    """Extract skill names from a jobs row that includes job_skills(skills(name))."""
    skill_rows = job.get("job_skills") or []
    skills: list[str] = []
    for s in skill_rows:
        if isinstance(s, dict) and s.get("skills") and isinstance(s["skills"], dict):
            name = s["skills"].get("name")
            if isinstance(name, str) and name:
                skills.append(name)
    return skills


def hydrate_job_row(j: dict) -> Job:
    row = dict(j)
    skills = skills_from_job_embed(row)
    row.pop("job_skills", None)
    row["skills_required"] = skills
    row["skills"] = skills
    return Job(**row)
