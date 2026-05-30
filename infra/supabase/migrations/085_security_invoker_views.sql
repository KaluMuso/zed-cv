-- Supabase advisor: security_definer_view on public_jobs and llm_usage_daily.
-- PG15+: run views with the invoker's privileges so RLS on underlying tables applies.
--
-- Rollback (revert to definer semantics):
--   ALTER VIEW public.public_jobs SET (security_invoker = false);
--   ALTER VIEW public.llm_usage_daily SET (security_invoker = false);

BEGIN;

ALTER VIEW public.public_jobs SET (security_invoker = true);
ALTER VIEW public.llm_usage_daily SET (security_invoker = true);

COMMENT ON VIEW public.public_jobs IS
    'Jobs visible on the public /jobs feed (security_invoker; RLS on jobs applies)';

COMMENT ON VIEW public.llm_usage_daily IS
    'Daily LLM usage roll-up for admin dashboards (security_invoker)';

COMMIT;
