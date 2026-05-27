"""Saved jobs API routes."""

from tests.conftest import FakeSupabaseQuery


def test_save_job_requires_auth(client):
    resp = client.post("/api/v1/jobs/00000000-0000-0000-0000-000000000099/save")
    assert resp.status_code in (401, 403)


def test_save_job_404_when_job_missing(client, auth_headers, fake_supabase):
    fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[]))
    resp = client.post(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000099/save",
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_save_job_returns_saved_true(client, auth_headers, fake_supabase):
    jid = "00000000-0000-0000-0000-000000000001"
    fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[{"id": jid}]))
    fake_supabase.set_table("saved_jobs", FakeSupabaseQuery(data=[]))
    resp = client.post(f"/api/v1/jobs/{jid}/save", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"saved": True}


def test_unsave_job_returns_204(client, auth_headers, fake_supabase):
    jid = "00000000-0000-0000-0000-000000000002"
    fake_supabase.set_table("saved_jobs", FakeSupabaseQuery(data=[]))
    resp = client.delete(f"/api/v1/jobs/{jid}/save", headers=auth_headers)
    assert resp.status_code == 204


def test_list_saved_jobs_empty(client, auth_headers, fake_supabase):
    fake_supabase.set_table("saved_jobs", FakeSupabaseQuery(data=[]))
    resp = client.get("/api/v1/users/me/saved-jobs", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"jobs": [], "applications": []}
