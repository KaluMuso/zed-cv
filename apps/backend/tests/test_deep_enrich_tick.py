"""Tests for secondary deep-enrich cron tick."""
from unittest.mock import AsyncMock, patch

from main import app
from app.services.deep_enrich import DeepEnrichJobResult, DeepEnrichTickResult
from tests.conftest import FakeSupabaseQuery

INGEST_HEADERS = {"X-INGEST-API-KEY": "test-ingest-key"}
MOUNTED_PATH = "/api/v1/jobs/deep-enrich-tick"


def _deep_enrich_route_methods() -> set[str]:
    methods: set[str] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if path == MOUNTED_PATH:
            methods |= set(getattr(route, "methods", set()) or set())
    return methods


def test_deep_enrich_tick_route_accepts_post(client):
    """Mounted app must expose POST on the n8n cron path (not only GET /{job_id})."""
    assert "POST" in _deep_enrich_route_methods()

    with patch(
        "app.api.v1.jobs.run_deep_enrich_tick",
        new_callable=AsyncMock,
        return_value=DeepEnrichTickResult(),
    ):
        resp = client.post(f"{MOUNTED_PATH}?limit=50", headers=INGEST_HEADERS)

    assert resp.status_code != 405, resp.text
    assert resp.status_code == 200
    assert resp.json() == {
        "enriched": 0,
        "split": 0,
        "failed": 0,
        "skipped": 0,
        "attempted": 0,
        "results": [],
    }


class TestDeepEnrichTick:
    def test_rejects_without_ingest_key(self, client):
        resp = client.post(MOUNTED_PATH)
        assert resp.status_code == 401

    @patch(
        "app.api.v1.jobs.run_deep_enrich_tick",
        new_callable=AsyncMock,
        return_value=DeepEnrichTickResult(
            enriched=1,
            failed=1,
            attempted=2,
            results=[
                DeepEnrichJobResult(
                    job_id="j1",
                    title="Engineer",
                    outcome="enriched",
                    detail="https://example.com/job",
                ),
                DeepEnrichJobResult(
                    job_id="j2",
                    title="Intern",
                    outcome="failed",
                    detail="HTTP 404",
                ),
            ],
        ),
    )
    def test_deep_enrich_tick_with_ingest_key(self, mock_tick, client, fake_supabase):
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[]))
        resp = client.post(
            f"{MOUNTED_PATH}?limit=10&include_review_queue=true",
            headers=INGEST_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["enriched"] == 1
        assert body["failed"] == 1
        assert body["attempted"] == 2
        assert len(body["results"]) == 2
        assert body["results"][1]["detail"] == "HTTP 404"
        mock_tick.assert_awaited_once_with(
            fake_supabase,
            limit=10,
            include_review_queue=True,
        )

    @patch(
        "app.api.v1.jobs.run_deep_enrich_tick",
        new_callable=AsyncMock,
        return_value=DeepEnrichTickResult(),
    )
    def test_deep_enrich_tick_can_exclude_review_queue(self, mock_tick, client):
        resp = client.post(
            f"{MOUNTED_PATH}?include_review_queue=false",
            headers=INGEST_HEADERS,
        )
        assert resp.status_code == 200
        mock_tick.assert_awaited_once()
        assert mock_tick.await_args.kwargs["include_review_queue"] is False

    @patch(
        "app.api.v1.jobs.run_deep_enrich_tick",
        new_callable=AsyncMock,
        return_value=DeepEnrichTickResult(),
    )
    def test_deep_enrich_tick_accepts_api_key_query_param(self, mock_tick, client):
        resp = client.post(
            f"{MOUNTED_PATH}?limit=5&api_key=test-ingest-key",
        )
        assert resp.status_code == 200
        mock_tick.assert_awaited_once()
