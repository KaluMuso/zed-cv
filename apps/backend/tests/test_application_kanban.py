"""Saved job application status API."""

from tests.conftest import FakeSupabaseQuery


def _job_row(job_id: str) -> dict:
    return {
        "id": job_id,
        "title": "Accountant",
        "company": "Zambeef",
        "location": "Lusaka",
        "description": "Manage accounts and reporting for regional operations.",
        "source": "manual",
        "source_url": "https://example.com/job",
        "apply_url": "https://example.com/apply",
        "posted_at": "2026-05-01T00:00:00+00:00",
        "closing_date": None,
        "salary_min": None,
        "salary_max": None,
        "employment_type": None,
        "work_arrangement": None,
        "quality_score": 80,
        "is_active": True,
        "requirements": [],
        "job_skills": [],
    }


def test_update_saved_job_status_requires_auth(client):
    resp = client.patch(
        "/api/v1/users/me/saved-jobs/00000000-0000-0000-0000-000000000001/status",
        json={"status": "applied"},
    )
    assert resp.status_code in (401, 403)


def test_update_saved_job_status_not_found(client, auth_headers, fake_supabase):
    fake_supabase.set_table("saved_jobs", FakeSupabaseQuery(data=[]))
    resp = client.patch(
        "/api/v1/users/me/saved-jobs/00000000-0000-0000-0000-000000000001/status",
        json={"status": "applied"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_update_saved_job_status_success(client, auth_headers, fake_supabase):
    job_id = "00000000-0000-0000-0000-000000000001"
    saved_id = "00000000-0000-0000-0000-000000000099"
    fake_supabase.set_table(
        "saved_jobs",
        FakeSupabaseQuery(
            data=[
                {
                    "id": saved_id,
                    "job_id": job_id,
                    "application_status": "saved",
                    "application_notes": None,
                    "interview_date": None,
                    "status_updated_at": "2026-05-01T00:00:00+00:00",
                    "jobs": _job_row(job_id),
                }
            ]
        ),
    )
    fake_supabase.set_table("application_status_history", FakeSupabaseQuery(data=[]))

    resp = client.patch(
        f"/api/v1/users/me/saved-jobs/{job_id}/status",
        json={"status": "applied", "notes": "Sent CV", "interview_date": "2026-05-28"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["application_status"] == "applied"
    assert body["application_notes"] == "Sent CV"
    assert body["interview_date"] == "2026-05-28"


def test_update_saved_job_status_rejects_invalid_transition(
    client, auth_headers, fake_supabase
):
    job_id = "00000000-0000-0000-0000-000000000002"
    fake_supabase.set_table(
        "saved_jobs",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "00000000-0000-0000-0000-000000000098",
                    "job_id": job_id,
                    "application_status": "offered",
                    "application_notes": None,
                    "interview_date": None,
                    "status_updated_at": "2026-05-01T00:00:00+00:00",
                }
            ]
        ),
    )
    resp = client.patch(
        f"/api/v1/users/me/saved-jobs/{job_id}/status",
        json={"status": "saved"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_list_saved_jobs_includes_applications(client, auth_headers, fake_supabase):
    job_id = "00000000-0000-0000-0000-000000000003"
    fake_supabase.set_table(
        "saved_jobs",
        FakeSupabaseQuery(
            data=[
                {
                    "application_status": "interviewing",
                    "status_updated_at": "2026-05-01T00:00:00+00:00",
                    "application_notes": "Phone screen Friday",
                    "interview_date": "2026-05-29",
                    "created_at": "2026-05-01T00:00:00+00:00",
                    "jobs": _job_row(job_id),
                }
            ]
        ),
    )
    resp = client.get("/api/v1/users/me/saved-jobs", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["jobs"]) == 1
    assert len(body["applications"]) == 1
    assert body["applications"][0]["application_status"] == "interviewing"
    assert body["applications"][0]["application_notes"] == "Phone screen Friday"
