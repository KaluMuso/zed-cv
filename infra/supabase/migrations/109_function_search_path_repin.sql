-- migration: 109_function_search_path_repin

-- Auditor finding: set_welcome_bonus() redefined without search_path setting, undoing migration 090.
-- Promote weaker search_path = public declarations on prune_user_notifications and admin_stats.
-- Date: 2026-06-08

BEGIN;

ALTER FUNCTION public.set_welcome_bonus()
  SET search_path = public, pg_catalog;

ALTER FUNCTION public.prune_user_notifications()
  SET search_path = public, pg_catalog;

ALTER FUNCTION public.admin_stats()
  SET search_path = public, pg_catalog;

COMMIT;
