-- 039_apply_source_tracking.sql
-- Track how apply links were resolved + throttle deep-link enrichment retries.

BEGIN;

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS apply_source TEXT
        CHECK (apply_source IS NULL OR apply_source IN ('direct', 'source_fallback', 'enriched')),
    ADD COLUMN IF NOT EXISTS enrichment_attempted_at TIMESTAMPTZ;

COMMENT ON COLUMN public.jobs.apply_source IS
    'How the user can apply: direct (scraper), enriched (deep-link fetch), source_fallback (listing URL only).';
COMMENT ON COLUMN public.jobs.enrichment_attempted_at IS
    'Last deep-link enrichment attempt; prevents re-fetching dead-end source URLs every ingest tick.';

CREATE INDEX IF NOT EXISTS idx_jobs_missing_apply_with_source
    ON public.jobs (enrichment_attempted_at)
    WHERE apply_url IS NULL
      AND apply_email IS NULL
      AND source_url IS NOT NULL;

COMMIT;
