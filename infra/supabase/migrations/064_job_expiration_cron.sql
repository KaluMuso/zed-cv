-- 064_job_expiration_cron.sql
--
-- Problem: jobs past closing_date stayed is_active=true and could surface in
-- admin views and any path that keys off is_active without the closing_date
-- filter in match_jobs_for_user.
--
-- Fix:
--   1. pg_cron daily at 04:30 CAT (02:30 UTC) calls deactivate_expired_jobs()
--   2. One-time backfill in this migration (NOTICE logs deactivated count)
--
-- Verify after apply:
--   SELECT COUNT(*) FROM jobs
--   WHERE is_active = true AND closing_date < NOW()::date;
--   -- expected: 0
--
-- Idempotent: CREATE EXTENSION IF NOT EXISTS; cron.schedule upserts by job name.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;

GRANT USAGE ON SCHEMA cron TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cron TO postgres;

CREATE OR REPLACE FUNCTION public.deactivate_expired_jobs()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE public.jobs
    SET is_active = false,
        updated_at = NOW()
    WHERE is_active = true
      AND closing_date IS NOT NULL
      AND closing_date < NOW()::date;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;

COMMENT ON FUNCTION public.deactivate_expired_jobs() IS
    'Sets is_active=false for jobs whose closing_date is before today. '
    'Returns the number of rows updated. Scheduled daily via pg_cron.';

-- 04:30 CAT (UTC+2, no DST) = 02:30 UTC. pg_cron uses UTC on Supabase.
SELECT cron.schedule(
    'zedcv-deactivate-expired-jobs',
    '30 2 * * *',
    $$SELECT public.deactivate_expired_jobs();$$
);

DO $$
DECLARE
    v_pending BIGINT;
    v_deactivated INTEGER;
BEGIN
    SELECT COUNT(*)::BIGINT
    INTO v_pending
    FROM public.jobs
    WHERE is_active = true
      AND closing_date IS NOT NULL
      AND closing_date < NOW()::date;

    v_deactivated := public.deactivate_expired_jobs();

    RAISE NOTICE
        '064_job_expiration_cron backfill: pending=%, deactivated=%',
        v_pending,
        v_deactivated;
END;
$$;

COMMIT;
