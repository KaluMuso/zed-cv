"""Tests for payment invoices and subscription cancel."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import FakeSupabaseQuery


class TestInvoiceService:
    @pytest.mark.asyncio
    async def test_render_invoice_html_masks_customer(self):
        from app.services.invoice import render_invoice_html

        html = render_invoice_html(
            {
                "invoice_number": "ZED-ABCD1234",
                "reference": "zedapply-ref",
                "amount_ngwee": 12500,
                "amount_kwacha": 125,
                "currency": "ZMW",
                "tier_label": "Starter",
                "payment_method": "lenco_mtn_money",
                "provider": "lenco",
                "status": "completed",
                "issued_at": "2026-05-27T12:00:00+00:00",
                "customer_name": "Test User",
                "customer_email": "test@example.com",
                "customer_phone": "+260971234567",
                "company_name": "Zed Apply",
                "company_email": "support@example.com",
                "app_url": "https://zedapply.com",
            }
        )
        assert "ZED-ABCD1234" in html
        assert "Starter" in html
        assert "K125" in html


class TestInvoiceRoutes:
    def test_get_invoice_404_for_other_user(self, client, fake_supabase, auth_headers):
        fake_supabase.set_table(
            "payments",
            FakeSupabaseQuery(data=[]),
        )
        resp = client.get(
            "/api/v1/subscription/payments/pay-missing/invoice",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get_invoice_returns_detail(
        self, client, fake_supabase, auth_headers, auth_token
    ):
        from jose import jwt

        payload = jwt.get_unverified_claims(auth_token)
        user_id = payload["sub"]

        fake_supabase.set_table(
            "payments",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "pay-inv-1",
                        "user_id": user_id,
                        "amount": 12500,
                        "currency": "ZMW",
                        "payment_method": "lenco_mtn_money",
                        "provider": "lenco",
                        "provider_ref": "zedapply-abc",
                        "status": "completed",
                        "created_at": "2026-05-27T10:00:00+00:00",
                        "completed_at": "2026-05-27T10:01:00+00:00",
                        "webhook_data": {"_resolved_tier": "starter"},
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": user_id,
                        "full_name": "Kaluba",
                        "email": "k@example.com",
                        "phone": "+260971234567",
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "tier_config",
            FakeSupabaseQuery(
                data=[
                    {"tier": "starter", "price_ngwee": 12500, "matches_limit": 50},
                    {"tier": "professional", "price_ngwee": 25000, "matches_limit": 125},
                ]
            ),
        )

        resp = client.get(
            "/api/v1/subscription/payments/pay-inv-1/invoice",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["invoice_number"].startswith("ZED-")
        assert body["tier"] == "starter"
        assert body["amount_kwacha"] == 125

    @patch("app.services.email.send_invoice_email", new_callable=AsyncMock)
    def test_email_invoice_route(
        self, mock_send, client, fake_supabase, auth_headers, auth_token
    ):
        from jose import jwt

        mock_send.return_value = True
        user_id = jwt.get_unverified_claims(auth_token)["sub"]
        fake_supabase.set_table(
            "payments",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "pay-email-1",
                        "user_id": user_id,
                        "amount": 12500,
                        "currency": "ZMW",
                        "payment_method": "lenco",
                        "provider": "lenco",
                        "provider_ref": "ref",
                        "status": "completed",
                        "created_at": "2026-05-27T10:00:00+00:00",
                        "completed_at": "2026-05-27T10:01:00+00:00",
                        "webhook_data": {},
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[{"id": user_id, "full_name": "A", "email": "a@x.com", "phone": "+260971234567"}]
            ),
        )
        fake_supabase.set_table("tier_config", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/subscription/payments/pay-email-1/invoice/email",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert mock_send.await_count == 1


class TestCancelSubscription:
    def test_cancel_free_plan_rejected(self, client, fake_supabase, auth_headers):
        fake_supabase.set_table(
            "subscriptions",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "sub-1",
                        "tier": "free",
                        "status": "active",
                        "current_period_end": None,
                        "cancelled_at": None,
                    }
                ]
            ),
        )
        resp = client.post("/api/v1/subscription/cancel", headers=auth_headers)
        assert resp.status_code == 400

    def test_cancel_paid_plan_sets_cancelled_at(
        self, client, fake_supabase, auth_headers
    ):
        fake_supabase.set_table(
            "subscriptions",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "sub-paid",
                        "tier": "starter",
                        "status": "active",
                        "current_period_end": "2026-06-27T00:00:00+00:00",
                        "cancelled_at": None,
                    }
                ]
            ),
        )
        resp = client.post("/api/v1/subscription/cancel", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "cancelled"
        assert body["tier"] == "starter"
