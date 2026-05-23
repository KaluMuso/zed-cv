"""Tests for secondary deep-enrich cron tick."""
from unittest.mock import AsyncMock, patch

from tests.conftest import FakeSupabaseQuery

INGEST_HEADERS = {"X-INGEST-API-KEY": "test-ingest-key"}


class TestDeepEnrichTick:
    def test_rejects_without_ingest_key(self, client):
        resp = client.post("/api/v1/jobs/deep-enrich-tick")
        assert resp.status_code == 401

    @patch(
        "app.api.v1.jobs.run_deep_enrich_tick",
        new_callable=AsyncMock,
        return_value={"processed": 2, "enriched": 1, "unchanged": 1},
    )
    def test_deep_enrich_tick_with_ingest_key(self, mock_tick, client, fake_supabase):
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[]))
        resp = client.post(
            "/api/v1/jobs/deep-enrich-tick?limit=10",
            headers=INGEST_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"processed": 2, "enriched": 1, "unchanged": 1}
        mock_tick.assert_awaited_once()
