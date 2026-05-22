"""Tests for daily WhatsApp digest batch builder and cron endpoint."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.daily_digest import (
    format_daily_digest_message,
    build_daily_digest_batch,
    _select_digest_matches,
)
from tests.conftest import FakeSupabaseQuery

INGEST_HEADERS = {"INGEST_API_KEY": "test-ingest-key"}
NOW = datetime(2026, 5, 22, 7, 0, tzinfo=timezone.utc)


class TestFormatDailyDigestMessage:
    def test_formats_three_matches(self):
        matches = [
            {
                "job_title": "Accountant",
                "job_company": "Zambeef",
                "final_score": 87.4,
            },
            {
                "job_title": "Driver",
                "job_company": "Trade Kings",
                "final_score": 72.0,
            },
            {
                "job_title": "Nurse",
                "job_company": "CIDRZ",
                "final_score": 65.2,
            },
        ]
        text = format_daily_digest_message("Chanda", matches)
        assert "Good morning Chanda!" in text
        assert "1. Accountant at Zambeef (87% match)" in text
        assert "2. Driver at Trade Kings (72% match)" in text
        assert "3. Nurse at CIDRZ (65% match)" in text
        assert "Reply 1, 2, or 3" in text
        assert "ZedApply" in text


class TestSelectDigestMatches:
    @pytest.mark.asyncio
    async def test_excludes_already_sent_and_old_jobs(self, fake_supabase):
        user_id = "user-1"
        recent_job = "job-recent"
        old_job = "job-old"
        sent_job = "job-sent"

        rpc_rows = [
            {
                "job_id": recent_job,
                "job_title": "Recent",
                "job_company": "Co A",
                "final_score": 90,
            },
            {
                "job_id": sent_job,
                "job_title": "Sent",
                "job_company": "Co B",
                "final_score": 88,
            },
            {
                "job_id": old_job,
                "job_title": "Old",
                "job_company": "Co C",
                "final_score": 85,
            },
        ]
        fake_supabase.set_table(
            "user_notifications",
            FakeSupabaseQuery(data=[{"job_id": sent_job}]),
        )
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": recent_job,
                        "posted_at": (NOW - timedelta(hours=2)).isoformat(),
                    },
                    {
                        "id": old_job,
                        "posted_at": (NOW - timedelta(days=3)).isoformat(),
                    },
                    {"id": sent_job, "posted_at": NOW.isoformat()},
                ]
            ),
        )

        with patch(
            "app.services.daily_digest.run_matching_for_user",
            new_callable=AsyncMock,
            return_value=rpc_rows,
        ):
            selected = await _select_digest_matches(
                user_id, fake_supabase, now=NOW, min_score=50.0
            )

        assert len(selected) == 1
        assert selected[0]["job_id"] == recent_job


class TestTriggerDailyDigestEndpoint:
    @pytest.mark.asyncio
    async def test_endpoint_returns_messages(self, client, fake_supabase):
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "u1",
                        "phone": "+260971234567",
                        "whatsapp_number": "+260971234567",
                        "full_name": "Jane Banda",
                        "whatsapp_verified": True,
                        "alert_frequency": "daily",
                    }
                ]
            ),
        )
        with patch(
            "app.api.v1.admin_ingest.build_daily_digest_batch",
            new_callable=AsyncMock,
            return_value=[
                {
                    "user_id": "u1",
                    "phone": "+260971234567",
                    "message": "Good morning Jane! ...",
                }
            ],
        ):
            resp = client.get(
                "/api/v1/admin/trigger-daily-digest",
                headers=INGEST_HEADERS,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["messages"]) == 1
        assert body["messages"][0]["user_id"] == "u1"
        assert body["messages"][0]["phone"] == "+260971234567"

    def test_endpoint_requires_api_key(self, client):
        resp = client.get("/api/v1/admin/trigger-daily-digest")
        assert resp.status_code == 401


class TestBuildDailyDigestBatch:
    @pytest.mark.asyncio
    async def test_skips_users_without_matches(self, fake_supabase):
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "u1",
                        "phone": "+260971234567",
                        "whatsapp_number": "+260971234567",
                        "full_name": "Jane",
                        "whatsapp_verified": True,
                        "alert_frequency": "daily",
                    }
                ]
            ),
        )
        with patch(
            "app.services.daily_digest._select_digest_matches",
            new_callable=AsyncMock,
            return_value=[],
        ):
            rows = await build_daily_digest_batch(fake_supabase)
        assert rows == []

    @pytest.mark.asyncio
    async def test_records_notifications_when_matches_exist(self, fake_supabase):
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "u1",
                        "phone": "+260971234567",
                        "whatsapp_number": "+260971234567",
                        "full_name": "Jane",
                        "whatsapp_verified": True,
                        "alert_frequency": "daily",
                    }
                ]
            ),
        )
        matches = [
            {
                "job_id": "j1",
                "job_title": "Dev",
                "job_company": "TechCo",
                "final_score": 80,
            }
        ]
        with (
            patch(
                "app.services.daily_digest._select_digest_matches",
                new_callable=AsyncMock,
                return_value=matches,
            ),
            patch(
                "app.services.daily_digest.record_digest_notifications",
                new_callable=AsyncMock,
            ) as mock_record,
        ):
            rows = await build_daily_digest_batch(fake_supabase)

        assert len(rows) == 1
        assert "Dev" in rows[0]["message"]
        mock_record.assert_awaited_once()
        assert mock_record.await_args.args[0] == "u1"
        assert mock_record.await_args.args[1] == ["j1"]
