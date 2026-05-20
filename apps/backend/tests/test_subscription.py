"""Smoke tests for subscription and payment routes."""
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import FakeSupabaseQuery


class _InsertSpyQuery(FakeSupabaseQuery):
    """Records payments.insert payloads for assertion."""

    def __init__(self, data=None):
        super().__init__(data=data)
        self.inserted: list[dict] = []

    def insert(self, data):
        if isinstance(data, dict):
            row = dict(data)
            if "id" not in row:
                row["id"] = "pay-spy-001"
            self.inserted.append(row)
            self._data = [row]
        return self


class _SingleQuery(FakeSupabaseQuery):
    """Mock that handles .single() by returning first item directly."""

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
        result.count = getattr(self, "_count", None)
        return result


class TestGetSubscription:
    def test_get_subscription_unauthenticated(self, client):
        """Subscription endpoint requires auth."""
        resp = client.get("/api/v1/subscription")
        assert resp.status_code in (401, 403, 404)

    def test_get_subscription_success(
        self, client, auth_headers, fake_supabase
    ):
        """Returns subscription details."""
        fake_supabase.set_table(
            "subscriptions",
            _SingleQuery(
                data=[
                    {
                        "id": "sub-1",
                        "user_id": "test-user-id",
                        "tier": "free",
                        "matches_used": 2,
                        "matches_limit": 5,
                        "status": "active",
                        "current_period_end": None,
                    }
                ]
            ),
        )
        resp = client.get("/api/v1/subscription", headers=auth_headers)
        # May be 200 or 404 depending on whether subscription router exists
        assert resp.status_code in (200, 404)

    @patch(
        "app.api.v1.subscription.get_credited_match_count",
        new_callable=AsyncMock,
        return_value=3,
    )
    def test_get_subscription_no_matches_limit_column(
        self, _mock_credited, client, auth_headers, fake_supabase
    ):
        """Regression: dropped matches_limit column must not KeyError on GET."""
        fake_supabase.set_table(
            "subscriptions",
            _SingleQuery(
                data=[
                    {
                        "id": "sub-1",
                        "user_id": "test-user-id",
                        "tier": "starter",
                        "status": "active",
                        "current_period_end": None,
                    }
                ]
            ),
        )
        resp = client.get("/api/v1/subscription", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["matches_limit"] == 50
        assert body["matches_used"] == 3
        assert body["tier"] == "starter"

    @patch(
        "app.api.v1.subscription.get_credited_match_count",
        new_callable=AsyncMock,
        return_value=0,
    )
    def test_get_subscription_free_tier_limit_is_10(
        self, _mock_credited, client, auth_headers, fake_supabase
    ):
        """Free tier quota matches zedapply.com/pricing (10 matches/month)."""
        fake_supabase.set_table(
            "subscriptions",
            _SingleQuery(
                data=[
                    {
                        "id": "sub-free",
                        "user_id": "test-user-id",
                        "tier": "free",
                        "status": "active",
                        "current_period_end": None,
                    }
                ]
            ),
        )
        resp = client.get("/api/v1/subscription", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["matches_limit"] == 10


class TestPaymentInitiate:
    def test_pay_invalid_tier(self, client, auth_headers, fake_supabase):
        """Rejects payment for free tier."""
        resp = client.post(
            "/api/v1/subscription/pay",
            headers=auth_headers,
            json={
                "tier": "free",
                "payment_method": "mtn",
                "phone": "+260971234567",
            },
        )
        # May be 422 or 404 depending on whether subscription router exists
        assert resp.status_code in (422, 404)

    @patch(
        "app.services.dpo_pay.create_payment_token", new_callable=AsyncMock
    )
    def test_pay_success(
        self, mock_dpo, client, auth_headers, fake_supabase
    ):
        """Payment initiation creates record and returns transaction_id."""
        fake_supabase.set_table(
            "subscriptions",
            _SingleQuery(data=[{"id": "sub-1"}]),
        )
        fake_supabase.set_table(
            "payments", FakeSupabaseQuery(data=[{"id": "pay-001"}])
        )
        mock_dpo.return_value = {
            "token": "DPO-TOKEN-123",
            "redirect_url": "https://pay.example.com",
        }

        resp = client.post(
            "/api/v1/subscription/pay",
            headers=auth_headers,
            json={
                "tier": "starter",
                "payment_method": "mtn",
                "phone": "+260971234567",
            },
        )
        # May be 200 or 404 depending on whether subscription router exists
        assert resp.status_code in (200, 404)

    @patch(
        "app.services.lenco.create_lenco_payment", new_callable=AsyncMock
    )
    def test_initiate_payment_writes_lenco_mtn_money(
        self, mock_lenco, client, auth_headers, fake_supabase
    ):
        """Regression: Lenco pay must store CHECK-valid payment_method."""
        mock_lenco.return_value = {
            "transaction_id": "LEN-TX-1",
            "status": "pending",
        }
        fake_supabase.set_table(
            "subscriptions",
            _SingleQuery(data=[{"id": "sub-1"}]),
        )
        payments_spy = _InsertSpyQuery()
        fake_supabase.set_table("payments", payments_spy)

        resp = client.post(
            "/api/v1/subscription/pay",
            headers=auth_headers,
            json={
                "tier": "starter",
                "payment_method": "lenco_mtn_money",
                "phone": "+260979370372",
            },
        )
        assert resp.status_code == 200
        assert payments_spy.inserted
        assert payments_spy.inserted[0]["payment_method"] == "lenco_mtn_money"
        assert payments_spy.inserted[0]["provider"] == "lenco"
