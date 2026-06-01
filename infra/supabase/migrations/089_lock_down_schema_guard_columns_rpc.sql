-- 089: Lock down schema_guard_columns RPC (Supabase advisor: SECURITY DEFINER
-- callable by anon/authenticated). Migration 083 revoked PUBLIC only; Supabase
-- default grants still allow anon/authenticated EXECUTE after CREATE OR REPLACE.
-- Backend and CI use service_role (bypasses RLS; retains EXECUTE).

BEGIN;

REVOKE EXECUTE ON FUNCTION public.schema_guard_columns() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.schema_guard_columns() FROM anon;
REVOKE EXECUTE ON FUNCTION public.schema_guard_columns() FROM authenticated;

GRANT EXECUTE ON FUNCTION public.schema_guard_columns() TO service_role;

COMMIT;
