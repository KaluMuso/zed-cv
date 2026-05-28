-- 079: Web Push (VAPID) subscriptions for high-match browser alerts

BEGIN;

CREATE TABLE IF NOT EXISTS web_push_subscriptions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint    TEXT NOT NULL,
    p256dh      TEXT NOT NULL,
    auth_secret TEXT NOT NULL,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (endpoint)
);

CREATE INDEX IF NOT EXISTS idx_web_push_subscriptions_user
    ON web_push_subscriptions (user_id);

COMMENT ON TABLE web_push_subscriptions IS
    'Browser Push API subscriptions (VAPID). One row per device endpoint.';

ALTER TABLE web_push_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY web_push_subscriptions_self ON web_push_subscriptions
    FOR SELECT USING (user_id = auth.uid());

COMMIT;
