"""Smoke tests for job listing routes."""
from unittest.mock import AsyncMock, patch
from tests.conftest import FakeSupabaseQuery


class TestJobList:
    def test_list_jobs_unauthenticated(self, client):
        """Job list requires auth (until public browsing is enabled)."""
        resp = client.get("/api/v1/jobs")
        assert resp.status_code in (401, 403)

    def test_list_jobs_empty(self, client, auth_headers, fake_supabase):
        """Returns empty list when no jobs exist."""
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["jobs"] == []
        assert body["total"] == 0

    def test_list_jobs_with_results(self, client, auth_headers, fake_supabase):
        """Returns formatted jobs."""
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "job-1",
                        "title": "Python Developer",
                        "company": "TechCo",
                        "location": "Lusaka",
                        "description": "Build APIs",
                        "source": "manual",
                        "posted_at": "2025-01-01T00:00:00Z",
                        "is_active": True,
                    }
                ],
                count=1,
            ),
        )
        resp = client.get("/api/v1/jobs", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["jobs"]) == 1
        assert body["jobs"][0]["title"] == "Python Developer"


class TestJobCreate:
    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_create_job_success(
        self, mock_embed, client, auth_headers, fake_supabase
    ):
        """Creates a job with embedding and dedup fingerprint."""
        mock_embed.return_value = [0.1] * 1536
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "job-new",
                        "title": "React Developer Needed",
                        "company": "StartupX",
                        "description": "Build modern UIs",
                        "location": "Kitwe",
                        "source": "manual",
                        "posted_at": "2025-01-01T00:00:00Z",
                        "is_active": True,
                    }
                ]
            ),
        )
        fake_supabase.set_table("skills", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/jobs",
            headers=auth_headers,
            json={
                "title": "React Developer Needed",
                "company": "StartupX",
                "description": "Build modern UIs with React and TypeScript for our platform",
                "location": "Kitwe",
                "source": "manual",
                "skills_required": ["react", "typescript"],
            },
        )
        assert resp.status_code == 201

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_create_job_duplicate_rejected(
        self, mock_embed, client, auth_headers, fake_supabase
    ):
        """Rejects duplicate jobs based on fingerprint."""
        mock_embed.return_value = [0.1] * 1536
        fake_supabase.set_table(
            "job_fingerprints",
            FakeSupabaseQuery(data=[{"job_id": "existing-job"}]),
        )
        resp = client.post(
            "/api/v1/jobs",
            headers=auth_headers,
            json={
                "title": "React Developer Needed",
                "company": "StartupX",
                "description": "Build modern UIs with React and TypeScript for our platform",
                "location": "Kitwe",
                "source": "manual",
            },
        )
        assert resp.status_code == 409
