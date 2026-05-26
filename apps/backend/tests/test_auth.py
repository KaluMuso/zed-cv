"""Smoke tests for auth routes."""
from unittest.mock import AsyncMock, patch
from tests.conftest import FakeSupabaseQuery


class TestOTPRequest:
    @patch("app.api.v1.auth.send_otp", new_callable=AsyncMock)
    @patch("app.api.v1.auth.lookup_user_auth_context", return_value=None)
    def test_request_otp_success(self, mock_lookup, mock_send, client, fake_supabase):
        """OTP request dispatches via send_otp."""
        fake_supabase.set_table("otp_codes", FakeSupabaseQuery(data=[]))
        resp = client.post(
            "/api/v1/auth/otp/request", json={"phone": "+260971234567"}
        )
        assert resp.status_code == 200
        assert "OTP sent" in resp.json()["message"]
        mock_send.assert_awaited_once()

    @patch("app.api.v1.auth.send_otp", new_callable=AsyncMock, side_effect=RuntimeError("WAHA down"))
    @patch("app.api.v1.auth.lookup_user_auth_context", return_value=None)
    def test_request_otp_delivery_failure_returns_503(
        self, mock_lookup, mock_send, client, fake_supabase
    ):
        """When delivery fails, return 503."""
        fake_supabase.set_table("otp_codes", FakeSupabaseQuery(data=[]))
        resp = client.post(
            "/api/v1/auth/otp/request", json={"phone": "+260971234567"}
        )
        assert resp.status_code == 503
        mock_send.assert_awaited_once()

    @patch("app.api.v1.auth.send_otp", new_callable=AsyncMock)
    @patch(
        "app.api.v1.auth.lookup_user_auth_context",
        return_value={"id": "u1", "email": "user@example.com", "tier": "free"},
    )
    def test_request_otp_email_failure_returns_problem_json(
        self, mock_lookup, mock_send, client, fake_supabase
    ):
        """Email OTP failures expose machine codes in RFC 7807 detail."""
        from app.services.email_delivery import (
            EMAIL_PROVIDER_UNAVAILABLE,
            EmailDeliveryError,
        )

        mock_send.side_effect = EmailDeliveryError(EMAIL_PROVIDER_UNAVAILABLE)
        fake_supabase.set_table("otp_codes", FakeSupabaseQuery(data=[]))
        resp = client.post(
            "/api/v1/auth/otp/request",
            json={"phone": "+260971234567", "channel": "email"},
        )
        assert resp.status_code == 503
        assert resp.headers["content-type"].startswith("application/problem+json")
        body = resp.json()
        assert body["detail"] == EMAIL_PROVIDER_UNAVAILABLE
        assert "WhatsApp" in body["user_message"]

    @patch("app.api.v1.auth.send_otp", new_callable=AsyncMock)
    @patch("app.api.v1.auth.lookup_user_auth_context", return_value=None)
    def test_request_otp_rate_limited(self, mock_send, mock_lookup, client, fake_supabase):
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

    def test_verify_invalid_code_increments_attempts(self, client, fake_supabase):
        """Wrong code path bumps attempts on the latest unverified OTP row.

        Regression test for the brute-force window: previously the row was only
        updated to verified=True on success, so the attempts >= max guard was
        dead code.
        """
        captured = {}

        class StubQuery(FakeSupabaseQuery):
            """First select returns no match (wrong code); second select returns
            the latest unverified row; update() captures the payload."""

            def __init__(self):
                super().__init__(data=[])
                self._call = 0

            def select(self, *a, **kw):
                self._call += 1
                if self._call == 1:
                    self._data = []
                else:
                    self._data = [{"id": "otp-9", "attempts": 2}]
                return self

            def update(self, data):
                captured["payload"] = data
                return self

        fake_supabase.set_table("otp_codes", StubQuery())
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+260971234567", "code": "999999"},
        )
        assert resp.status_code == 401
        assert captured.get("payload") == {"attempts": 3}

    def _seed_new_user_verify(self, fake_supabase):
        """Common fixture: valid unverified OTP, empty users table (so the
        verify path treats this as a new-user signup)."""
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

    def test_verify_valid_code_new_user(self, client, fake_supabase):
        """Valid OTP for new user with consent_accepted=true creates account
        and returns tokens."""
        self._seed_new_user_verify(fake_supabase)
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={
                "phone": "+260971234567",
                "code": "123456",
                "consent_accepted": True,
                "email": "newuser@example.com",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert "user_id" in body

    def test_verify_new_user_missing_email_rejected(self, client, fake_supabase):
        """New signups must include an email for digest delivery."""
        self._seed_new_user_verify(fake_supabase)
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={
                "phone": "+260971234567",
                "code": "123456",
                "consent_accepted": True,
            },
        )
        assert resp.status_code == 400
        assert "Email" in resp.json()["detail"]

    def test_verify_new_user_missing_consent_rejected(self, client, fake_supabase):
        """New user signup without consent_accepted in the payload returns 400.

        The frontend gates the submit button behind a consent checkbox, but
        the backend is the source of truth — a hand-crafted request without
        the field must be rejected.
        """
        self._seed_new_user_verify(fake_supabase)
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+260971234567", "code": "123456"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Consent required"

    def test_verify_new_user_consent_false_rejected(self, client, fake_supabase):
        """Explicit consent_accepted=false is also rejected with 400 — only
        an explicit true unlocks account creation."""
        self._seed_new_user_verify(fake_supabase)
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={
                "phone": "+260971234567",
                "code": "123456",
                "consent_accepted": False,
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Consent required"

    def test_verify_existing_user_no_consent_needed(self, client, fake_supabase):
        """Existing users already consented at original signup; subsequent
        logins must not require the field. Otherwise every existing user
        would be locked out until the frontend ships the checkbox."""
        fake_supabase.set_table(
            "otp_codes",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "otp-2",
                        "phone": "+260971234567",
                        "code": "123456",
                        "verified": False,
                        "attempts": 0,
                        "expires_at": "2099-12-31T00:00:00Z",
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[{"id": "existing-uuid-9", "role": "user"}]
            ),
        )
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+260971234567", "code": "123456"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["user_id"] == "existing-uuid-9"
