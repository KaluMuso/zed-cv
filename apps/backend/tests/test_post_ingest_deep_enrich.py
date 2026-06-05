"""Post-ingest deep-enrich scheduling (duplicate n8n guard)."""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import get_settings
from app.services.deep_enrich import DeepEnrichTickResult, schedule_post_ingest_deep_enrich


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_schedule_skipped_when_disabled(monkeypatch):
    monkeypatch.setenv("POST_INGEST_DEEP_ENRICH_ENABLED", "false")
    get_settings.cache_clear()

    stats = await schedule_post_ingest_deep_enrich(None, ingested_count=40)

    assert stats == DeepEnrichTickResult()


@pytest.mark.asyncio
async def test_schedule_respects_max_limit(monkeypatch):
    monkeypatch.setenv("POST_INGEST_DEEP_ENRICH_MAX_LIMIT", "5")
    get_settings.cache_clear()

    with patch(
        "app.services.deep_enrich.run_deep_enrich_tick",
        new_callable=AsyncMock,
        return_value=DeepEnrichTickResult(
            enriched=1,
            attempted=1,
        ),
    ) as mock_tick:
        await schedule_post_ingest_deep_enrich(None, ingested_count=40)

    mock_tick.assert_awaited_once()
    assert mock_tick.await_args.kwargs["limit"] == 5
    assert mock_tick.await_args.kwargs["inter_job_delay_sec"] == 1.0
