-- 100: In-app notification inbox (navbar dropdown).
--
-- Phase 0 v1 types: web_push, tier_expiry, invoice, admin_broadcast.
-- Distinct from user_notifications (050) which tracks digest dedup only.

BEGIN;

CREATE TABLE IF NOT EXISTS notifications (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type       VARCHAR(40) NOT NULL
               CHECK (type IN (
                   'web_push',
                   'tier_expiry',
                   'invoice',
                   'admin_broadcast'
               )),
    payload    JSONB NOT NULL DEFAULT '{}'::jsonb,
    read_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_created
    ON notifications (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
    ON notifications (user_id)
    WHERE read_at IS NULL;

COMMENT ON TABLE notifications IS
    'User-facing in-app notification inbox (web push history, tier reminders, invoices, admin broadcasts).';

COMMENT ON COLUMN notifications.payload IS
    'Display + routing: title, body, url (app path), plus type-specific ids.';

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY notifications_self_select ON notifications
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY notifications_self_update ON notifications
    FOR UPDATE USING (user_id = auth.uid());

COMMIT;
