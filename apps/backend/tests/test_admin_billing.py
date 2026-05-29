"""Admin billing observability endpoints."""
from __future__ import annotations

from tests.conftest import FakeSupabaseQuery


def _wire_admin_user(fake_supabase) -> None:
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "admin-user-id",
                    "phone": "+260971111111",
                    "role": "superadmin",
                    "subscription_tier": "super_standard",
                }
            ]
        ),
    )


class TestAdminBillingHealth:
    def test_billing_health_returns_lenco_snapshot(
        self, client, fake_supabase, admin_headers, monkeypatch
    ):
        _wire_admin_user(fake_supabase)
        monkeypatch.setenv("LENCO_ENVIRONMENT", "sandbox")
        monkeypatch.setenv("LENCO_VERIFY_SIGNATURES", "true")
        from app.core.config import get_settings

        get_settings.cache_clear()

        resp = client.get("/api/v1/admin/billing/health", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["lenco_environment"] == "sandbox"
        assert body["webhook_url_expected"].endswith("/webhooks/lenco")
        assert "payments_pending" in body


class TestAdminPaymentDetail:
    def test_payment_detail_includes_webhook_summary(
        self, client, fake_supabase, admin_headers
    ):
        _wire_admin_user(fake_supabase)
        fake_supabase.set_table(
            "payments",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "pay-admin-1",
                        "user_id": "user-1",
                        "amount": 12500,
                        "currency": "ZMW",
                        "payment_method": "lenco_mtn_money",
                        "provider": "lenco",
                        "provider_ref": "zedapply-abc",
                        "status": "completed",
                        "created_at": "2026-05-27T10:00:00+00:00",
                        "completed_at": "2026-05-27T10:01:00+00:00",
                        "webhook_data": {
                            "event": "collection.successful",
                            "data": {
                                "reference": "zedapply-abc",
                                "status": "successful",
                            },
                        },
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "admin-user-id",
                        "phone": "+260971111111",
                        "role": "superadmin",
                        "subscription_tier": "super_standard",
                    },
                    {
                        "id": "user-1",
                        "phone": "+260971234567",
                        "email": "u@example.com",
                        "full_name": "Test User",
                    },
                ]
            ),
        )
        fake_supabase.set_table("tier_config", FakeSupabaseQuery(data=[]))

        resp = client.get(
            "/api/v1/admin/payments/pay-admin-1",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["invoice_number"].startswith("ZED-")
        assert body["webhook_summary"]["event"] == "collection.successful"
        assert body["provider_ref"] == "zedapply-abc"
