-- 017_otp_codes_now_hashed.sql
--
-- Purpose:
--   Task #76: otp_codes.code now holds HMAC-SHA256(jwt_secret, phone || ":" || code)
--   instead of the plaintext OTP. Without this change, a database leak
--   (export, replica, accidental dump) would reveal active OTPs for the
--   5-minute TTL window — long enough for an attacker to log in as any
--   user with an OTP outstanding.
--
--   No DDL change required. The column type is already `text` and
--   varchar-sized to fit a 64-char hex digest. This migration is a
--   COMMENT-only documentation step so the schema's intent is recorded
--   at the DB layer.
--
-- Deploy ordering:
--   1. Backend code change (apps/backend/app/api/v1/auth.py) deploys.
--   2. From that moment, all NEW OTP rows are hashes, all NEW verify
--      attempts hash the user-supplied code before comparing.
--   3. Any in-flight plaintext OTPs from the old code path will fail
--      to verify against the new hashed comparison and the user will
--      need to request a fresh OTP. 5-min TTL means this window
--      auto-closes.
--   4. No backfill needed — existing rows expire on their own.
--
-- Idempotency: COMMENT ON COLUMN is fully idempotent. Safe to re-run.

BEGIN;

COMMENT ON COLUMN public.otp_codes.code IS
    'HMAC-SHA256 hex digest of (phone:code) signed with JWT_SECRET. '
    'Plaintext before task #76 deploy on 2026-05-15. '
    'See app/api/v1/auth.py::_hash_otp for the hashing logic. '
    'A DB leak no longer reveals usable OTPs — an attacker would have '
    'to brute-force the 6-digit OTP space against each row''s hash '
    'within the 5-min TTL, which is bounded by the rate-limiter and '
    'max_otp_attempts.';

COMMIT;
