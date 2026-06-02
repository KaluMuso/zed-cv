"""Smoke tests for job listing routes."""
from unittest.mock import AsyncMock, patch

import pytest

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

    def test_strips_scraper_footer_lines(self):
        from app.api.v1.jobs import _strip_html

        html = "<p>Role summary</p><p>Scraped from bestjobs.co</p>"
        assert _strip_html(html) == "Role summary"


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

    def test_list_jobs_location_filter_returns_matching_job(
        self, client, fake_supabase
    ):
        """Regression for Sentry issue ZEDCV-BACKEND-C: filtering by
        location must return the matching rows, not silently degrade to
        an empty list. Root cause was `count="exact"` + ilike on a
        nested-join query tripping the Supabase free-tier Cloudflare
        Worker (CF error 1101 → APIError: JSON could not be generated),
        forcing the retry block to return JobList(jobs=[], total=0).
        Switching to `count="estimated"` keeps the upstream call cheap.

        Uses the real prod row 0aea31f8-5d55-4055-8969-922798a12ab1 as
        fixture data so the manual post-deploy smoke
        (GET /jobs?location=Livingstone) can cross-check against the
        same identifier.
        """
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "0aea31f8-5d55-4055-8969-922798a12ab1",
                        "title": "MAINTENANCE MANAGER",
                        "company": "David Livingstone",
                        "location": "Livingstone",
                        "description": "Lead the maintenance team.",
                        "source": "scraper",
                        "posted_at": "2026-05-15T00:00:00Z",
                        "is_active": True,
                    }
                ],
                count=1,
            ),
        )
        resp = client.get("/api/v1/jobs?location=Livingstone")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert len(body["jobs"]) == 1
        assert body["jobs"][0]["id"] == "0aea31f8-5d55-4055-8969-922798a12ab1"
        assert body["jobs"][0]["location"] == "Livingstone"

    def test_list_jobs_skills_come_from_second_query(
        self, client, fake_supabase
    ):
        """Path A regression: after splitting the embedded join into a
        separate `.in_("job_id", [...])` call on job_skills, the response
        must still carry skill names against the right jobs. Pins both
        the per-job mapping and the merged `skills` / `skills_required`
        list shape the frontend reads.
        """
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "job-A",
                        "title": "Accountant",
                        "company": "Co A",
                        "location": "Lusaka",
                        "description": "x",
                        "source": "scraper",
                        "posted_at": "2026-05-15T00:00:00Z",
                        "is_active": True,
                    },
                    {
                        "id": "job-B",
                        "title": "Driver",
                        "company": "Co B",
                        "location": "Lusaka",
                        "description": "y",
                        "source": "scraper",
                        "posted_at": "2026-05-15T00:00:00Z",
                        "is_active": True,
                    },
                ],
                count=2,
            ),
        )
        fake_supabase.set_table(
            "job_skills",
            FakeSupabaseQuery(
                data=[
                    {"job_id": "job-A", "skills": {"name": "accounting"}},
                    {"job_id": "job-A", "skills": {"name": "excel"}},
                    {"job_id": "job-B", "skills": {"name": "driving"}},
                ],
            ),
        )

        resp = client.get("/api/v1/jobs?location=Lusaka")
        assert resp.status_code == 200
        body = resp.json()

        by_id = {j["id"]: j for j in body["jobs"]}
        assert sorted(by_id["job-A"]["skills"]) == ["accounting", "excel"]
        assert by_id["job-B"]["skills"] == ["driving"]
        # `skills_required` mirrors `skills` for frontend compatibility.
        assert by_id["job-A"]["skills_required"] == by_id["job-A"]["skills"]

    def test_list_jobs_location_filter_uses_star_wildcard_not_percent(
        self, client, fake_supabase
    ):
        """Regression for Sentry issue ZEDCV-BACKEND-C: the location
        filter must produce a URL-safe wildcard. supabase-py 2.9.1
        leaves the raw `%` characters in the URL for the direct
        `.ilike(col, "%x%")` path (httpx's QueryParams treats them as
        literal, producing `…location=ilike.%Lusaka%…` — malformed
        percent-encoding). Upstream Cloudflare Worker rejects that with
        exception 1101 (`APIError: JSON could not be generated`),
        forcing the retry-degrade block to swallow the request. `*` is
        PostgREST's URL-safe wildcard, equivalent to `%` for ilike,
        and encodes cleanly to `%2A`.

        Verifies both: (a) the filter value handed to the supabase
        client has no `%` chars, (b) the response carries the matching
        Lusaka row instead of the degraded empty page that prod was
        emitting before this fix.
        """
        captured_ilike: list[tuple[str, str]] = []

        class _CapturingQuery(FakeSupabaseQuery):
            def ilike(self, column, value):  # type: ignore[override]
                captured_ilike.append((column, value))
                return self

        fake_supabase.set_table(
            "jobs",
            _CapturingQuery(
                data=[
                    {
                        "id": "lusaka-1",
                        "title": "Accountant",
                        "company": "Co",
                        "location": "Lusaka",
                        "description": "x",
                        "source": "manual",
                        "posted_at": "2026-05-18T00:00:00Z",
                        "is_active": True,
                    }
                ],
                count=1,
            ),
        )

        resp = client.get("/api/v1/jobs?location=Lusaka")
        assert resp.status_code == 200
        body = resp.json()
        # Behavioural: not degraded.
        assert body["total"] == 1
        assert len(body["jobs"]) == 1
        assert body["jobs"][0]["location"] == "Lusaka"
        # URL-safety: every captured ilike value uses `*`, never `%`.
        assert captured_ilike, "expected list_jobs to call .ilike()"
        assert ("location", "*Lusaka*") in captured_ilike
        for column, value in captured_ilike:
            assert "%" not in value, (
                f"raw `%` in filter value {value!r} for column {column!r} "
                "would re-introduce CF 1101 (ZEDCV-BACKEND-C)"
            )

    def test_list_jobs_employment_type_filter_accepted(
        self, client, fake_supabase
    ):
        captured_in: list[tuple[str, list[str]]] = []

        class _CapturingQuery(FakeSupabaseQuery):
            def in_(self, column, values):  # type: ignore[override]
                captured_in.append((column, list(values)))
                return self

        fake_supabase.set_table("jobs", _CapturingQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs?employment_type=full_time,contract")
        assert resp.status_code == 200
        assert ("employment_type", ["full_time", "contract"]) in captured_in

    def test_list_jobs_work_arrangement_filter_accepted(
        self, client, fake_supabase
    ):
        captured_in: list[tuple[str, list[str]]] = []

        class _CapturingQuery(FakeSupabaseQuery):
            def in_(self, column, values):  # type: ignore[override]
                captured_in.append((column, list(values)))
                return self

        fake_supabase.set_table("jobs", _CapturingQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs?work_arrangement=remote,hybrid")
        assert resp.status_code == 200
        assert ("work_arrangement", ["remote", "hybrid"]) in captured_in

    def test_list_jobs_has_salary_filter_uses_or_clause(
        self, client, fake_supabase
    ):
        captured_or: list[str] = []

        class _CapturingQuery(FakeSupabaseQuery):
            def or_(self, clause, *args, **kwargs):  # type: ignore[override]
                captured_or.append(clause)
                return self

        fake_supabase.set_table("jobs", _CapturingQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs?has_salary=true")
        assert resp.status_code == 200
        assert "salary_min.not.is.null,salary_max.not.is.null" in captured_or

    def test_list_jobs_saved_only_requires_auth(self, client, fake_supabase):
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs?saved_only=true")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "auth_required"

    def test_list_jobs_saved_only_short_circuits_when_empty(
        self, client, auth_headers, fake_supabase
    ):
        fake_supabase.set_table("saved_jobs", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs?saved_only=true", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["jobs"] == []
        assert body["total"] == 0

    def test_list_jobs_default_feed_filters_visibility_status(
        self, client, fake_supabase
    ):
        captured_in: list[tuple[str, list[str]]] = []

        class _CapturingQuery(FakeSupabaseQuery):
            def in_(self, column, values):  # type: ignore[override]
                captured_in.append((column, list(values)))
                return self

        fake_supabase.set_table("jobs_user_facing", _CapturingQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 200
        vis_filters = [v for col, v in captured_in if col == "visibility_status"]
        assert vis_filters and set(vis_filters[0]) == {"open", "recently_closed"}

    def test_list_jobs_include_archived_skips_visibility_filter(
        self, client, fake_supabase
    ):
        captured_in: list[tuple[str, list[str]]] = []

        class _CapturingQuery(FakeSupabaseQuery):
            def in_(self, column, values):  # type: ignore[override]
                captured_in.append((column, list(values)))
                return self

        fake_supabase.set_table("jobs_user_facing", _CapturingQuery(data=[], count=0))
        resp = client.get("/api/v1/jobs?include_archived=true")
        assert resp.status_code == 200
        assert not any(col == "visibility_status" for col, _ in captured_in)


class TestJobCreate:
    @patch("app.api.v1.jobs.resolve_skill_ids", new_callable=AsyncMock)
    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_create_job_success(
        self, mock_embed, mock_resolve, client, auth_headers, fake_supabase
    ):
        """Creates a job with embedding and dedup fingerprint."""
        mock_embed.return_value = [0.1] * 1536
        mock_resolve.return_value = []
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
    def test_ingest_accepts_short_title_chef(
        self, mock_embed, client, fake_supabase
    ):
        """Short titles like 'Chef' must not 422 the scraper batch."""
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(data=[{"id": "job-chef-1"}]),
        )
        fake_supabase.set_table("skills", FakeSupabaseQuery(data=[]))

        chef = {
            **self.SAMPLE_JOB,
            "title": "Chef",
            "company": "Hotel A",
            "description": (
                "Hotel kitchen chef preparing meals for guests and managing "
                "stock in Lusaka."
            ),
            "source_url": "https://gozambiajobs.com/jobs/chef-hotel-a/",
        }

        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [chef]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ingested"] == 1
        assert body["errors"] == []

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_invalid_row_does_not_fail_batch(
        self, mock_embed, client, fake_supabase
    ):
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "jobs", FakeSupabaseQuery(data=[{"id": "job-valid-1"}])
        )
        fake_supabase.set_table("skills", FakeSupabaseQuery(data=[]))

        bad = {**self.SAMPLE_JOB, "title": "AB", "description": "too short"}
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [self.SAMPLE_JOB, bad]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ingested"] == 1
        assert len(body["errors"]) == 1
        assert body["errors"][0]["index"] == 1

    @patch(
        "app.api.v1.jobs.resolve_apply_contacts_from_aggregator_url",
        new_callable=AsyncMock,
    )
    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_resolves_aggregator_apply_url(
        self, mock_embed, mock_resolve, client, fake_supabase
    ):
        """Aggregator apply_url is replaced with employer URL before insert."""
        from app.services.job_page_text_extractor import ApplyContacts

        mock_embed.return_value = [0.1] * 768
        mock_resolve.return_value = ApplyContacts(
            apply_url="https://wd1.myworkdaysite.com/recruiting/abinbev/job/1"
        )
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        jobs_table = FakeSupabaseQuery(data=[])
        fake_supabase.set_table("jobs", jobs_table)
        fake_supabase.set_table("skills", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [self.SAMPLE_JOB]},
        )
        assert resp.status_code == 200
        assert resp.json()["ingested"] == 1
        mock_resolve.assert_awaited_once()
        inserted = jobs_table._data[0]
        assert inserted["apply_url"] == (
            "https://wd1.myworkdaysite.com/recruiting/abinbev/job/1"
        )
        assert inserted.get("apply_source") == "enriched"

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_dedupes_existing_fingerprint(
        self, mock_embed, client, fake_supabase
    ):
        """Fingerprint match merges provenance onto the existing row."""
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table(
            "job_fingerprints",
            FakeSupabaseQuery(data=[{"job_id": "already-here"}]),
        )
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "already-here",
                        "apply_url": None,
                        "apply_email": None,
                        "contact_phone": None,
                        "admin_published": None,
                        "scraping_sources": [],
                        "source_url": None,
                    }
                ]
            ),
        )

        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [self.SAMPLE_JOB]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ingested"] == 0
        assert body["merged"] == 1
        assert body["duplicates"] == 0

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


# ─── task #60: richer job schema ──────────────────────────────────────


class TestSalaryParseToNgwee:
    """`_parse_salary_to_ngwee` is the ingest fallback that runs when a
    scraper emits free-text salary like 'K15,000 - K20,000' instead of
    integer min/max. Tests pin the parsing behaviour so future changes to
    the regex don't silently break existing ingests."""

    @pytest.mark.parametrize(
        "raw, expected_min_ngwee, expected_max_ngwee",
        [
            # Single value: both ends set to the same number.
            ("K15,000", 1_500_000, 1_500_000),
            ("K 15,000", 1_500_000, 1_500_000),
            ("ZMW 15000", 1_500_000, 1_500_000),
            # Range: min/max distinct, order-tolerant.
            ("K15,000 - K20,000", 1_500_000, 2_000_000),
            ("K20,000 to K15,000", 1_500_000, 2_000_000),
            ("ZMW 15000-20000/month", 1_500_000, 2_000_000),
            # k suffix.
            ("15k-20k", 1_500_000, 2_000_000),
            ("K15k", 1_500_000, 1_500_000),
            # m suffix (executive salaries).
            ("K3.5m", 350_000_000, 350_000_000),
        ],
    )
    def test_parses_known_zmw_shapes(self, raw, expected_min_ngwee, expected_max_ngwee):
        from app.schemas.jobs import _parse_salary_to_ngwee
        mn, mx = _parse_salary_to_ngwee(raw)
        assert mn == expected_min_ngwee
        assert mx == expected_max_ngwee

    @pytest.mark.parametrize(
        "raw",
        [
            "negotiable",
            "Salary: negotiable based on experience",
            "depends on experience",
            "TBD",
            "to be discussed",
            "competitive package",
            "",
            None,
            "   ",
        ],
    )
    def test_returns_none_for_placeholder_text(self, raw):
        """'negotiable' and friends must not accidentally extract a
        partial number from the surrounding text."""
        from app.schemas.jobs import _parse_salary_to_ngwee
        assert _parse_salary_to_ngwee(raw) == (None, None)

    @pytest.mark.parametrize(
        "raw",
        [
            "USD 5000-7000",     # no ZMW marker
            "$5000 per month",
            "£3000",
            "Naira 500,000",
        ],
    )
    def test_returns_none_for_non_zmw_currency(self, raw):
        """Non-ZMW values are intentionally not converted. The currency
        column carries the unit instead; this helper sticks to ngwee."""
        from app.schemas.jobs import _parse_salary_to_ngwee
        assert _parse_salary_to_ngwee(raw) == (None, None)

    def test_ignores_year_shaped_numbers(self):
        """Salary '2026' is almost certainly a year, not K2,026/month."""
        from app.schemas.jobs import _parse_salary_to_ngwee
        # Year-looking number should be filtered out; only the real
        # salary survives.
        assert _parse_salary_to_ngwee("K15,000 (posted 2026)") == (1_500_000, 1_500_000)

    def test_ignores_implausibly_small_amounts(self):
        """K200 is well below Zambian minimum monthly wage; treat as noise."""
        from app.schemas.jobs import _parse_salary_to_ngwee
        # Should pull the K15k and ignore the page-number '5'.
        assert _parse_salary_to_ngwee("page 5 — K15,000") == (1_500_000, 1_500_000)


class TestOrdinalDateParsing:
    """The WhatsApp channel often writes deadlines as '20th May 2026'.
    The tolerant date parser must strip the ordinal suffix before
    strptime, since Python's directives don't understand st/nd/rd/th."""

    def test_parses_ordinal_day(self):
        from app.schemas.jobs import _tolerant_parse_date
        from datetime import date
        assert _tolerant_parse_date("20th May 2026") == date(2026, 5, 20)

    def test_parses_first_third_second(self):
        from app.schemas.jobs import _tolerant_parse_date
        from datetime import date
        assert _tolerant_parse_date("1st June 2026") == date(2026, 6, 1)
        assert _tolerant_parse_date("3rd July 2026") == date(2026, 7, 3)
        assert _tolerant_parse_date("2nd August 2026") == date(2026, 8, 2)

    def test_iso_still_takes_precedence(self):
        """The ordinal strip should never get in the way of canonical ISO."""
        from app.schemas.jobs import _tolerant_parse_date
        from datetime import date
        assert _tolerant_parse_date("2026-05-20") == date(2026, 5, 20)

    def test_returns_none_on_truly_unparseable(self):
        from app.schemas.jobs import _tolerant_parse_date
        assert _tolerant_parse_date("sometime in May") is None


class TestJobIngestRicherFields:
    """Task #60 added optional structured fields to JobCreate. Ingest must
    accept them when present AND keep working when absent."""

    BASE_JOB = {
        "title": "Senior Backend Engineer",
        "company": "Airtel Zambia",
        "location": "Lusaka",
        "description": "We're hiring a senior backend engineer to lead the payments platform team.",
        "source": "scraper",
    }

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_accepts_all_new_fields(
        self, mock_embed, client, fake_supabase
    ):
        """A scraper row carrying every new structured field still ingests."""
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "jobs", FakeSupabaseQuery(data=[{"id": "job-rich-1"}])
        )

        full = {
            **self.BASE_JOB,
            "employment_type": "full_time",
            "work_arrangement": "hybrid",
            "hybrid_days_per_week": 3,
            "benefits": ["medical aid", "13th cheque", "phone allowance"],
            "application_instructions": "Email CV + cover letter to careers@example.com",
            "reporting_structure": "Reports to the Head of Engineering",
            "manages_others": 4,
            "interview_process": "1. Phone screen 2. Tech test 3. Onsite panel",
            "tools_tech_stack": ["python", "postgres", "aws"],
            "success_metrics": "Reduce payment-flow p99 latency by 30%",
            "company_description": "Zambia's largest mobile money operator",
            "reference_number": "ENG-2026-042",
            "currency": "ZMW",
            "pay_frequency": "monthly",
            "bonus_structure": "Quarterly performance bonus up to 15%",
            "equity_offered": False,
        }

        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [full]},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["ingested"] == 1
        assert resp.json()["errors"] == []

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_still_works_with_no_new_fields(
        self, mock_embed, client, fake_supabase
    ):
        """Backwards-compat: a pre-#60 scraper payload (just the original
        fields) must ingest without 422 or insert errors."""
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "jobs", FakeSupabaseQuery(data=[{"id": "job-legacy-1"}])
        )

        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [self.BASE_JOB]},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["ingested"] == 1

    def test_ingest_rejects_invalid_employment_type(self, client, fake_supabase):
        """Unknown enum value is reported per-row — batch still returns 200."""
        bad = {**self.BASE_JOB, "employment_type": "totally-made-up"}
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [bad]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ingested"] == 0
        assert len(body["errors"]) == 1
        assert "employment_type" in body["errors"][0]["reason"].lower() or "validation" in body["errors"][0]["reason"]

    def test_ingest_rejects_invalid_work_arrangement(self, client, fake_supabase):
        bad = {**self.BASE_JOB, "work_arrangement": "in-the-cloud-somewhere"}
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [bad]},
        )
        assert resp.status_code == 200
        assert resp.json()["ingested"] == 0
        assert len(resp.json()["errors"]) == 1

    def test_ingest_rejects_invalid_pay_frequency(self, client, fake_supabase):
        bad = {**self.BASE_JOB, "pay_frequency": "fortnightly"}
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [bad]},
        )
        assert resp.status_code == 200
        assert resp.json()["ingested"] == 0
        assert len(resp.json()["errors"]) == 1

    def test_ingest_rejects_hybrid_days_out_of_range(self, client, fake_supabase):
        bad = {**self.BASE_JOB, "hybrid_days_per_week": 7}
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [bad]},
        )
        assert resp.status_code == 200
        assert resp.json()["ingested"] == 0
        assert len(resp.json()["errors"]) == 1

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_uses_salary_text_when_ints_missing(
        self, mock_embed, client, fake_supabase
    ):
        """salary_text fallback path: scraper sends a free-form salary
        string with no min/max ints; ingest derives them. The salary_text
        field itself is dropped before insert (DB has no column)."""
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        captured_inserts: list[dict] = []

        class CapturingTable:
            def __init__(self):
                pass
            def select(self, *_a, **_k):
                return FakeSupabaseQuery(data=[])
            def insert(self, payload):
                captured_inserts.append(payload)
                return FakeSupabaseQuery(data=[{"id": "captured-1"}])

        fake_supabase.set_table("jobs", CapturingTable())

        payload = {**self.BASE_JOB, "salary_text": "K15,000 - K20,000"}
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [payload]},
        )
        assert resp.status_code == 200
        # The ingest should have populated min/max from salary_text AND
        # dropped salary_text from the insert payload.
        assert len(captured_inserts) == 1
        inserted = captured_inserts[0]
        assert inserted["salary_min"] == 1_500_000
        assert inserted["salary_max"] == 2_000_000
        assert "salary_text" not in inserted

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_does_not_override_existing_salary_ints(
        self, mock_embed, client, fake_supabase
    ):
        """When the scraper already provides salary_min/max ints, the
        salary_text helper must NOT override them — that data is more
        reliable than free-form text parsing."""
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        captured_inserts: list[dict] = []

        class CapturingTable:
            def select(self, *_a, **_k):
                return FakeSupabaseQuery(data=[])
            def insert(self, payload):
                captured_inserts.append(payload)
                return FakeSupabaseQuery(data=[{"id": "captured-2"}])

        fake_supabase.set_table("jobs", CapturingTable())

        payload = {
            **self.BASE_JOB,
            "salary_min": 999,  # bogus value just to prove it survives
            "salary_max": 9999,
            "salary_text": "K15,000 - K20,000",
        }
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [payload]},
        )
        assert resp.status_code == 200
        assert captured_inserts[0]["salary_min"] == 999
        assert captured_inserts[0]["salary_max"] == 9999


class _EnrichableJobsQuery(FakeSupabaseQuery):
    """Jobs table mock that applies update() to the stored row."""

    def __init__(self, row: dict):
        super().__init__(data=[dict(row)])
        self._row = dict(row)
        self.last_patch: dict | None = None
        self._single = False

    def update(self, data):
        self.last_patch = dict(data)
        self._row.update(data)
        self._data = [dict(self._row)]
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        from unittest.mock import MagicMock

        result = MagicMock()
        if self._single and self._data:
            result.data = self._data[0]
        else:
            result.data = self._data
        result.count = self._count
        return result


class TestJobEnrich:
    JOB_ID = "00000000-0000-0000-0000-000000000099"
    BASE_ROW = {
        "id": JOB_ID,
        "title": "Accountant",
        "description": "Manage books for a Lusaka firm with five years experience.",
        "source": "scraper",
        "posted_at": "2025-01-01T00:00:00Z",
        "is_active": True,
        "quality_score": 40,
        "is_enriched": False,
    }

    def test_enrich_rejects_without_credentials(self, client, fake_supabase):
        fake_supabase.set_table("jobs", _EnrichableJobsQuery(self.BASE_ROW))
        resp = client.patch(
            f"/api/v1/jobs/{self.JOB_ID}/enrich",
            json={"contact_email": "hr@employer.co.zm"},
        )
        assert resp.status_code == 401

    def test_enrich_rejects_wrong_ingest_key(self, client, fake_supabase):
        fake_supabase.set_table("jobs", _EnrichableJobsQuery(self.BASE_ROW))
        resp = client.patch(
            f"/api/v1/jobs/{self.JOB_ID}/enrich",
            json={"contact_email": "hr@employer.co.zm"},
            headers={"X-INGEST-API-KEY": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_enrich_with_ingest_key(self, client, fake_supabase):
        jobs_q = _EnrichableJobsQuery(self.BASE_ROW)
        fake_supabase.set_table("jobs", jobs_q)
        resp = client.patch(
            f"/api/v1/jobs/{self.JOB_ID}/enrich",
            json={
                "source_platform": "gozambiajobs",
                "original_source_url": "https://employer.example/jobs/42",
                "contact_whatsapp": "+260971234567",
            },
            headers={"X-INGEST-API-KEY": "test-ingest-key"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_enriched"] is True
        assert body["source_platform"] == "gozambiajobs"
        assert body["contact_whatsapp"] == "+260971234567"
        assert jobs_q.last_patch is not None
        assert jobs_q.last_patch["is_enriched"] is True
        assert jobs_q.last_patch["apply_source"] == "enriched"

    def test_enrich_404_when_job_missing(self, client, fake_supabase):
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[]))
        resp = client.patch(
            f"/api/v1/jobs/{self.JOB_ID}/enrich",
            json={"contact_email": "hr@employer.co.zm"},
            headers={"X-INGEST-API-KEY": "test-ingest-key"},
        )
        assert resp.status_code == 404

    def test_enrich_with_admin_jwt(self, client, fake_supabase, admin_headers):
        jobs_q = _EnrichableJobsQuery(self.BASE_ROW)
        fake_supabase.set_table("jobs", jobs_q)
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "admin-user-id",
                        "phone": "+260971111111",
                        "role": "admin",
                    }
                ]
            ),
        )
        resp = client.patch(
            f"/api/v1/jobs/{self.JOB_ID}/enrich",
            json={"contact_email": "careers@company.co.zm"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["contact_email"] == "careers@company.co.zm"
        assert jobs_q.last_patch["is_enriched"] is True
