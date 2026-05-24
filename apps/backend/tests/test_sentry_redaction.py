"""Unit tests for Sentry PII scrubbing (ZDPA / observability)."""
import copy

from app.observability.sentry import before_send
from app.observability.sentry_scrub import (
    redact_string,
    scrub_sentry_event,
    should_drop_sentry_event,
    _scrub_string_leaves,
)


class TestRedactString:
    def test_phone_e164_redacted(self):
        s = "OTP send failed for +260977123456"
        out = redact_string(s)
        assert "+260977123456" not in out
        assert "[REDACTED_PHONE]" in out

    def test_phone_local_zero_prefix(self):
        s = "SMS to 09771234567 failed"
        out = redact_string(s)
        assert "09771234567" not in out
        assert "[REDACTED_PHONE]" in out

    def test_whatsapp_jid_redacted(self):
        s = "WAHA chatId 260977123456@c.us unreachable"
        out = redact_string(s)
        assert "@c.us" not in out
        assert "[REDACTED_PHONE]" in out

    def test_email_redacted(self):
        s = "Sent welcome email to user@example.com"
        out = redact_string(s)
        assert "user@example.com" not in out
        assert "[REDACTED_EMAIL]" in out

    def test_nrc_redacted(self):
        s = "NRC 123456/78/9 on file"
        out = redact_string(s)
        assert "123456/78/9" not in out
        assert "[REDACTED_NRC]" in out

    def test_jwt_redacted(self):
        jwt = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0"
            ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        out = redact_string(f"Bearer {jwt} rejected")
        assert jwt not in out
        assert "[REDACTED_JWT]" in out

    def test_non_zambian_phone_preserved(self):
        s = "Caller-ID +14155552671 routed to fallback"
        assert "+14155552671" in redact_string(s)


class TestWalk:
    def test_walks_nested_dict(self):
        event = {"exception": {"values": [{"value": "User +260977123456 hit error"}]}}
        _scrub_string_leaves(event)
        assert event["exception"]["values"][0]["value"] == "User [REDACTED_PHONE] hit error"


class TestShouldDrop:
    def test_drops_otp_verify_path_in_url(self):
        event = {"request": {"url": "https://api.zedapply.com/api/v1/auth/otp/verify"}}
        assert should_drop_sentry_event(event) is True

    def test_drops_verify_otp_alias_path(self):
        event = {"message": "handler /auth/verify-otp exploded"}
        assert should_drop_sentry_event(event) is True

    def test_drops_lenco_webhook_with_body(self):
        event = {
            "request": {
                "url": "/api/v1/webhooks/lenco",
                "data": {"amount": 12500, "phone": "+260977123456"},
            }
        }
        assert should_drop_sentry_event(event) is True

    def test_keeps_lenco_webhook_without_body(self):
        event = {"request": {"url": "/api/v1/webhooks/lenco"}}
        assert should_drop_sentry_event(event) is False


class TestBeforeSend:
    def test_scrubs_and_tags(self):
        event = {"message": "OTP send failed for +260977123456"}
        result = before_send(event, hint=None)
        assert result is event
        assert "[REDACTED_PHONE]" in event["message"]
        assert event["tags"]["redaction_version"] == "1.0"

    def test_returns_none_for_otp_verify(self):
        event = {
            "request": {"url": "https://api.example.com/api/v1/auth/otp/verify"},
            "message": "validation error",
        }
        assert before_send(copy.deepcopy(event), hint=None) is None

    def test_strips_user_ip(self):
        event = {
            "message": "ok",
            "user": {"id": "u1", "ip_address": "41.72.1.1"},
            "request": {"headers": {"X-Forwarded-For": "41.72.1.1"}},
        }
        before_send(event, hint=None)
        assert "ip_address" not in event.get("user", {})
        assert "X-Forwarded-For" not in event["request"]["headers"]

    def test_scrub_entry_matches_before_send(self):
        event = {"extra": {"note": "contact john@example.com"}}
        assert scrub_sentry_event(event) is event
        assert event["extra"]["note"] == "contact [REDACTED_EMAIL]"
