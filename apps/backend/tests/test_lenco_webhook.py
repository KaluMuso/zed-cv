"""Tests for Lenco v2 webhook signature verification + event extraction.

Signature verification is the security boundary - if this is wrong, an
attacker can mint payment-success webhooks and grant themselves any tier.
Pin the contract here.
"""
import hashlib
import hmac
import json
from unittest.mock import patch
from tests.conftest import FakeSupabaseQuery
from tests.test_webhooks import _UpdateSpyQuery
from app.services.lenco_webhook import verify_signature, extract_event_fields


# Helper to compute a valid signature the way Lenco does.
def _sign(body: bytes, key: str) -> str:
    return hmac.new(key.encode("utf-8"), body, hashlib.sha512).hexdigest()


class TestVerifySignature:
    def test_valid_with_dedicated_webhook_secret(self):
        body = b'{"event":"collection.successful"}'
        sig = _sign(body, "secret-A")
        assert verify_signature(body, sig, webhook_secret="secret-A", api_key="secret-B") is True

    def test_falls_back_to_api_key_when_secret_empty(self):
        body = b'{"x":1}'
        sig = _sign(body, "api-key-only")
        assert verify_signature(body, sig, webhook_secret="", api_key="api-key-only") is True

    def test_accepts_either_key_during_migration(self):
        """When BOTH keys are set, signatures from either should verify.
        Lets a deployment rotate from API-key-signing to dedicated-secret
        without dropping in-flight deliveries."""
        body = b'{"x":1}'
        sig_with_api = _sign(body, "api-key")
        assert verify_signature(
            body, sig_with_api,
            webhook_secret="dedicated",
            api_key="api-key",
        ) is True

    def test_rejects_wrong_signature(self):
        body = b'{"event":"collection.successful"}'
        bad_sig = "a" * 128
        assert verify_signature(body, bad_sig, webhook_secret="secret-A") is False

    def test_rejects_missing_signature(self):
        body = b'{"x":1}'
        assert verify_signature(body, "", webhook_secret="secret-A") is False

    def test_rejects_when_no_keys_configured(self):
        body = b'{"x":1}'
        sig = _sign(body, "irrelevant")
        assert verify_signature(body, sig, webhook_secret="", api_key="") is False

    def test_signature_case_insensitive(self):
        """Lenco sends lowercase hex; be lenient about uppercase."""
        body = b'{"x":1}'
        sig = _sign(body, "k").upper()
        assert verify_signature(body, sig, webhook_secret="k") is True

    def test_signature_strips_whitespace(self):
        body = b'{"x":1}'
        sig = "  " + _sign(body, "k") + "\n"
        assert verify_signature(body, sig, webhook_secret="k") is True

    def test_tampered_body_fails_verification(self):
        body = b'{"event":"collection.successful","amount":12500}'
        sig = _sign(body, "k")
        tampered = b'{"event":"collection.successful","amount":99999999}'
        assert verify_signature(tampered, sig, webhook_secret="k") is False


class TestExtractEventFields:
    def test_collection_successful_marks_paid(self):
        payload = {
            "event": "collection.successful",
            "data": {
                "reference": "ZEDCV-abc",
                "transactionRef": "LEN-xyz",
                "status": "successful",
                "amount": 12500,
                "currency": "ZMW",
            },
        }
        f = extract_event_fields(payload)
        assert f["is_paid"] is True
        assert f["is_failed"] is False
        assert f["company_ref"] == "ZEDCV-abc"
        assert f["lenco_ref"] == "LEN-xyz"
        assert f["amount_ngwee"] == 12500
        assert f["currency"] == "ZMW"

    def test_failed_event_marks_failed(self):
        payload = {"event": "collection.failed", "data": {"status": "failed", "reference": "x"}}
        f = extract_event_fields(payload)
        assert f["is_paid"] is False
        assert f["is_failed"] is True

    def test_pending_is_neither(self):
        payload = {"event": "collection.pending", "data": {"status": "pending", "reference": "x"}}
        f = extract_event_fields(payload)
        assert f["is_paid"] is False
        assert f["is_failed"] is False

    def test_amount_coerces_strings_and_floats(self):
        assert extract_event_fields({"data": {"amount": "12500"}})["amount_ngwee"] == 12500
        assert extract_event_fields({"data": {"amount": 12500.0}})["amount_ngwee"] == 12500
        assert extract_event_fields({"data": {"amount": None}})["amount_ngwee"] is None

    def test_handles_non_dict_payload(self):
        """Best-effort: a totally malformed payload shouldn't crash."""
        f = extract_event_fields("not a dict")  # type: ignore[arg-type]
        assert f == {}

    def test_handles_missing_data_key(self):
        f = extract_event_fields({"event": "collection.successful"})
        assert f["is_paid"] is True  # event suffix implies success
        assert f["company_ref"] is None


class TestLencoWebhookRoute:
    """End-to-end test through the FastAPI route. Mounts a known signing
    key into settings via the test env, then sends a signed request."""

    def test_missing_signature_returns_401(self, client, fake_supabase):
        resp = client.post(
            "/api/v1/webhooks/lenco",
            json={"event": "collection.successful"},
        )
        assert resp.status_code == 401

    def test_wrong_signature_returns_401(self, client, fake_supabase):
        resp = client.post(
            "/api/v1/webhooks/lenco",
            headers={"x-lenco-signature": "deadbeef" * 16},
            json={"event": "collection.successful"},
        )
        assert resp.status_code == 401

    @patch("app.services.email.send_payment_confirmation_email")
    @patch("app.services.whatsapp.send_whatsapp_message")
    def test_valid_signature_completes_payment(
        self, mock_wa, mock_email, client, fake_supabase, monkeypatch
    ):
        """Valid signature + paid status updates payment + upgrades sub."""
        # Inject a known signing key via the lru_cached settings instance
        from app.core.config import get_settings
        get_settings.cache_clear()
        monkeypatch.setenv("LENCO_API_KEY", "test-lenco-key")
        monkeypatch.setenv("LENCO_WEBHOOK_SECRET", "")
        settings = get_settings()
        assert settings.lenco_api_key == "test-lenco-key"

        body_dict = {
            "event": "collection.successful",
            "data": {
                "reference": "pay-123",
                "transactionRef": "LEN-abc",
                "status": "successful",
                "amount": 12500,  # Starter tier price
                "currency": "ZMW",
            },
        }
        body_bytes = json.dumps(body_dict).encode("utf-8")
        sig = _sign(body_bytes, "test-lenco-key")

        # Wire fakes for the lookup chain.
        fake_supabase.set_table(
            "payments",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "pay-123",
                        "user_id": "user-1",
                        "amount": 12500,
                        "status": "pending",
                        "subscriptions": {"id": "sub-1", "current_period_end": None},
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "users", FakeSupabaseQuery(data=[{"id": "user-1", "phone": "+260971234567"}])
        )

        resp = client.post(
            "/api/v1/webhooks/lenco",
            headers={
                "x-lenco-signature": sig,
                "Content-Type": "application/json",
            },
            content=body_bytes,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    @patch("app.services.email.send_payment_confirmation_email")
    @patch("app.services.whatsapp.send_whatsapp_message")
    def test_lenco_payment_sets_user_and_subscription_billing_period(
        self, mock_wa, mock_email, client, fake_supabase, monkeypatch
    ):
        """Successful Lenco webhook must activate billing via Postgres RPC."""
        from app.core.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("LENCO_API_KEY", "test-lenco-key")
        monkeypatch.setenv("LENCO_WEBHOOK_SECRET", "")

        body_dict = {
            "event": "collection.successful",
            "data": {
                "reference": "pay-bill-1",
                "transactionRef": "LEN-bill-abc",
                "status": "successful",
                "amount": 12500,
                "currency": "ZMW",
            },
        }
        body_bytes = json.dumps(body_dict).encode("utf-8")
        sig = _sign(body_bytes, "test-lenco-key")

        fake_supabase.set_table(
            "payments",
            _UpdateSpyQuery(
                data=[
                    {
                        "id": "pay-bill-1",
                        "user_id": "user-1",
                        "amount": 12500,
                        "status": "pending",
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
                "x-lenco-signature": sig,
                "Content-Type": "application/json",
            },
            content=body_bytes,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

        assert len(subs_spy.update_calls) == 1
        assert subs_spy.update_calls[0]["tier"] == "starter"
        assert subs_spy.update_calls[0]["current_period_start"]
        assert subs_spy.update_calls[0]["current_period_end"]
        assert subs_spy.update_calls[0]["started_at"]

        assert len(users_spy.update_calls) == 1
        assert users_spy.update_calls[0]["subscription_tier"] == "starter"
        assert users_spy.update_calls[0]["subscription_started_at"]
        assert users_spy.update_calls[0]["subscription_expires_at"]
        assert users_spy.update_calls[0]["subscription_renews_at"]

    @patch("app.services.email.send_payment_confirmation_email")
    @patch("app.services.whatsapp.send_whatsapp_message")
    def test_idempotency_skips_already_completed(
        self, mock_wa, mock_email, client, fake_supabase, monkeypatch
    ):
        """A duplicate webhook on a completed payment is a no-op (status:
        already_processed). Prevents double-resetting matches_used."""
        from app.core.config import get_settings
        get_settings.cache_clear()
        monkeypatch.setenv("LENCO_API_KEY", "test-lenco-key")
        monkeypatch.setenv("LENCO_WEBHOOK_SECRET", "")

        body_dict = {
            "event": "collection.successful",
            "data": {
                "reference": "pay-dup",
                "status": "successful",
                "amount": 12500,
            },
        }
        body_bytes = json.dumps(body_dict).encode("utf-8")
        sig = _sign(body_bytes, "test-lenco-key")

        fake_supabase.set_table(
            "payments",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "pay-dup",
                        "user_id": "user-1",
                        "amount": 12500,
                        "status": "completed",  # already done
                        "subscriptions": {},
                    }
                ]
            ),
        )

        resp = client.post(
            "/api/v1/webhooks/lenco",
            headers={"x-lenco-signature": sig, "Content-Type": "application/json"},
            content=body_bytes,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "already_processed"
