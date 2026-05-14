-- 018 — Data-subject rights groundwork (task #63)
--
-- Lets the new DELETE /api/v1/me endpoint hard-delete the user row while
-- KEEPING subscription + payment history (anonymised) for 7 years to
-- satisfy Zambian tax/accounting retention obligations described in the
-- Privacy Policy (task #61).
--
-- The mechanism is to:
--   1. Make `user_id` nullable on `subscriptions` and `payments`.
--   2. Change the FK from ON DELETE CASCADE to ON DELETE SET NULL.
--
-- After this migration, a single `DELETE FROM users WHERE id = X` will
-- atomically:
--   - CASCADE-delete the rows the user owns (cvs, matches, user_skills,
--     cv_generations, generated_documents, application_outcomes,
--     cv_upload_queue) — those FKs are unchanged.
--   - NULL out user_id on subscriptions + payments — the row stays for
--     the retention window with no remaining link to the natural person.
--
-- Idempotent: each ALTER guarded by IF EXISTS / DROP IF EXISTS so a
-- re-apply on a partially-migrated DB doesn't 23505.

BEGIN;

-- ── subscriptions.user_id ──
-- Note: subscriptions.user_id is also UNIQUE; we keep the UNIQUE since
-- PostgreSQL treats each NULL as distinct under UNIQUE, so multiple
-- anonymised rows coexist without violating the constraint.
ALTER TABLE subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_user_id_fkey;

ALTER TABLE subscriptions
    ALTER COLUMN user_id DROP NOT NULL;

ALTER TABLE subscriptions
    ADD CONSTRAINT subscriptions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- ── payments.user_id ──
ALTER TABLE payments
    DROP CONSTRAINT IF EXISTS payments_user_id_fkey;

ALTER TABLE payments
    ALTER COLUMN user_id DROP NOT NULL;

ALTER TABLE payments
    ADD CONSTRAINT payments_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

COMMIT;

COMMENT ON COLUMN subscriptions.user_id IS
    'Nullable — set to NULL when the owning user exercises right-to-erasure (task #63). Row retained for 7-year tax/accounting window.';
COMMENT ON COLUMN payments.user_id IS
    'Nullable — set to NULL when the owning user exercises right-to-erasure (task #63). Row retained for 7-year tax/accounting window.';
