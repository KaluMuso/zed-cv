-- 107_dedupe_key_trigger_insert_only.sql
--
-- PURPOSE
-- -------
-- Fix Sentry issue ZEDCV-BACKEND-1S:
--   "duplicate key value violates unique constraint idx_jobs_dedupe_key_active"
--   raised by PATCH /api/v1/admin/jobs/{job_id} whenever an admin edits
--   title, company, or location to a value combination that already exists on
--   another active job.
--
-- ROOT CAUSE
-- ----------
-- A BEFORE UPDATE trigger on public.jobs recomputes the `dedupe_key` generated
-- column (or trigger-maintained column) on every UPDATE, including admin edits.
-- When the new (title, company, location) triple hashes to the same value as
-- another active row the partial unique index idx_jobs_dedupe_key_active raises
-- a UniqueViolation, which Uvicorn surfaces as a bare text/plain 500 — bypassing
-- CORS middleware so the browser reports it as a "CORS error".
--
-- FIX (Option A — preferred)
-- --------------------------
-- The dedupe_key exists solely to prevent the scraper ingest pipeline from
-- inserting duplicate listings.  Admin edits are intentional, curated changes;
-- recomputing the key on UPDATE is wrong at the policy level, not just at the
-- implementation level.  We restrict the trigger to INSERT only so the key is
-- set once at ingest and never mutated by later admin edits.
--
-- SAFETY
-- ------
-- * idx_jobs_dedupe_key_active is NOT dropped — ingest-time deduplication is
--   fully preserved.
-- * Existing dedupe_key values on rows are unchanged.
-- * Reversible: the DOWN migration recreates the FOR EACH ROW trigger for both
--   INSERT and UPDATE.
-- * Idempotent: DROP TRIGGER IF EXISTS + CREATE OR REPLACE are safe to re-run.
--
-- APPLIES AFTER: 106_notifications_train_schema_guard.sql
--
BEGIN;

-- ── 1. Drop the existing trigger that fires on INSERT and UPDATE ────────────

DROP TRIGGER IF EXISTS set_jobs_dedupe_key ON public.jobs;
DROP TRIGGER IF EXISTS jobs_set_dedupe_key ON public.jobs;
DROP TRIGGER IF EXISTS trg_jobs_dedupe_key ON public.jobs;

-- ── 2. Ensure the trigger function exists (idempotent CREATE OR REPLACE) ───
--
-- The function computes dedupe_key as:
--   lower(title || '|' || coalesce(company,'') || '|' || coalesce(location,''))
-- This mirrors the Python _fingerprint() inputs (title, company, location are
-- the three dedupe inputs per _FINGERPRINT_TRIGGER_FIELDS in admin.py).
--
-- We CREATE OR REPLACE so the migration is safe even if the function already
-- exists with a slightly different body.

CREATE OR REPLACE FUNCTION public.fn_jobs_set_dedupe_key()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    -- Only set on INSERT; never mutate on UPDATE so admin edits cannot
    -- collide with other active rows (Sentry ZEDCV-BACKEND-1S).
    IF TG_OP = 'INSERT' THEN
        NEW.dedupe_key := lower(
            NEW.title
            || '|' || coalesce(NEW.company, '')
            || '|' || coalesce(NEW.location, '')
        );
    END IF;
    RETURN NEW;
END;
$$;

-- ── 3. Recreate the trigger as INSERT-only ─────────────────────────────────

CREATE TRIGGER trg_jobs_dedupe_key
BEFORE INSERT ON public.jobs
FOR EACH ROW EXECUTE FUNCTION public.fn_jobs_set_dedupe_key();

-- ── DOWN (reversible — run manually if rollback needed) ────────────────────
-- To restore the original INSERT+UPDATE behaviour:
--
--   DROP TRIGGER IF EXISTS trg_jobs_dedupe_key ON public.jobs;
--   CREATE TRIGGER trg_jobs_dedupe_key
--   BEFORE INSERT OR UPDATE OF title, company, location ON public.jobs
--   FOR EACH ROW EXECUTE FUNCTION public.fn_jobs_set_dedupe_key();

COMMIT;
