-- 101: Admin broadcast Web Push campaigns (Track 4C schema for 4D compose UI).
-- Depends on 100_in_app_notifications (admin_broadcast rows in notifications inbox).

BEGIN;

CREATE TABLE IF NOT EXISTS admin_notification_campaigns (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title               TEXT NOT NULL CHECK (char_length(title) BETWEEN 1 AND 120),
    body                TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 500),
    url                 TEXT CHECK (url IS NULL OR char_length(url) <= 512),
    target_audience     TEXT NOT NULL CHECK (target_audience IN ('all', 'tier')),
    target_tier         TEXT CHECK (
        (target_audience = 'all' AND target_tier IS NULL)
        OR (
            target_audience = 'tier'
            AND target_tier IN ('free', 'starter', 'professional', 'super_standard')
        )
    ),
    scheduled_at        TIMESTAMPTZ,
    status              TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'scheduled', 'sending', 'completed', 'failed', 'cancelled')),
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    recipients_queued   INTEGER NOT NULL DEFAULT 0,
    recipients_sent     INTEGER NOT NULL DEFAULT 0,
    recipients_failed   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS admin_notification_recipients (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id     UUID NOT NULL REFERENCES admin_notification_campaigns(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sent', 'failed', 'skipped')),
    skip_reason     TEXT,
    sent_at         TIMESTAMPTZ,
    devices_sent    INTEGER NOT NULL DEFAULT 0,
    error           TEXT,
    UNIQUE (campaign_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_admin_notification_recipients_campaign
    ON admin_notification_recipients (campaign_id);

CREATE INDEX IF NOT EXISTS idx_admin_notification_recipients_pending
    ON admin_notification_recipients (campaign_id, status)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_admin_notification_campaigns_due
    ON admin_notification_campaigns (scheduled_at)
    WHERE status IN ('pending', 'scheduled');

COMMENT ON TABLE admin_notification_campaigns IS
    'Admin-composed broadcast push campaigns (all users or by subscription tier).';

COMMENT ON TABLE admin_notification_recipients IS
    'Per-user delivery rows for admin_notification_campaigns.';

ALTER TABLE admin_notification_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_notification_recipients ENABLE ROW LEVEL SECURITY;

COMMIT;
