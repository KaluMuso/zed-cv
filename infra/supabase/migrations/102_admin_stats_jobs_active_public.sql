-- 102: admin_stats() with job review counters and jobs_active_public.
-- Merges the former 099_admin_stats_job_review_counts + jobs_active_public extension.
-- Apply after 099_match_dismiss_note (same numeric generation; distinct files).

BEGIN;

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

COMMIT;
