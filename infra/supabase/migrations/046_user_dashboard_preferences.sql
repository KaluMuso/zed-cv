-- 046 — Dashboard user settings on users table
--
-- Backs PATCH /api/v1/users/me/preferences (WhatsApp delivery number,
-- location, display currency, alert cadence). whatsapp_verified is a
-- stub for a future n8n OTP flow — reset to false when the number changes.

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS whatsapp_number VARCHAR(15);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS whatsapp_verified BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'ZMW'
    CHECK (currency IN ('ZMW', 'USD'));

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS alert_frequency VARCHAR(10) NOT NULL DEFAULT 'daily'
    CHECK (alert_frequency IN ('daily', 'weekly', 'muted'));

-- location already exists on users (001_initial_schema.sql).

COMMENT ON COLUMN users.whatsapp_number IS
    'E.164 delivery number (+260XXXXXXXXX). Distinct from auth phone when set.';

COMMENT ON COLUMN users.whatsapp_verified IS
    'True after OTP verification of whatsapp_number; cleared on number change.';

COMMENT ON COLUMN users.currency IS
    'User-facing currency preference for dashboard display (ZMW or USD).';

COMMENT ON COLUMN users.alert_frequency IS
    'Match digest cadence: daily, weekly, or muted.';

COMMIT;
