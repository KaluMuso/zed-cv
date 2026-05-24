-- 063_revoke_security_definer_anon.sql
--
-- Supabase security advisor (2026-05-24): five SECURITY DEFINER functions were
-- executable by anon/authenticated via PostgREST. Revoke public/role grants;
-- retain service_role only (FastAPI backend + n8n cron use SUPABASE_KEY /
-- SUPABASE_SERVICE_ROLE_KEY).
--
-- Frontend does not call these RPCs directly.

BEGIN;

-- Payment activation (webhooks → subscription_billing.py)
REVOKE EXECUTE ON FUNCTION public.activate_subscription_after_payment(
    UUID, UUID, TEXT, UUID, TEXT, INTEGER, TIMESTAMPTZ
) FROM anon, authenticated, PUBLIC;

GRANT EXECUTE ON FUNCTION public.activate_subscription_after_payment(
    UUID, UUID, TEXT, UUID, TEXT, INTEGER, TIMESTAMPTZ
) TO service_role;

-- Admin dashboard aggregates (/admin/stats → admin.py, require_admin)
REVOKE EXECUTE ON FUNCTION public.admin_stats() FROM anon, authenticated, PUBLIC;

GRANT EXECUTE ON FUNCTION public.admin_stats() TO service_role;

-- Admin companies CSV (/admin/export/companies.csv → admin_companies_export.py)
REVOKE EXECUTE ON FUNCTION public.admin_export_companies() FROM anon, authenticated, PUBLIC;

GRANT EXECUTE ON FUNCTION public.admin_export_companies() TO service_role;

-- Daily subscription expiry cron (n8n → subscription_expiry_daily.json)
REVOKE EXECUTE ON FUNCTION public.downgrade_expired_subscriptions() FROM anon, authenticated, PUBLIC;

GRANT EXECUTE ON FUNCTION public.downgrade_expired_subscriptions() TO service_role;

-- Production RLS audit (production_readiness_audit.py)
REVOKE EXECUTE ON FUNCTION public.schema_guard_rls() FROM anon, authenticated, PUBLIC;

GRANT EXECUTE ON FUNCTION public.schema_guard_rls() TO service_role;

COMMIT;
