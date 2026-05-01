"""Smoke tests for auth routes."""
from unittest.mock import AsyncMock, patch
from tests.conftest import FakeSupabaseQuery


class TestOTPRequest:
    @patch("app.api.v1.auth.send_whatsapp_otp", new_callable=AsyncMock)
    def test_request_otp_success(self, mock_wa, client, fake_supabase):
        """OTP request sends WhatsApp message."""
        fake_supabase.set_table("otp_codes", FakeSupabaseQuery(data=[]))
        resp = client.post(
            "/api/v1/auth/otp/request", json={"phone": "+260971234567"}
        )
        assert resp.status_code == 200
        assert "OTP sent" in resp.json()["message"]

    @patch("app.api.v1.auth.send_whatsapp_otp", new_callable=AsyncMock)
    def test_request_otp_rate_limited(self, mock_wa, client, fake_supabase):
        """Rejects rapid re-requests."""
        fake_supabase.set_table(
            "otp_codes",
            FakeSupabaseQuery(
                data=[{"created_at": "2099-01-01T00:00:00Z"}]
            ),
        )
        resp = client.post(
            "/api/v1/auth/otp/request", json={"phone": "+260971234567"}
        )
        assert resp.status_code == 429

    def test_request_otp_missing_phone(self, client):
        """Missing phone field returns 422."""
        resp = client.post("/api/v1/auth/otp/request", json={})
        assert resp.status_code == 422


class TestOTPVerify:
    def test_verify_invalid_code(self, client, fake_supabase):
        """Invalid OTP returns 401."""
        fake_supabase.set_table("otp_codes", FakeSupabaseQuery(data=[]))
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+260971234567", "code": "000000"},
        )
        assert resp.status_code == 401

    def test_verify_valid_code_new_user(self, client, fake_supabase):
        """Valid OTP for new user creates account and returns tokens."""
        fake_supabase.set_table(
            "otp_codes",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "otp-1",
                        "phone": "+260971234567",
                        "code": "123456",
                        "verified": False,
                        "attempts": 0,
                        "expires_at": "2099-12-31T00:00:00Z",
                    }
                ]
            ),
        )
        fake_supabase.set_table("users", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "subscriptions",
            FakeSupabaseQuery(
                data=[{"id": "sub-1", "user_id": "fake-uuid-001"}]
            ),
        )
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+260971234567", "code": "123456"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert "user_id" in body
