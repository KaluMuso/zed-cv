"""Web Push service and subscribe route tests."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.web_push import (
    HIGH_MATCH_PUSH_THRESHOLD,
    build_high_match_payload,
    vapid_configured,
)


class TestWebPushHelpers:
    def test_build_high_match_payload_compact(self):
        payload = build_high_match_payload(
            match_id="m-1",
            job_title="Software Engineer",
            score=92.4,
            app_url="https://zedapply.com",
        )
        assert payload["score"] == 92
        assert payload["url"] == "/matches/m-1"
        assert "Software Engineer" in payload["title"]
        raw = str(payload)
        assert len(raw) < 512

    def test_vapid_configured_requires_both_keys(self, monkeypatch):
        monkeypatch.setenv("VAPID_PRIVATE_KEY", "priv")
        monkeypatch.setenv("VAPID_PUBLIC_KEY", "pub")
        from app.core.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()
        assert vapid_configured(settings) is True


class TestPushSubscribeRoute:
    def test_subscribe_stores_subscription(self, client: TestClient, auth_headers):
        with patch("app.api.v1.push.vapid_configured", return_value=True):
            with patch(
                "app.api.v1.push.upsert_subscription",
                new=AsyncMock(),
            ) as upsert:
                res = client.post(
                    "/api/v1/push/subscribe",
                    headers=auth_headers,
                    json={
                        "endpoint": "https://push.example/sub/abc",
                        "keys": {"p256dh": "key", "auth": "secret"},
                    },
                )
        assert res.status_code == 200
        assert res.json()["ok"] is True
        upsert.assert_awaited_once()


class TestHighMatchNotify:
    def test_notify_skips_below_threshold(self):
        from app.services.notifications import notify_high_match_web_pushes

        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.not_.is_.return_value.execute.return_value = MagicMock(
            data=[]
        )
        sent = asyncio.run(
            notify_high_match_web_pushes("u1", ["j1"], supabase, min_score=HIGH_MATCH_PUSH_THRESHOLD)
        )
        assert sent == 0

    def test_notify_sends_for_high_scores(self):
        from app.services.notifications import notify_high_match_web_pushes

        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.not_.is_.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "match-1",
                    "job_id": "j1",
                    "score": 90,
                    "jobs": {"title": "Analyst"},
                }
            ]
        )
        with patch(
            "app.services.notifications.send_high_match_push",
            new=AsyncMock(return_value=1),
        ) as send_push:
            sent = asyncio.run(
                notify_high_match_web_pushes("u1", ["j1"], supabase)
            )
        assert sent == 1
        send_push.assert_awaited_once()
