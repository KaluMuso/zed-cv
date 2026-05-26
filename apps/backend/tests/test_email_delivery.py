"""Email delivery errors and Resend health diagnostics."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_delivery import (
    EMAIL_PROVIDER_UNAVAILABLE,
    EmailDeliveryError,
    check_resend_health,
)


class TestCheckResendHealth:
    def test_missing_api_key(self):
        report = check_resend_health(
            resend_api_key="",
            resend_from_email="Zed CV <noreply@zedcv.com>",
        )
        body = report.as_dict()
        assert body["status"] == "error"
        assert body["code"] == EMAIL_PROVIDER_UNAVAILABLE
        assert body["api_key_configured"] is False

    @patch("resend.Domains.list")
    def test_ok_when_domain_verified(self, mock_list):
        mock_list.return_value = MagicMock(
            data=[{"name": "zedcv.com", "status": "verified"}]
        )
        report = check_resend_health(
            resend_api_key="re_test",
            resend_from_email="Zed CV <noreply@zedcv.com>",
        )
        body = report.as_dict()
        assert body["status"] == "ok"
        assert body.get("code") is None
        assert body["domain_verified"] is True

    @patch("resend.Domains.list")
    def test_degraded_when_domain_missing(self, mock_list):
        mock_list.return_value = MagicMock(
            data=[{"name": "other.com", "status": "verified"}]
        )
        report = check_resend_health(
            resend_api_key="re_test",
            resend_from_email="noreply@zedcv.com",
        )
        body = report.as_dict()
        assert body["status"] == "degraded"
        assert body["code"] == "email_domain_unverified"


class TestSendOtpEmail:
    @pytest.mark.asyncio
    async def test_raises_when_api_key_missing(self, monkeypatch):
        from app.services import email as email_mod

        monkeypatch.setenv("RESEND_API_KEY", "")
        email_mod.get_settings.cache_clear()
        with pytest.raises(EmailDeliveryError) as exc:
            await email_mod.send_otp_email("user@example.com", "123456")
        assert exc.value.code == EMAIL_PROVIDER_UNAVAILABLE
        email_mod.get_settings.cache_clear()
