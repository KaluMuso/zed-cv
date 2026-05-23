-- 050: Track WhatsApp (and other) job digests sent per user
--
-- Prevents the same job from appearing in consecutive daily digests.
-- Backend inserts rows when GET /admin/trigger-daily-digest builds a batch.

BEGIN;

CREATE TABLE IF NOT EXISTS user_notifications (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id     UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    channel    VARCHAR(40) NOT NULL DEFAULT 'whatsapp_daily_digest'
               CHECK (channel IN ('whatsapp_daily_digest', 'whatsapp_manual', 'email_digest')),
    sent_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, job_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_user_notifications_user_sent
    ON user_notifications (user_id, sent_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_notifications_job
    ON user_notifications (job_id);

COMMENT ON TABLE user_notifications IS
    'Jobs already delivered to a user on a given channel (daily WhatsApp digest, etc.).';

ALTER TABLE user_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_notifications_self ON user_notifications
    FOR SELECT USING (user_id = auth.uid());

COMMIT;
