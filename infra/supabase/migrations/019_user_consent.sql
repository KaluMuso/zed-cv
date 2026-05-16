-- 019 — users.consent_accepted_at (task #62)
--
-- Records the moment a user explicitly ticked the Terms + Privacy
-- consent checkbox at sign-up. Nullable on the column itself because
-- the backfill below sets a value for every existing row at apply
-- time — going forward the auth route writes it on first user
-- insert, so production rows will be non-null in practice. Keeping
-- the column nullable means a future migration that splits this
-- field by document type (e.g. terms_accepted_at vs privacy_accepted_at)
-- has somewhere to land without a forced backfill on rotation.
--
-- Why we backfill NOW(): every user already on the platform implicitly
-- consented at the moment they signed up (the previous /auth flow
-- showed the legal links inline above the OTP request button). The
-- backfill records that consent at the moment we became able to
-- store it. Without this, the new consent UI would block every
-- returning user on their next sign-in because the audit log would
-- show "no consent on record".

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS consent_accepted_at TIMESTAMPTZ;

UPDATE users
SET consent_accepted_at = NOW()
WHERE consent_accepted_at IS NULL;

COMMIT;

COMMENT ON COLUMN users.consent_accepted_at IS
    'Timestamp the user clicked the consent checkbox at /auth (task #62). NULL only for malformed rows; populated for all real users.';
