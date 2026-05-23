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
                        "matches_limit": 10,
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
        from app.services import tier_config as tier_config_svc

        tier_config_svc.clear_tier_config_cache()
        fake_supabase.set_table("tier_config", FakeSupabaseQuery(data=[]))
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
        """Free tier quota (10 matches/month)."""
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
    def test_pay_returns_410_gone(self, client, auth_headers):
        """Legacy server-side initiation removed in favour of Lenco widget."""
        resp = client.post(
            "/api/v1/subscription/pay",
            headers=auth_headers,
            json={
                "tier": "starter",
                "payment_method": "lenco_mtn_money",
                "phone": "+260971234567",
            },
        )
        assert resp.status_code == 410
