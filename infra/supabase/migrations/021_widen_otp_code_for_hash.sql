-- 021_widen_otp_code_for_hash.sql
--
-- HOTFIX for production 500 on /auth/otp/request (2026-05-15).
--
-- Migration 017 introduced HMAC-SHA256 hashing of OTP codes in the FastAPI
-- backend (_hash_otp in apps/backend/app/api/v1/auth.py), but the original
-- `otp_codes.code` column was sized at varchar(6) for the plaintext 6-digit
-- code. The hashed value is a 64-char hex digest, so every
-- /auth/otp/request returned a 500 with:
--
--   postgrest.exceptions.APIError: {'code': '22001', 'message': 'value too
--   long for type character varying(6)'}
--
-- The uvicorn 500 stripped CORS headers on the way back to the browser, so
-- users saw "CORS error" instead of the real schema mismatch — same trap as
-- feedback_zedcv_uvicorn_500_bypasses_cors.md.
--
-- This migration is the schema half of the change that was missing from 017.
-- It has already been applied to production Supabase via the SQL Editor on
-- 2026-05-15; this file exists so a fresh deploy reproduces the same state.
--
-- (Filename is 021 because feat/task-62-consent-and-wysiwyg merged while
-- this hotfix was in flight and claimed both 019 — users.consent_accepted_at
-- — and 020 — legal_docs. Originally numbered 020; renumbered after the
-- collision was spotted on rebase.)
--
-- After this migration runs, the column holds a 64-char HMAC-SHA256 hex
-- digest. The plaintext 6-digit OTP only ever lives in the WhatsApp
-- message and in the user's head during verification.

ALTER TABLE otp_codes ALTER COLUMN code TYPE varchar(64);

COMMENT ON COLUMN otp_codes.code
  IS 'HMAC-SHA256(jwt_secret, phone || '':'' || plaintext_otp), 64-char hex digest. '
     'Widened from varchar(6) in migration 021 to hold the hashed value introduced '
     'by migration 017. The plaintext 6-digit OTP is never persisted.';
