-- 119: Expand user_notifications.channel CHECK to include auto-match channels
--
-- The cron-tick auto-match path (_send_due_digest in matches.py) needs its
-- own channel values so it can dedup independently from the daily digest.

BEGIN;

ALTER TABLE user_notifications
  DROP CONSTRAINT IF EXISTS user_notifications_channel_check;

ALTER TABLE user_notifications
  ADD CONSTRAINT user_notifications_channel_check
  CHECK (channel IN (
    'whatsapp_daily_digest',
    'whatsapp_manual',
    'email_digest',
    'whatsapp_auto_match',
    'email_auto_match'
  ));

COMMENT ON CONSTRAINT user_notifications_channel_check ON user_notifications IS
  'Allowed notification channels: daily digest (email/whatsapp), manual whatsapp, auto-match (email/whatsapp).';

COMMIT;
