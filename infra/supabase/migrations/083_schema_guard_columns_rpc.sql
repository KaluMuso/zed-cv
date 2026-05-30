-- 083: RPC for ci_schema_guard.py live mode (information_schema.columns in public).

BEGIN;

CREATE OR REPLACE FUNCTION public.schema_guard_columns()
RETURNS TABLE (table_name text, column_name text)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT c.table_name::text,
           c.column_name::text
    FROM information_schema.columns c
    WHERE c.table_schema = 'public'
    ORDER BY c.table_name, c.ordinal_position;
$$;

REVOKE ALL ON FUNCTION public.schema_guard_columns() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.schema_guard_columns() TO service_role;

COMMENT ON FUNCTION public.schema_guard_columns() IS
    'CI schema-guard: one row per (table, column) in public for drift detection.';

COMMIT;
