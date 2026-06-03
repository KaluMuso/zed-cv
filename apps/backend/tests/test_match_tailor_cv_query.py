"""Regression: tailor-cv must not select jobs.skills (column does not exist)."""
from pathlib import Path


def test_tailor_cv_embeds_job_skills_not_jobs_skills_column():
    matches_py = (
        Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "matches.py"
    ).read_text()
    assert "job_skills(skills(name))" in matches_py
    assert "jobs(title, company, description, skills)" not in matches_py
