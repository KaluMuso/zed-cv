-- 061: Dual-channel notification preference (email default, WhatsApp Starter+).
--
-- preferred_notification_channel drives daily digest routing in the backend.
-- Existing paid users with verified WhatsApp keep WhatsApp digests until they
-- change the setting; everyone else defaults to email.

BEGIN;

DO $$
BEGIN
    CREATE TYPE preferred_notification_channel AS ENUM ('email', 'whatsapp', 'both');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS preferred_notification_channel preferred_notification_channel
        NOT NULL DEFAULT 'email';

COMMENT ON COLUMN users.preferred_notification_channel IS
    'Daily match digest channel: email (default), whatsapp (Starter+), or both.';

-- Preserve delivery for paid users already on verified WhatsApp daily alerts.
UPDATE users u
SET preferred_notification_channel = 'whatsapp'
WHERE u.whatsapp_verified = true
  AND u.alert_frequency = 'daily'
  AND COALESCE(u.subscription_tier, 'free') IN ('starter', 'professional', 'super_standard')
  AND u.preferred_notification_channel = 'email';

COMMIT;
