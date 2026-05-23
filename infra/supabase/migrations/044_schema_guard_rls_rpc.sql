-- 044: RPC for production_readiness_audit.py — RLS status on audited tables

BEGIN;

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
          'legal_docs'
      )
    ORDER BY c.relname;
$$;

REVOKE ALL ON FUNCTION public.schema_guard_rls() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.schema_guard_rls() TO service_role;

COMMENT ON FUNCTION public.schema_guard_rls() IS
    'Ops audit: returns relrowsecurity for Track-1 RLS tables (migration 040).';

COMMIT;
