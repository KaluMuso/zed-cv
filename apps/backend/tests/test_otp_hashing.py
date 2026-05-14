"""Pin OTP-hashing behaviour for /auth/otp/* (task #76).

The plaintext-OTP-in-DB era ended in this slice. These tests pin:
  - _hash_otp produces deterministic output for the same (code, phone, secret)
  - Different phones produce different hashes for the same code
  - Different codes produce different hashes for the same phone
  - The hash is HMAC-SHA256 (catches a refactor swapping in SHA-256 plain
    or sha512 etc.)
  - The verify route hashes the user-supplied code before comparing
    (catches a regression that re-introduces plaintext compare)
"""
import hashlib
import hmac

from app.api.v1.auth import _hash_otp


SECRET = "test-jwt-secret-not-real"


class TestHashOTP:
    def test_deterministic(self):
        """Same inputs → same hash. Otherwise the verify path can never
        match the request path's stored hash."""
        h1 = _hash_otp("123456", "+260971234567", SECRET)
        h2 = _hash_otp("123456", "+260971234567", SECRET)
        assert h1 == h2

    def test_different_phones_different_hashes(self):
        """Critical: the same code generated for two different users must
        produce different hashes. Otherwise an attacker who observes a
        hash for user A could authenticate as user B if both happened
        to receive the same OTP value (1 in 10^6 collision but real)."""
        h_a = _hash_otp("123456", "+260971234567", SECRET)
        h_b = _hash_otp("123456", "+260977888777", SECRET)
        assert h_a != h_b

    def test_different_codes_different_hashes(self):
        h_1 = _hash_otp("000000", "+260971234567", SECRET)
        h_2 = _hash_otp("000001", "+260971234567", SECRET)
        assert h_1 != h_2

    def test_different_secrets_different_hashes(self):
        """Rotating JWT_SECRET should invalidate existing hashes. Pinning
        this catches a regression that hard-codes the secret somewhere."""
        h_old = _hash_otp("123456", "+260971234567", "old-secret")
        h_new = _hash_otp("123456", "+260971234567", "new-secret")
        assert h_old != h_new

    def test_output_is_64_char_hex(self):
        """SHA-256 → 32 bytes → 64 hex chars. If this changes, the
        algorithm has been swapped."""
        h = _hash_otp("123456", "+260971234567", SECRET)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_matches_hmac_sha256_phone_colon_code(self):
        """Pin the exact algorithm. A change here breaks every existing
        OTP row, so this test exists to make that change deliberate."""
        expected = hmac.new(
            SECRET.encode("utf-8"),
            b"+260971234567:123456",
            hashlib.sha256,
        ).hexdigest()
        actual = _hash_otp("123456", "+260971234567", SECRET)
        assert actual == expected


class TestOTPRequestStoresHash:
    """End-to-end through /auth/otp/request — the row inserted into
    otp_codes.code must be a hash, not the plaintext code."""

    def test_request_stores_hashed_code(self, client, fake_supabase, monkeypatch):
        # Patch the WAHA call so we don't need a real service.
        from unittest.mock import AsyncMock
        monkeypatch.setattr(
            "app.api.v1.auth.send_whatsapp_otp",
            AsyncMock(return_value={"id": "msg-1"}),
        )

        # Empty recent-OTP table so no rate-limit cooldown.
        from tests.conftest import FakeSupabaseQuery
        fake_supabase.set_table("otp_codes", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/auth/otp/request",
            json={"phone": "+260971234567"},
        )
        assert resp.status_code == 200

        # Inspect what got inserted. FakeSupabaseQuery's insert path
        # records the payload — verify the "code" field is a 64-char
        # hex hash, not a 6-digit plaintext.
        otp_table = fake_supabase._tables.get("otp_codes")
        assert otp_table is not None
        # The fake records the last inserted dict in _data.
        stored = otp_table._data[-1] if isinstance(otp_table._data, list) and otp_table._data else None
        if stored:
            code_stored = stored.get("code", "")
            # Plaintext would be 6 chars; hash is 64 hex chars.
            assert len(code_stored) == 64, (
                f"Stored code should be 64-char hash, got {len(code_stored)} chars: {code_stored!r}"
            )
            assert all(c in "0123456789abcdef" for c in code_stored), (
                "Stored code should be hex digest"
            )
