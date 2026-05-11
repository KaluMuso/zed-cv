"""Smoke tests for job listing routes."""
from unittest.mock import AsyncMock, patch
from tests.conftest import FakeSupabaseQuery


class TestJobList:
    def test_list_jobs_public(self, client):
        """GET /jobs is intentionally public (per birds-eye doc §5)."""
        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 200

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
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[{"id": "test-user-id", "phone": "+260971234567", "role": "admin"}]
            ),
        )
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
            "users",
            FakeSupabaseQuery(
                data=[{"id": "test-user-id", "phone": "+260971234567", "role": "admin"}]
            ),
        )
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

    def test_create_job_forbidden_for_non_admin(
        self, client, auth_headers, fake_supabase
    ):
        """Authenticated free users cannot post jobs — must be admin/superadmin."""
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[{"id": "test-user-id", "phone": "+260971234567", "role": "user"}]
            ),
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
        assert resp.status_code == 403


class TestJobIngest:
    """POST /api/v1/jobs/ingest — bulk endpoint for n8n scraper."""

    SAMPLE_JOB = {
        "title": "Accounts Officer at TEVETA",
        "company": "TEVETA",
        "location": "Lusaka",
        "description": "VACANCY: TEVETA seeks an Accounts Officer to manage the books, reconcile MoMo, and handle monthly close.",
        "requirements": ["Degree in accounting", "ZICA member"],
        "skills_required": [],
        "salary_min": None,
        "salary_max": None,
        "apply_url": "https://jobwebzambia.com/jobs/accounts-officer-teveta/",
        "apply_email": None,
        "source": "scraper",
        "source_url": "https://jobwebzambia.com/jobs/accounts-officer-teveta/",
        "closing_date": None,
        "posted_at": "2026-05-08",
    }

    def test_ingest_rejects_missing_api_key(self, client, fake_supabase):
        """No api_key field → 422 (Pydantic missing-required-field)."""
        resp = client.post("/api/v1/jobs/ingest", json={"jobs": [self.SAMPLE_JOB]})
        assert resp.status_code == 422

    def test_ingest_rejects_wrong_api_key(self, client, fake_supabase):
        """Wrong api_key → 401, no leak of whether the server has one configured."""
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "definitely-not-the-key", "jobs": [self.SAMPLE_JOB]},
        )
        assert resp.status_code == 401

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_success_with_valid_key(
        self, mock_embed, client, fake_supabase
    ):
        """Valid batch with one job → ingested=1, duplicates=0."""
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(data=[{"id": "job-ingested-1"}]),
        )
        fake_supabase.set_table("skills", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [self.SAMPLE_JOB]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ingested"] == 1
        assert body["duplicates"] == 0
        assert body["errors"] == []

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_dedupes_existing_fingerprint(
        self, mock_embed, client, fake_supabase
    ):
        """Job already in job_fingerprints → counted as duplicate, not re-inserted."""
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table(
            "job_fingerprints",
            FakeSupabaseQuery(data=[{"job_id": "already-here"}]),
        )

        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [self.SAMPLE_JOB]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ingested"] == 0
        assert body["duplicates"] == 1
