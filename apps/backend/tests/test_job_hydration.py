"""job_hydration helpers."""
from app.services.job_hydration import hydrate_job_row, skills_from_job_embed


def test_skills_from_job_embed_flattens_postgrest_shape():
    job = {
        "title": "Engineer",
        "job_skills": [
            {"skills": {"name": "Python"}},
            {"skills": {"name": "SQL"}},
            {"skills": {}},
        ],
    }
    assert skills_from_job_embed(job) == ["Python", "SQL"]


def test_hydrate_job_row_sets_skills_required():
    row = {
        "id": "j1",
        "title": "Engineer",
        "description": "x" * 25,
        "source": "manual",
        "posted_at": "2026-01-01T00:00:00+00:00",
        "job_skills": [{"skills": {"name": "Excel"}}],
    }
    job = hydrate_job_row(row)
    assert job.skills_required == ["Excel"]
    assert job.skills == ["Excel"]
