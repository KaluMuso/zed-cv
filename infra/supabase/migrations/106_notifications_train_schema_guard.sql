-- 106: Idempotent schema guard for notifications train (099–105).
--
-- Use when prod applied objects out-of-band or only has ledger row
-- 099_admin_stats_job_review_counts (20260603081919). Safe on fresh DBs that
-- already ran 099–105 — all statements are IF NOT EXISTS / CREATE OR REPLACE.
-- On drifted prod, after this file run scripts/notifications_train_ledger_backfill.sql
-- in the SQL Editor (registry only — do not add that script under migrations/).

BEGIN;

-- ── 099_match_dismiss_note ────────────────────────────────────────────────
ALTER TABLE public.matches
    ADD COLUMN IF NOT EXISTS dismiss_note VARCHAR(500);

COMMENT ON COLUMN public.matches.dismiss_note IS
    'Optional detail when dismiss_reason is other (max 500 chars).';

-- ── 100_in_app_notifications ──────────────────────────────────────────────
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

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

DO $guard_notifications_policies$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'notifications'
          AND policyname = 'notifications_self_select'
    ) THEN
        CREATE POLICY notifications_self_select ON notifications
            FOR SELECT USING (user_id = auth.uid());
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'notifications'
          AND policyname = 'notifications_self_update'
    ) THEN
        CREATE POLICY notifications_self_update ON notifications
            FOR UPDATE USING (user_id = auth.uid());
    END IF;
END;
$guard_notifications_policies$;

-- ── 101_admin_broadcast_notifications ─────────────────────────────────────
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

ALTER TABLE admin_notification_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_notification_recipients ENABLE ROW LEVEL SECURITY;

-- ── 102_admin_stats_jobs_active_public (replaces partial 099_admin_stats) ───
DROP FUNCTION IF EXISTS public.admin_stats();

CREATE OR REPLACE FUNCTION public.admin_stats()
RETURNS TABLE (
    users_total INTEGER,
    users_active_30d INTEGER,
    subscriptions_active INTEGER,
    subscriptions_paid INTEGER,
    jobs_total INTEGER,
    jobs_active INTEGER,
    jobs_expired INTEGER,
    jobs_deactivated INTEGER,
    jobs_need_review INTEGER,
    jobs_active_public INTEGER,
    matches_24h INTEGER,
    matches_total INTEGER,
    revenue_ngwee_30d BIGINT,
    revenue_ngwee_total BIGINT
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        (SELECT COUNT(*)::INTEGER FROM public.users) AS users_total,
        (SELECT COUNT(*)::INTEGER FROM public.users
            WHERE created_at > NOW() - INTERVAL '30 days') AS users_active_30d,
        (SELECT COUNT(*)::INTEGER FROM public.subscriptions
            WHERE status = 'active') AS subscriptions_active,
        (SELECT COUNT(*)::INTEGER FROM public.subscriptions
            WHERE status = 'active' AND tier <> 'free') AS subscriptions_paid,
        (SELECT COUNT(*)::INTEGER FROM public.jobs) AS jobs_total,
        (SELECT COUNT(*)::INTEGER FROM public.jobs
            WHERE is_active = TRUE) AS jobs_active,
        (SELECT COUNT(*)::INTEGER FROM public.jobs
            WHERE is_active = FALSE) AS jobs_expired,
        (SELECT COUNT(*)::INTEGER FROM public.jobs
            WHERE is_active = FALSE) AS jobs_deactivated,
        (SELECT COUNT(*)::INTEGER FROM public.jobs
            WHERE COALESCE(is_review_required, false) = true
              AND admin_reviewed_at IS NULL) AS jobs_need_review,
        (SELECT COUNT(*)::INTEGER FROM public.jobs
            WHERE is_active = TRUE
              AND COALESCE(is_review_required, false) = false
              AND (
                  apply_url IS NOT NULL AND btrim(apply_url) <> ''
                  OR apply_email IS NOT NULL AND btrim(apply_email) <> ''
                  OR contact_phone IS NOT NULL AND btrim(contact_phone) <> ''
                  OR COALESCE(admin_published, false) = true
              )) AS jobs_active_public,
        (SELECT COUNT(*)::INTEGER FROM public.matches
            WHERE created_at > NOW() - INTERVAL '24 hours') AS matches_24h,
        (SELECT COUNT(*)::INTEGER FROM public.matches) AS matches_total,
        COALESCE((SELECT SUM(amount)::BIGINT FROM public.payments
            WHERE status = 'completed'
              AND completed_at > NOW() - INTERVAL '30 days'), 0) AS revenue_ngwee_30d,
        COALESCE((SELECT SUM(amount)::BIGINT FROM public.payments
            WHERE status = 'completed'), 0) AS revenue_ngwee_total;
$$;

-- ── 105_referral_paid_status ──────────────────────────────────────────────
ALTER TABLE public.referral_events
    DROP CONSTRAINT IF EXISTS referral_events_status_check;

ALTER TABLE public.referral_events
    ADD CONSTRAINT referral_events_status_check
    CHECK (status IN ('signed_up', 'qualified', 'paid', 'rewarded'));

ALTER TABLE public.referral_events
    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;

COMMIT;
