-- 010_admin_stats_and_tier_constraints.sql
--
-- Two fixes that should have shipped in earlier migrations:
--
-- 1. Add the public.admin_stats() RPC the backend has always called but
--    never had. apps/backend/app/api/v1/admin.py calls
--    supabase.rpc("admin_stats") on every /admin/stats hit. Until this
--    migration lands the function doesn't exist and the call 500s with
--    "Could not find the function public.admin_stats without parameters
--    in the schema cache". Discovered via Sentry on 2026-05-10.
--
-- 2. Bring the subscription tier CHECK constraints into line with
--    reality. users_subscription_tier_check and subscriptions_tier_check
--    both allow only ('free','starter','professional'). super_standard
--    tier was added in migration 005 and is wired throughout the
--    codebase, but the CHECK constraints were never updated. Admin tier
--    updates targeting super_standard fail with check_violation. This
--    is §10 #1 from the audit ("CHECK constraints are stale") — the
--    fix only partially landed; this migration finishes it.

BEGIN;

-- ── Fix 2: tier CHECK constraints ────────────────────────────────────
-- Idempotent: DROP IF EXISTS handles re-runs; recreate is identical.
ALTER TABLE public.users
    DROP CONSTRAINT IF EXISTS users_subscription_tier_check;
ALTER TABLE public.users
    ADD CONSTRAINT users_subscription_tier_check
    CHECK (subscription_tier IN ('free', 'starter', 'professional', 'super_standard'));

ALTER TABLE public.subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_tier_check;
ALTER TABLE public.subscriptions
    ADD CONSTRAINT subscriptions_tier_check
    CHECK (tier IN ('free', 'starter', 'professional', 'super_standard'));

-- ── Fix 1: admin_stats() RPC ─────────────────────────────────────────
-- Returns a single row of counters matching the AdminStats Pydantic
-- schema at apps/backend/app/schemas/admin.py. supabase-py wraps
-- RETURNS TABLE as list[dict]; admin.py:get_stats handles both
-- list-of-one and dict shapes (defensive normalization landed in the
-- 2D-1z test-fix slice).
--
-- SECURITY DEFINER + SET search_path: function runs as the function
-- owner (supabase superuser) regardless of caller. The backend uses the
-- service_role key so this is mostly defence-in-depth.
CREATE OR REPLACE FUNCTION public.admin_stats()
RETURNS TABLE (
    users_total INTEGER,
    users_active_30d INTEGER,
    subscriptions_active INTEGER,
    subscriptions_paid INTEGER,
    jobs_total INTEGER,
    jobs_active INTEGER,
    jobs_expired INTEGER,
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
        -- Activity proxy: users created in last 30 days. Replace with a
        -- real last_active_at lookup if/when that column is added.
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
