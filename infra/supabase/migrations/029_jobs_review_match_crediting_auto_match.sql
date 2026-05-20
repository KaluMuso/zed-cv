-- 029_jobs_review_match_crediting_auto_match.sql
--
-- Track 4b: listing eligibility review queue, per-unique-job match crediting,
-- and auto-match/notification preferences.

BEGIN;

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS admin_review_reason text NULL,
    ADD COLUMN IF NOT EXISTS admin_reviewed_at timestamptz NULL,
    ADD COLUMN IF NOT EXISTS admin_reviewed_by_user_id uuid NULL REFERENCES public.users(id);

CREATE INDEX IF NOT EXISTS idx_jobs_admin_review
    ON public.jobs (is_active, admin_review_reason)
    WHERE admin_review_reason IS NOT NULL;

ALTER TABLE public.matches
    ADD COLUMN IF NOT EXISTS credited_at timestamptz NULL;

CREATE INDEX IF NOT EXISTS idx_matches_credited
    ON public.matches (user_id, credited_at);

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS last_auto_match_at timestamptz NULL,
    ADD COLUMN IF NOT EXISTS auto_match_enabled boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS notification_channels jsonb DEFAULT '{"whatsapp": true, "email": true}'::jsonb,
    ADD COLUMN IF NOT EXISTS last_notification_at timestamptz NULL;

COMMIT;
