"""Ingest pipeline tests for job quality gates (migration 073)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.conftest import FakeSupabaseQuery


class TestJobIngestQualityGates:
    BASE = {
        "title": "Warehouse Assistant",
        "company": "Test Co",
        "location": "Lusaka",
        "description": "A" * 350,
        "source": "scraper",
        "source_url": "https://careers.testco.zm/jobs/1",
        "apply_url": "https://careers.testco.zm/apply",
    }

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_promotes_apply_url_when_source_url_missing(
        self, mock_embed, client, fake_supabase
    ):
        """Employer apply_url is copied to source_url when listing URL was omitted."""
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        jobs_q = FakeSupabaseQuery(data=[])
        fake_supabase.set_table("jobs", jobs_q)

        payload = {**self.BASE, "source_url": None}
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [payload]},
        )
        assert resp.status_code == 200
        assert resp.json()["ingested"] == 1
        inserted = jobs_q._data[0]
        assert inserted.get("source_url") == self.BASE["apply_url"]
        assert "missing_source_url" not in (inserted.get("deactivation_reason") or "")

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_deactivates_when_no_listing_url(
        self, mock_embed, client, fake_supabase
    ):
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        jobs_q = FakeSupabaseQuery(data=[])
        fake_supabase.set_table("jobs", jobs_q)

        payload = {
            **self.BASE,
            "source_url": None,
            "apply_url": None,
            "apply_email": None,
        }
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [payload]},
        )
        assert resp.status_code == 200
        assert resp.json()["ingested"] == 1
        inserted = jobs_q._data[0]
        assert inserted.get("is_active") is False
        # Apply-path gate sets terminal reason when no source_url to deep-enrich.
        assert inserted.get("deactivation_reason") == "no_valid_apply_path_no_source"

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_normalizes_sections(
        self, mock_embed, client, fake_supabase
    ):
        mock_embed.return_value = [0.1] * 768
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        jobs_q = FakeSupabaseQuery(data=[])
        fake_supabase.set_table("jobs", jobs_q)

        payload = {
            **self.BASE,
            "description": (
                "RESPONSIBILITIES\nManage stock.\n\nREQUIREMENTS\nGrade 12."
            ),
        }
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [payload]},
        )
        assert resp.status_code == 200
        inserted = jobs_q._data[0]
        assert "## Responsibilities" in inserted.get("description", "")
        assert inserted.get("section_responsibilities")
