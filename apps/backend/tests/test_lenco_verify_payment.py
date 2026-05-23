"""Tests for Lenco widget POST /subscription/verify-payment."""
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import FakeSupabaseQuery


class _SingleQuery(FakeSupabaseQuery):
    def single(self):
        self._single = True
        return self

    def execute(self):
        result = MagicMock()
        if getattr(self, "_single", False) and self._data:
            result.data = (
                self._data[0] if isinstance(self._data, list) else self._data
            )
        else:
            result.data = self._data
        return result


def _seed_subscription(fake_supabase):
    fake_supabase.set_table(
        "subscriptions",
        _SingleQuery(data=[{"id": "sub-1", "user_id": "test-user-id", "tier": "free"}]),
    )


COLLECTION_SUCCESS = {
    "reference": "zedapply-abc",
    "lencoReference": "LEN-9001",
    "amount": "125.00",
    "currency": "ZMW",
    "type": "mobile-money",
    "status": "successful",
    "mobileMoneyDetails": {"operator": "mtn"},
}

COLLECTION_FAILED = {
    **COLLECTION_SUCCESS,
    "status": "failed",
    "reasonForFailure": "Insufficient funds",
}

COLLECTION_PROCESSING = {
    **COLLECTION_SUCCESS,
    "status": "pending",
}


class TestVerifyPaymentEndpoint:
    @patch(
        "app.services.lenco_payment_verify.activate_subscription_after_payment",
        return_value={"start": "2026-01-01T00:00:00+00:00", "end": "2026-02-01T00:00:00+00:00"},
    )
    @patch(
        "app.services.lenco_payment_verify.fetch_collection_status",
        new_callable=AsyncMock,
        return_value=COLLECTION_SUCCESS,
    )
    def test_verify_payment_success_activates_subscription(
        self, _mock_fetch, _mock_activate, client, auth_headers, fake_supabase
    ):
        _seed_subscription(fake_supabase)
        fake_supabase.set_table("payments", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/subscription/verify-payment",
            headers=auth_headers,
            json={"reference": "zedapply-abc", "tier": "starter"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["tier"] == "starter"
        assert body["reference"] == "zedapply-abc"
        _mock_activate.assert_called_once()

    @patch(
        "app.services.lenco_payment_verify.fetch_collection_status",
        new_callable=AsyncMock,
        return_value=COLLECTION_FAILED,
    )
    def test_verify_payment_failed_marks_payment_failed(
        self, _mock_fetch, client, auth_headers, fake_supabase
    ):
        _seed_subscription(fake_supabase)
        fake_supabase.set_table(
            "payments",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "pay-fail-1",
                        "user_id": "test-user-id",
                        "provider_ref": "zedapply-fail",
                        "status": "pending",
                        "subscriptions": {"id": "sub-1"},
                    }
                ]
            ),
        )

        resp = client.post(
            "/api/v1/subscription/verify-payment",
            headers=auth_headers,
            json={"reference": "zedapply-fail", "tier": "starter"},
        )
        assert resp.status_code == 402

    @patch(
        "app.services.lenco_payment_verify.fetch_collection_status",
        new_callable=AsyncMock,
        return_value=COLLECTION_PROCESSING,
    )
    def test_verify_payment_processing_returns_202(
        self, _mock_fetch, client, auth_headers, fake_supabase
    ):
        _seed_subscription(fake_supabase)
        fake_supabase.set_table("payments", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/subscription/verify-payment",
            headers=auth_headers,
            json={"reference": "zedapply-pending", "tier": "starter"},
        )
        assert resp.status_code == 202
        assert resp.json()["status"] == "processing"

    @patch(
        "app.services.lenco_payment_verify.fetch_collection_status",
        new_callable=AsyncMock,
        side_effect=__import__(
            "app.services.lenco", fromlist=["LencoApiError"]
        ).LencoApiError(404, "not found"),
    )
    def test_verify_payment_lenco_404_returns_502(
        self, _mock_fetch, client, auth_headers, fake_supabase
    ):
        _seed_subscription(fake_supabase)
        resp = client.post(
            "/api/v1/subscription/verify-payment",
            headers=auth_headers,
            json={"reference": "zedapply-missing", "tier": "starter"},
        )
        assert resp.status_code == 502

    @patch(
        "app.services.lenco_payment_verify.activate_subscription_after_payment",
        return_value={"start": "2026-01-01T00:00:00+00:00", "end": "2026-02-01T00:00:00+00:00"},
    )
    @patch(
        "app.services.lenco_payment_verify.fetch_collection_status",
        new_callable=AsyncMock,
        return_value=COLLECTION_SUCCESS,
    )
    def test_verify_payment_idempotent_on_duplicate_reference(
        self, _mock_fetch, _mock_activate, client, auth_headers, fake_supabase
    ):
        _seed_subscription(fake_supabase)
        fake_supabase.set_table(
            "payments",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "pay-done",
                        "user_id": "test-user-id",
                        "provider_ref": "zedapply-dup",
                        "status": "completed",
                        "subscriptions": {"id": "sub-1"},
                    }
                ]
            ),
        )

        resp = client.post(
            "/api/v1/subscription/verify-payment",
            headers=auth_headers,
            json={"reference": "zedapply-dup", "tier": "starter"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Payment already verified."
        _mock_fetch.assert_not_called()
        _mock_activate.assert_not_called()


class TestLencoPaymentMethodMapping:
    def test_map_mtn(self):
        from app.services.lenco import map_lenco_payment_method

        assert map_lenco_payment_method(
            {"type": "mobile-money", "mobileMoneyDetails": {"operator": "mtn"}}
        ) == "lenco_mtn_money"

    def test_map_airtel(self):
        from app.services.lenco import map_lenco_payment_method

        assert map_lenco_payment_method(
            {"type": "mobile-money", "mobileMoneyDetails": {"operator": "airtel"}}
        ) == "lenco_airtel_money"

    def test_map_card(self):
        from app.services.lenco import map_lenco_payment_method

        assert map_lenco_payment_method({"type": "card"}) == "lenco_card"
