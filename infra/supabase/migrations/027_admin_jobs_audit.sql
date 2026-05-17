-- 027_admin_jobs_audit.sql
-- Adds an audit column tracking which admin last edited a job via the
-- /api/v1/admin/jobs CRUD endpoints. NULL for scraper-inserted or
-- pre-audit-era rows; set on every admin POST/PATCH/DELETE.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS makes this safe to re-apply.
-- updated_at already exists on public.jobs (default now()) — see
-- migration 001. The /admin/jobs PATCH endpoint sets it explicitly on
-- write because there is no UPDATE trigger.

BEGIN;

ALTER TABLE public.jobs
  ADD COLUMN IF NOT EXISTS updated_by_user_id uuid REFERENCES public.users(id);

COMMENT ON COLUMN public.jobs.updated_by_user_id IS
  'User who last manually edited this job via /api/v1/admin/jobs. '
  'NULL for scraper-inserted or pre-audit-era rows.';

COMMIT;
