"""Admin Resend health endpoint."""
from unittest.mock import patch

from app.services.email_delivery import ResendHealthReport


class TestAdminEmailHealth:
    @patch("app.services.email_delivery.check_resend_health")
    def test_returns_report(self, mock_health, client, auth_headers, fake_supabase):
        from tests.conftest import FakeSupabaseQuery

        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[{"id": "test-user-id", "role": "admin"}]
            ),
        )
        mock_health.return_value = ResendHealthReport(
            status="ok",
            code=None,
            message="healthy",
            api_key_configured=True,
            from_email="noreply@zedcv.com",
            from_domain="zedcv.com",
            domain_verified=True,
            domains_listed=1,
        )
        resp = client.get("/api/v1/admin/email/health", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
