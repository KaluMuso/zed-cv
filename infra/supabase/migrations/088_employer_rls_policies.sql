-- 088: RLS on employer tables (service-role backend today; blocks direct anon/authenticated DB access).
-- Extends schema_guard_rls for production_readiness_audit.py.
--
-- Backend (service_role) bypasses RLS — all employer writes stay on FastAPI routes.
-- Authenticated policies scope reads to the caller's employer org via employer_users.

BEGIN;

-- ── employers ───────────────────────────────────────────────────────────────
ALTER TABLE public.employers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS employers_member_select ON public.employers;
CREATE POLICY employers_member_select ON public.employers
    FOR SELECT
    TO authenticated
    USING (
        id IN (
            SELECT employer_id
            FROM public.employer_users
            WHERE user_id = auth.uid()
        )
    );

-- ── employer_subscriptions ──────────────────────────────────────────────────
ALTER TABLE public.employer_subscriptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS employer_subscriptions_member_select ON public.employer_subscriptions;
CREATE POLICY employer_subscriptions_member_select ON public.employer_subscriptions
    FOR SELECT
    TO authenticated
    USING (
        employer_id IN (
            SELECT employer_id
            FROM public.employer_users
            WHERE user_id = auth.uid()
        )
    );

-- ── cv_access_audit (service writes; org members may read audit trail) ──────
ALTER TABLE public.cv_access_audit ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cv_access_audit_org_select ON public.cv_access_audit;
CREATE POLICY cv_access_audit_org_select ON public.cv_access_audit
    FOR SELECT
    TO authenticated
    USING (
        employer_user_id IN (
            SELECT eu.user_id
            FROM public.employer_users eu
            WHERE eu.employer_id IN (
                SELECT employer_id
                FROM public.employer_users
                WHERE user_id = auth.uid()
            )
        )
    );

-- ── schema_guard_rls: extend Track-1 RPC with employer tables ───────────────
CREATE OR REPLACE FUNCTION public.schema_guard_rls()
RETURNS TABLE (table_name text, rls_enabled boolean)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT c.relname::text,
           c.relrowsecurity
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'r'
      AND c.relname IN (
          'otp_codes',
          'whatsapp_sessions',
          'user_skills',
          'application_outcomes',
          'skills',
          'skill_aliases',
          'job_skills',
          'job_fingerprints',
          'ai_cache',
          'legal_docs',
          'employers',
          'employer_subscriptions',
          'cv_access_audit'
      )
    ORDER BY c.relname;
$$;

REVOKE ALL ON FUNCTION public.schema_guard_rls() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.schema_guard_rls() TO service_role;

COMMENT ON FUNCTION public.schema_guard_rls() IS
    'Ops audit: relrowsecurity for RLS-audited tables (040 Track-1 + 088 employer).';

-- ── schema_guard_security_invoker_views: migration 085 sentinel ─────────────
CREATE OR REPLACE FUNCTION public.schema_guard_security_invoker_views()
RETURNS TABLE (view_name text, security_invoker boolean)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT c.relname::text,
           COALESCE(
               c.reloptions IS NOT NULL
               AND 'security_invoker=true' = ANY (c.reloptions),
               false
           )
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'v'
      AND c.relname IN ('public_jobs', 'llm_usage_daily')
    ORDER BY c.relname;
$$;

REVOKE ALL ON FUNCTION public.schema_guard_security_invoker_views() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.schema_guard_security_invoker_views() TO service_role;

COMMENT ON FUNCTION public.schema_guard_security_invoker_views() IS
    'Ops audit: security_invoker=true on public_jobs and llm_usage_daily (085).';

COMMIT;

COMMENT ON POLICY employers_member_select ON public.employers IS
    'Employer portal members read their org row; writes via service_role API.';
COMMENT ON POLICY employer_subscriptions_member_select ON public.employer_subscriptions IS
    'Employer portal members read their org subscription; billing via service_role API.';
COMMENT ON POLICY cv_access_audit_org_select ON public.cv_access_audit IS
    'Org members read CV access audit for their employer; inserts via service_role API.';
