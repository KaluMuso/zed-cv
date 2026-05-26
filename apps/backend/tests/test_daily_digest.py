"""Tests for daily WhatsApp digest batch builder and cron endpoint."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.daily_digest import (
    WHATSAPP_DAILY_DIGEST_CHANNEL,
    format_daily_digest_message,
    build_daily_digest_batch,
    run_whatsapp_daily_digest,
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
                user_id,
                "whatsapp_daily_digest",
                fake_supabase,
                now=NOW,
                min_score=50.0,
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
                        "preferred_notification_channel": "whatsapp",
                        "subscription_tier": "starter",
                        "email_notifications_enabled": True,
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
                        "preferred_notification_channel": "whatsapp",
                        "subscription_tier": "starter",
                    }
                ]
            ),
        )
        with (
            patch(
                "app.services.daily_digest.user_in_quiet_hours",
                return_value=False,
            ),
            patch(
                "app.services.daily_digest._select_digest_matches",
                new_callable=AsyncMock,
                return_value=[],
            ),
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
                        "preferred_notification_channel": "whatsapp",
                        "subscription_tier": "starter",
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
                "app.services.daily_digest.user_in_quiet_hours",
                return_value=False,
            ),
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
        assert mock_record.await_args.args[2] == WHATSAPP_DAILY_DIGEST_CHANNEL

    @pytest.mark.asyncio
    async def test_build_batch_skips_users_in_quiet_hours(self, fake_supabase):
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
                        "preferred_notification_channel": "whatsapp",
                        "subscription_tier": "starter",
                        "quiet_hours_start": "20:00",
                        "quiet_hours_end": "07:00",
                        "display_timezone": "Africa/Lusaka",
                    }
                ]
            ),
        )
        with (
            patch(
                "app.services.daily_digest.user_in_quiet_hours",
                return_value=True,
            ),
            patch(
                "app.services.daily_digest._select_digest_matches",
                new_callable=AsyncMock,
            ) as mock_select,
        ):
            rows = await build_daily_digest_batch(fake_supabase)
        assert rows == []
        mock_select.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_run_whatsapp_counts_quiet_hours_skipped(self, fake_supabase):
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
                        "preferred_notification_channel": "whatsapp",
                        "subscription_tier": "starter",
                        "quiet_hours_start": "20:00",
                        "quiet_hours_end": "07:00",
                        "display_timezone": "Africa/Lusaka",
                    }
                ]
            ),
        )
        with (
            patch(
                "app.services.daily_digest.user_in_quiet_hours",
                return_value=True,
            ),
            patch(
                "app.services.daily_digest.send_whatsapp_message",
                new_callable=AsyncMock,
            ) as mock_send,
        ):
            stats = await run_whatsapp_daily_digest(fake_supabase)
        assert stats["quiet_hours_skipped"] == 1
        assert stats["sent"] == 0
        mock_send.assert_not_awaited()
