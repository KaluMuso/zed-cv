"""Unit tests for notification channel helpers and digest cron endpoints."""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.notification_channels import (
    validate_channel_update,
    wants_email_digest,
    wants_whatsapp_digest,
)

INGEST_HEADERS = {"INGEST_API_KEY": "test-ingest-key"}


class TestNotificationChannelHelpers:
    def test_free_tier_cannot_use_whatsapp_channel(self):
        row = {
            "preferred_notification_channel": "whatsapp",
            "subscription_tier": "free",
            "whatsapp_verified": True,
            "phone": "+260971234567",
        }
        assert wants_whatsapp_digest(row) is False
        with pytest.raises(ValueError):
            validate_channel_update("both", "free")

    def test_starter_whatsapp_channel_allowed_when_verified(self):
        row = {
            "preferred_notification_channel": "both",
            "subscription_tier": "starter",
            "whatsapp_verified": True,
            "whatsapp_number": "+260971234567",
            "email": "user@test.com",
            "email_notifications_enabled": True,
        }
        assert wants_whatsapp_digest(row) is True
        assert wants_email_digest(row) is True


class TestDigestCronEndpoints:
    @pytest.mark.asyncio
    async def test_email_digest_endpoint(self, client):
        with patch(
            "app.api.v1.admin_ingest.run_email_daily_digest",
            new_callable=AsyncMock,
            return_value={"sent": 2, "skipped": 1, "failed": 0},
        ):
            resp = client.post(
                "/api/v1/admin/trigger-daily-digest-email",
                headers=INGEST_HEADERS,
            )
        assert resp.status_code == 200
        assert resp.json() == {"sent": 2, "skipped": 1, "failed": 0}

    @pytest.mark.asyncio
    async def test_whatsapp_digest_endpoint(self, client):
        with patch(
            "app.api.v1.admin_ingest.run_whatsapp_daily_digest",
            new_callable=AsyncMock,
            return_value={"sent": 1, "skipped": 0, "failed": 0},
        ):
            resp = client.post(
                "/api/v1/admin/trigger-daily-digest-whatsapp",
                headers=INGEST_HEADERS,
            )
        assert resp.status_code == 200
        assert resp.json()["sent"] == 1
