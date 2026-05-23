"""Tests for Lenco v2 webhook signature verification + route handling."""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch

from tests.conftest import FakeSupabaseQuery
from tests.test_webhooks import _UpdateSpyQuery
from app.services.lenco_webhook import verify_lenco_signature, extract_event_fields

TEST_API_KEY = "test-lenco-api-secret-key"


def _webhook_hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def _sign(body: bytes, api_key: str = TEST_API_KEY) -> str:
    """Compute X-Lenco-Signature the way Lenco documents it."""
    return hmac.new(
        _webhook_hash_key(api_key).encode(),
        body,
        hashlib.sha512,
    ).hexdigest()


class TestVerifyLencoSignature:
    def test_webhook_signature_uses_sha256_of_api_key(self):
        """Regression: signing key must be sha256(api_key), not raw api_key."""
        body = b'{"event":"collection.successful"}'
        wrong_sig = hmac.new(
            TEST_API_KEY.encode(),
            body,
            hashlib.sha512,
        ).hexdigest()
        assert verify_lenco_signature(body, wrong_sig, TEST_API_KEY) is False

        assert verify_lenco_signature(body, _sign(body), TEST_API_KEY) is True

    def test_rejects_missing_signature(self):
        assert verify_lenco_signature(b"{}", "", TEST_API_KEY) is False

    def test_rejects_tampered_body(self):
        body = b'{"amount":12500}'
        sig = _sign(body)
        assert verify_lenco_signature(b'{"amount":99999}', sig, TEST_API_KEY) is False


class TestExtractEventFields:
    def test_collection_successful_marks_paid(self):
        payload = {
            "event": "collection.successful",
            "data": {
                "reference": "zedapply-abc",
                "status": "successful",
                "amount": 12500,
            },
        }
        fields = extract_event_fields(payload)
        assert fields["is_paid"] is True
        assert fields["is_failed"] is False
        assert fields["company_ref"] == "zedapply-abc"

    def test_collection_failed_marks_failed(self):
        payload = {
            "event": "collection.failed",
            "data": {"reference": "zedapply-fail", "status": "failed"},
        }
        fields = extract_event_fields(payload)
        assert fields["is_failed"] is True
        assert fields["is_paid"] is False


class TestLencoWebhookRoute:
    def _post_lenco(self, client, body_dict: dict, *, sig: str | None = None):
        body_bytes = json.dumps(body_dict).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if sig is not None:
            headers["x-lenco-signature"] = sig
        return client.post(
            "/api/v1/webhooks/lenco",
            headers=headers,
            content=body_bytes,
        )

    def test_webhook_invalid_signature_returns_401(
        self, client, fake_supabase, monkeypatch
    ):
        from app.core.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("LENCO_API_KEY", TEST_API_KEY)

        resp = self._post_lenco(
            client,
            {"event": "collection.successful", "data": {"reference": "x"}},
            sig="deadbeef" * 16,
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid signature"

    @patch("app.services.email.send_payment_confirmation_email")
    @patch("app.services.whatsapp.send_whatsapp_message")
    def test_webhook_valid_signature_processes_event(
        self, _mock_wa, _mock_email, client, fake_supabase, monkeypatch
    ):
        from app.core.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("LENCO_API_KEY", TEST_API_KEY)

        body_dict = {
            "event": "collection.successful",
            "data": {
                "reference": "zedapply-pay-1",
                "transactionRef": "LEN-1",
                "status": "successful",
                "amount": 12500,
                "currency": "ZMW",
            },
        }
        body_bytes = json.dumps(body_dict).encode("utf-8")

        fake_supabase.set_table(
            "payments",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "pay-internal-1",
                        "user_id": "user-1",
                        "amount": 12500,
                        "status": "pending",
                        "provider_ref": "zedapply-pay-1",
                        "subscriptions": {"id": "sub-1", "current_period_end": None},
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(data=[{"id": "user-1", "phone": "+260971234567"}]),
        )

        resp = client.post(
            "/api/v1/webhooks/lenco",
            headers={
                "x-lenco-signature": _sign(body_bytes),
                "Content-Type": "application/json",
            },
            content=body_bytes,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    @patch("app.services.email.send_payment_confirmation_email")
    @patch("app.services.whatsapp.send_whatsapp_message")
    def test_webhook_collection_successful_activates_subscription(
        self, _mock_wa, _mock_email, client, fake_supabase, monkeypatch
    ):
        from app.core.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("LENCO_API_KEY", TEST_API_KEY)

        body_dict = {
            "event": "collection.successful",
            "data": {
                "reference": "zedapply-bill",
                "transactionRef": "LEN-bill",
                "status": "successful",
                "amount": 12500,
            },
        }
        body_bytes = json.dumps(body_dict).encode("utf-8")

        fake_supabase.set_table(
            "payments",
            _UpdateSpyQuery(
                data=[
                    {
                        "id": "pay-bill",
                        "user_id": "user-1",
                        "amount": 12500,
                        "status": "pending",
                        "provider_ref": "zedapply-bill",
                        "subscriptions": {
                            "id": "sub-1",
                            "current_period_end": None,
                            "started_at": None,
                        },
                    }
                ]
            ),
        )
        subs_spy = _UpdateSpyQuery(data=[{"id": "sub-1", "user_id": "user-1"}])
        users_spy = _UpdateSpyQuery(
            data=[{"id": "user-1", "phone": "+260971234567", "subscription_started_at": None}]
        )
        fake_supabase.set_table("subscriptions", subs_spy)
        fake_supabase.set_table("users", users_spy)

        resp = client.post(
            "/api/v1/webhooks/lenco",
            headers={
                "x-lenco-signature": _sign(body_bytes),
                "Content-Type": "application/json",
            },
            content=body_bytes,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert subs_spy.update_calls[0]["tier"] == "starter"
        assert users_spy.update_calls[0]["subscription_started_at"]

    def test_webhook_collection_failed_marks_payment_failed(
        self, client, fake_supabase, monkeypatch
    ):
        from app.core.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("LENCO_API_KEY", TEST_API_KEY)

        body_dict = {
            "event": "collection.failed",
            "data": {
                "reference": "zedapply-fail",
                "status": "failed",
            },
        }
        body_bytes = json.dumps(body_dict).encode("utf-8")

        payments_spy = _UpdateSpyQuery(
            data=[
                {
                    "id": "pay-fail",
                    "user_id": "user-1",
                    "amount": 12500,
                    "status": "pending",
                    "provider_ref": "zedapply-fail",
                    "subscriptions": {},
                }
            ]
        )
        fake_supabase.set_table("payments", payments_spy)

        resp = client.post(
            "/api/v1/webhooks/lenco",
            headers={
                "x-lenco-signature": _sign(body_bytes),
                "Content-Type": "application/json",
            },
            content=body_bytes,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"
        assert payments_spy.update_calls[-1]["status"] == "failed"

    @patch("app.services.email.send_payment_confirmation_email")
    @patch("app.services.whatsapp.send_whatsapp_message")
    def test_webhook_idempotent_after_frontend_verify(
        self, _mock_wa, _mock_email, client, fake_supabase, monkeypatch
    ):
        """Frontend verify-payment completed first; webhook must no-op."""
        from app.core.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("LENCO_API_KEY", TEST_API_KEY)

        body_dict = {
            "event": "collection.successful",
            "data": {
                "reference": "zedapply-dup",
                "status": "successful",
                "amount": 12500,
            },
        }
        body_bytes = json.dumps(body_dict).encode("utf-8")

        fake_supabase.set_table(
            "payments",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "pay-dup",
                        "user_id": "user-1",
                        "amount": 12500,
                        "status": "completed",
                        "provider_ref": "zedapply-dup",
                        "subscriptions": {
                            "id": "sub-1",
                            "started_at": "2026-01-01T00:00:00+00:00",
                        },
                    }
                ]
            ),
        )

        resp = client.post(
            "/api/v1/webhooks/lenco",
            headers={
                "x-lenco-signature": _sign(body_bytes),
                "Content-Type": "application/json",
            },
            content=body_bytes,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "already_processed"
