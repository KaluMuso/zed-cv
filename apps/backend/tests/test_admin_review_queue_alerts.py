"""Tests for POST /api/v1/admin/check-review-queue."""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.services import admin_alerts
from tests.conftest import FakeSupabaseQuery


INGEST_HEADERS = {"INGEST_API_KEY": "test-ingest-key"}


def _settings(**overrides) -> Settings:
    base = {
        "supabase_url": "https://fake.supabase.co",
        "supabase_key": "fake",
        "gemini_api_key": "fake",
        "jwt_secret": "test-secret",
        "ingest_api_key": "test-ingest-key",
        "enable_admin_whatsapp_alerts": True,
        "waha_api_url": "http://waha:3000",
        "waha_api_key": "waha-key",
    }
    base.update(overrides)
    return Settings(**base)


def _jobs_count_query(count: int) -> FakeSupabaseQuery:
    return FakeSupabaseQuery(data=[], count=count)


def _cache_query(result: dict | None = None) -> FakeSupabaseQuery:
    if result is None:
        return FakeSupabaseQuery(data=[])
    return FakeSupabaseQuery(data=[{"id": "cache-1", "result": result}])


class TestCheckReviewQueueEndpoint:
    @patch(
        "app.services.admin_alerts.send_admin_whatsapp",
        new_callable=AsyncMock,
    )
    def test_check_review_queue_no_alert_when_below_threshold(
        self, mock_send, client, fake_supabase
    ):
        fake_supabase.set_table("jobs", _jobs_count_query(5))
        fake_supabase.set_table("ai_cache", _cache_query())

        resp = client.post(
            "/api/v1/admin/check-review-queue",
            headers=INGEST_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["review_count"] == 5
        assert body["alerted"] is False
        assert body["reason"] == "below_threshold"
        mock_send.assert_not_called()

    @patch(
        "app.services.admin_alerts.send_admin_whatsapp",
        new_callable=AsyncMock,
    )
    def test_check_review_queue_alerts_at_threshold_10(
        self, mock_send, client, fake_supabase
    ):
        fake_supabase.set_table("jobs", _jobs_count_query(12))
        fake_supabase.set_table("ai_cache", _cache_query())

        resp = client.post(
            "/api/v1/admin/check-review-queue",
            headers=INGEST_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["alerted"] is True
        assert body["threshold_alerted"] == 10
        assert body["review_count"] == 12
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "Review queue has 12 jobs" in text
        assert "ZedApply Admin Alert" in text

    @patch(
        "app.services.admin_alerts.send_admin_whatsapp",
        new_callable=AsyncMock,
    )
    def test_check_review_queue_idempotent_within_same_threshold_band(
        self, mock_send, client, fake_supabase
    ):
        fake_supabase.set_table("jobs", _jobs_count_query(15))
        fake_supabase.set_table(
            "ai_cache",
            _cache_query(
                {
                    "last_threshold": 10,
                    "last_alert_at": "2026-05-21T14:00:00+00:00",
                    "last_alert_count": 12,
                }
            ),
        )

        resp = client.post(
            "/api/v1/admin/check-review-queue",
            headers=INGEST_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["alerted"] is False
        assert body["reason"] == "already_alerted_for_threshold"
        mock_send.assert_not_called()

    @patch(
        "app.services.admin_alerts.send_admin_whatsapp",
        new_callable=AsyncMock,
    )
    def test_check_review_queue_re_alerts_at_threshold_25(
        self, mock_send, client, fake_supabase
    ):
        fake_supabase.set_table("jobs", _jobs_count_query(26))
        fake_supabase.set_table(
            "ai_cache",
            _cache_query(
                {
                    "last_threshold": 10,
                    "last_alert_at": "2026-05-21T14:00:00+00:00",
                    "last_alert_count": 12,
                }
            ),
        )

        resp = client.post(
            "/api/v1/admin/check-review-queue",
            headers=INGEST_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["alerted"] is True
        assert body["threshold_alerted"] == 25
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "Last alert: 2026-05-21 14:00 (12 jobs)" in text

    def test_check_review_queue_rejects_invalid_ingest_key(self, client):
        resp = client.post(
            "/api/v1/admin/check-review-queue",
            headers={"INGEST_API_KEY": "wrong"},
        )
        assert resp.status_code == 401


class TestAdminAlertsHelpers:
    def test_threshold_for_review_count(self):
        assert admin_alerts.threshold_for_review_count(9) is None
        assert admin_alerts.threshold_for_review_count(10) == 10
        assert admin_alerts.threshold_for_review_count(24) == 10
        assert admin_alerts.threshold_for_review_count(25) == 25
        assert admin_alerts.threshold_for_review_count(100) == 100
        assert admin_alerts.threshold_for_review_count(150) == 100

    @pytest.mark.asyncio
    @patch(
        "app.services.admin_alerts.send_admin_whatsapp",
        new_callable=AsyncMock,
    )
    async def test_disabled_skips_whatsapp(self, mock_send, fake_supabase):
        fake_supabase.set_table("jobs", _jobs_count_query(12))
        fake_supabase.set_table("ai_cache", _cache_query())
        settings = _settings(enable_admin_whatsapp_alerts=False)

        out = await admin_alerts.check_review_queue_and_alert(
            fake_supabase, settings
        )
        assert out["alerted"] is False
        assert out["reason"] == "disabled"
        mock_send.assert_not_called()
