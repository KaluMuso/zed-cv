"""Tests for Lenco v2 webhook signature verification + route handling."""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch

from tests.conftest import FakeSupabaseQuery
from tests.test_webhooks import _UpdateSpyQuery
from app.services.lenco_webhook import (
    verify_lenco_signature,
    extract_event_fields,
    derive_lenco_webhook_hash_key,
    mask_lenco_webhook_payload,
    is_valid_uuid,
    parse_zedapply_consumer_user_id,
    resolve_lenco_webhook_payment,
)

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
        assert verify_lenco_signature(body, wrong_sig, api_key=TEST_API_KEY) is False

        assert verify_lenco_signature(body, _sign(body), api_key=TEST_API_KEY) is True

    def test_rejects_missing_signature(self):
        assert verify_lenco_signature(b"{}", "", api_key=TEST_API_KEY) is False

    def test_rejects_tampered_body(self):
        body = b'{"amount":12500}'
        sig = _sign(body)
        assert verify_lenco_signature(
            b'{"amount":99999}', sig, api_key=TEST_API_KEY
        ) is False

    def test_accepts_webhook_secret_without_api_key(self):
        body = b'{"event":"collection.successful"}'
        webhook_secret = derive_lenco_webhook_hash_key(api_key=TEST_API_KEY)
        sig = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha512,
        ).hexdigest()
        assert verify_lenco_signature(
            body, sig, webhook_secret=webhook_secret, api_key=""
        ) is True

    def test_compare_digest_used_for_signature(self, monkeypatch):
        """Regression: signature check must use timing-safe compare."""
        body = b'{"event":"collection.successful"}'
        sig = _sign(body)
        calls: list[tuple[str, str]] = []

        original = hmac.compare_digest

        def _spy(a: str, b: str) -> bool:
            calls.append((a, b))
            return original(a, b)

        monkeypatch.setattr(hmac, "compare_digest", _spy)
        assert verify_lenco_signature(body, sig, api_key=TEST_API_KEY) is True
        assert len(calls) == 1


class TestMaskLencoWebhookPayload:
    def test_masks_reference_and_amount_last_four(self):
        masked = mask_lenco_webhook_payload(
            {
                "event": "collection.successful",
                "data": {
                    "reference": "zedapply-pay-1234",
                    "amount": 12500,
                    "status": "successful",
                },
            }
        )
        assert masked["reference"] == "***1234"
        assert masked["amount"] == "***2500"
        assert masked["status"] == "successful"


class TestLencoReferenceParsing:
    def test_is_valid_uuid(self):
        assert is_valid_uuid("5d6c1f43-f440-48fe-b4c8-88364544ee3d") is True
        assert is_valid_uuid("zedapply-5d6c1f43-f440-48fe-b4c8-88364544ee3d-1") is False

    def test_parse_widget_reference_user_id(self):
        user_id = "5d6c1f43-f440-48fe-b4c8-88364544ee3d"
        ref = f"zedapply-{user_id}-1780091173119"
        assert parse_zedapply_consumer_user_id(ref) == user_id

    def test_parse_skips_employer_and_legacy_short_refs(self):
        assert parse_zedapply_consumer_user_id("zedapply-emp-abc-1") is None
        assert parse_zedapply_consumer_user_id("zedapply-pay-1") is None


class TestResolveLencoWebhookPayment:
    def test_skips_invalid_uuid_id_lookup(self, fake_supabase):
        user_id = "5d6c1f43-f440-48fe-b4c8-88364544ee3d"
        ref = f"zedapply-{user_id}-1780091173119"
        fake_supabase.set_table("payments", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "subscriptions",
            FakeSupabaseQuery(
                data=[{"id": "sub-1", "user_id": user_id, "tier": "free"}]
            ),
        )
        payment = resolve_lenco_webhook_payment(
            fake_supabase,
            ref,
            None,
            amount_ngwee=12500,
            webhook_payload={"event": "collection.successful"},
            allow_create=True,
        )
        assert payment is not None
        assert payment["user_id"] == user_id
        assert payment["provider_ref"] == ref
        assert payment["status"] == "pending"


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

    def test_company_ref_alias_from_companyRef_field(self):
        payload = {
            "event": "collection.successful",
            "data": {
                "companyRef": "zedapply-widget-ref",
                "status": "successful",
                "amount": 12500,
            },
        }
        fields = extract_event_fields(payload)
        assert fields["company_ref"] == "zedapply-widget-ref"

    def test_collection_failed_marks_failed(self):
        payload = {
            "event": "collection.failed",
            "data": {"reference": "zedapply-fail", "status": "failed"},
        }
        fields = extract_event_fields(payload)
        assert fields["is_failed"] is True
        assert fields["is_paid"] is False

    def test_transfer_successful_is_not_paid(self):
        payload = {
            "event": "transfer.successful",
            "data": {"reference": "zedapply-pay-1", "status": "successful", "amount": "250.00"},
        }
        fields = extract_event_fields(payload)
        assert fields["is_paid"] is False

    def test_decimal_kwacha_amount_converts_to_ngwee(self):
        payload = {
            "event": "collection.successful",
            "data": {"reference": "zedapply-abc", "status": "successful", "amount": "250.00"},
        }
        fields = extract_event_fields(payload)
        assert fields["amount_ngwee"] == 25000


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

    @patch("app.services.email.send_payment_confirmation_email")
    @patch("app.services.whatsapp.send_whatsapp_message")
    def test_webhook_widget_reference_does_not_query_payments_id_as_uuid(
        self, _mock_wa, _mock_email, client, fake_supabase, monkeypatch
    ):
        """Regression: zedapply-{user_uuid}-{ts} must not be used as payments.id."""
        from app.core.config import get_settings
        import uuid as uuid_mod

        get_settings.cache_clear()
        monkeypatch.setenv("LENCO_API_KEY", TEST_API_KEY)

        user_id = str(uuid_mod.uuid4())
        company_ref = f"zedapply-{user_id}-1717000000000"
        body_dict = {
            "event": "collection.successful",
            "data": {
                "reference": company_ref,
                "transactionRef": "LEN-widget",
                "status": "successful",
                "amount": 12500,
            },
        }
        body_bytes = json.dumps(body_dict).encode("utf-8")

        payments_q = FakeSupabaseQuery(data=[])
        subs_q = FakeSupabaseQuery(
            data=[{"id": "sub-widget", "user_id": user_id, "tier": "free"}]
        )
        users_q = FakeSupabaseQuery(
            data=[{"id": user_id, "phone": "+260971234567", "subscription_started_at": None}]
        )
        fake_supabase.set_table("payments", payments_q)
        fake_supabase.set_table("subscriptions", subs_q)
        fake_supabase.set_table("users", users_q)

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
        assert payments_q._data[0]["provider_ref"] == company_ref

    def test_webhook_skips_signature_when_verify_disabled(
        self, client, fake_supabase, monkeypatch
    ):
        from app.core.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("LENCO_VERIFY_SIGNATURES", "false")

        body_dict = {
            "event": "collection.failed",
            "data": {"reference": "zedapply-no-sig", "status": "failed"},
        }
        body_bytes = json.dumps(body_dict).encode("utf-8")

        payments_spy = _UpdateSpyQuery(
            data=[
                {
                    "id": "pay-no-sig",
                    "user_id": "user-1",
                    "amount": 12500,
                    "status": "pending",
                    "provider_ref": "zedapply-no-sig",
                    "subscriptions": {},
                }
            ]
        )
        fake_supabase.set_table("payments", payments_spy)

        resp = client.post(
            "/api/v1/webhooks/lenco",
            headers={"Content-Type": "application/json"},
            content=body_bytes,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"
