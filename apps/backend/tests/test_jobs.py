"""Smoke tests for job listing routes."""
from unittest.mock import AsyncMock, patch
from tests.conftest import FakeSupabaseQuery


class TestStripHtml:
    """`_strip_html` must remove real HTML tags but leave non-HTML angle
    brackets alone — job descriptions routinely contain literal `<...>`
    in salary ranges, emails, placeholders, and comparisons. Stripping
    those would silently lose ingested data (description is mutated in
    place before fingerprinting, embedding, and storage)."""

    def test_strips_real_html(self):
        from app.api.v1.jobs import _strip_html
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"
        assert _strip_html("<H1>Title</H1>") == "Title"
        assert _strip_html('<div class="x">Hi</div>') == "Hi"

    def test_paragraph_breaks(self):
        from app.api.v1.jobs import _strip_html
        assert _strip_html("<p>First.</p><p>Second.</p>") == "First.\n\nSecond."

    def test_lists_become_bullets(self):
        from app.api.v1.jobs import _strip_html
        assert (
            _strip_html("<ul><li>One</li><li>Two</li></ul>")
            == "• One\n• Two"
        )

    def test_br_becomes_newline(self):
        from app.api.v1.jobs import _strip_html
        assert (
            _strip_html("Line one<br>Line two<br/>Line three")
            == "Line one\nLine two\nLine three"
        )

    def test_entities_unescaped(self):
        from app.api.v1.jobs import _strip_html
        assert _strip_html("A &amp; B") == "A & B"

    def test_preserves_salary_range_with_angle_brackets(self):
        """Regression: previously '<K15000 - K30000>' got eaten by the
        catch-all `<[^>]+>` regex, silently destroying salary data on
        every scraped ingest and on the backfill endpoint."""
        from app.api.v1.jobs import _strip_html
        s = "Salary range: <K15000 - K30000> ZMW per month."
        assert _strip_html(s) == s

    def test_preserves_email_in_angle_brackets(self):
        """Regression: '<user@host>' is a common contact format in
        scraped job postings. Stripping it loses the only way to apply."""
        from app.api.v1.jobs import _strip_html
        s = "Apply via <careers@company.com>"
        assert _strip_html(s) == s

    def test_preserves_template_placeholders(self):
        from app.api.v1.jobs import _strip_html
        s = "Required: <relevant degree>. Must have <2 years experience>."
        assert _strip_html(s) == s

    def test_preserves_lone_comparisons(self):
        from app.api.v1.jobs import _strip_html
        s = "Latency must be < 10ms but > 2ms baseline."
        assert _strip_html(s) == s


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

    def test_list_jobs_accepts_sort_recent(self, client, fake_supabase):
        """sort=recent is the default; route should accept it without 422."""
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs?sort=recent")
        assert resp.status_code == 200

    def test_list_jobs_accepts_sort_closing(self, client, fake_supabase):
        """sort=closing emits a `not.is.null` filter on closing_date."""
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs?sort=closing")
        assert resp.status_code == 200

    def test_list_jobs_unknown_sort_falls_back(self, client, fake_supabase):
        """Unknown sort should fall back silently to 'recent' (no 400)."""
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs?sort=does-not-exist")
        assert resp.status_code == 200

    def test_list_jobs_short_circuits_unknown_skill(self, client, fake_supabase):
        """If the requested skill names resolve to zero skill_ids, return
        an empty list immediately — don't burn the main query."""
        fake_supabase.set_table("skills", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table("skill_aliases", FakeSupabaseQuery(data=[]))
        resp = client.get("/api/v1/jobs?skills=quantum-clog-dancing")
        assert resp.status_code == 200
        body = resp.json()
        assert body["jobs"] == []
        assert body["total"] == 0

    def test_list_jobs_source_filter_accepted(self, client, fake_supabase):
        """source=manual,scraper passes type-check and reaches the query."""
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs?source=manual,scraper")
        assert resp.status_code == 200


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

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_skips_aggregator_cross_listing(
        self, mock_embed, client, fake_supabase
    ):
        """A job whose apply_url points at a blacklisted aggregator
        (e.g. zimbojobs.com) is counted in `skipped`, never embedded,
        never written. Filter runs BEFORE the Gemini call so we don't
        burn embedding quota on noise."""
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))

        cross_listed = dict(self.SAMPLE_JOB)
        cross_listed["title"] = "Software Engineer at Acme"
        cross_listed["apply_url"] = "https://www.zimbojobs.com/jobs/12345"
        cross_listed["source_url"] = "https://www.zimbojobs.com/jobs/12345"

        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [cross_listed]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ingested"] == 0
        assert body["duplicates"] == 0
        assert body["skipped"] == 1
        assert body["errors"] == []
        # The filter must short-circuit before embedding to save Gemini quota.
        mock_embed.assert_not_called()

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_skip_filter_is_case_insensitive(
        self, mock_embed, client, fake_supabase
    ):
        """Blacklist match must be case-insensitive — scrapers don't
        normalize URLs."""
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))

        cross_listed = dict(self.SAMPLE_JOB)
        cross_listed["apply_url"] = "HTTPS://WWW.ZIMBOJOBS.COM/JOBS/abc"
        cross_listed["source_url"] = None

        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [cross_listed]},
        )
        assert resp.json()["skipped"] == 1
        mock_embed.assert_not_called()
