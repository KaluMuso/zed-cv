"""Rate limit behaviour for critical public/auth endpoints."""
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import FakeSupabaseQuery


class _OtpCooldownBypassQuery(FakeSupabaseQuery):
    """Always empty selects so only SlowAPI limits apply (not DB cooldown)."""

    def execute(self):
        result = MagicMock()
        result.data = []
        return result


def _enable_limiter():
    from app.core.rate_limit import limiter

    prev = limiter.enabled
    limiter.enabled = True
    try:
        limiter.reset()
    except Exception:
        pass
    return limiter, prev


def _restore_limiter(limiter, prev):
    limiter.enabled = prev
    try:
        limiter.reset()
    except Exception:
        pass


class TestOTPRequestSlowAPI:
    @patch("app.api.v1.auth.send_otp", new_callable=AsyncMock)
    def test_sixth_request_per_phone_returns_429_problem_json(
        self, mock_send_otp, client, fake_supabase
    ):
        """5/hour per phone — 6th call is 429 with RFC 7807 body."""
        fake_supabase.set_table("otp_codes", _OtpCooldownBypassQuery())
        limiter, prev = _enable_limiter()
        phone = "+260971234567"
        try:
            for _ in range(5):
                r = client.post(
                    "/api/v1/auth/otp/request",
                    json={"phone": phone},
                )
                assert r.status_code == 200, r.text
            r6 = client.post(
                "/api/v1/auth/otp/request",
                json={"phone": phone},
            )
            assert r6.status_code == 429, r6.text
            assert "application/problem+json" in r6.headers.get("content-type", "")
            body = r6.json()
            assert body["status"] == 429
            assert "too_many_requests" in body["type"]
            assert "Retry-After" in r6.headers or "retry-after" in {
                k.lower() for k in r6.headers
            }
        finally:
            _restore_limiter(limiter, prev)

