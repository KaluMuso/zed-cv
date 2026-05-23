-- 046: Deep-scrape enrichment columns on jobs
--
-- n8n secondary scrape writes employer-direct apply contacts and the
-- original listing URL (not intermediate job-board redirects).

BEGIN;

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS source_platform VARCHAR(64),
    ADD COLUMN IF NOT EXISTS original_source_url TEXT,
    ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(20),
    ADD COLUMN IF NOT EXISTS contact_whatsapp VARCHAR(64),
    ADD COLUMN IF NOT EXISTS is_enriched BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN public.jobs.source_platform IS
    'Listing site identifier (e.g. gozambiajobs, linkedin, whatsapp).';
COMMENT ON COLUMN public.jobs.original_source_url IS
    'Employer or primary listing URL after deep scrape (not aggregator redirect).';
COMMENT ON COLUMN public.jobs.contact_email IS
    'Application email discovered on the original listing.';
COMMENT ON COLUMN public.jobs.contact_phone IS
    'E.164 phone (+260XXXXXXXXX) for voice/SMS apply path.';
COMMENT ON COLUMN public.jobs.contact_whatsapp IS
    'WhatsApp apply contact: E.164 (+260...) or wa.me link.';
COMMENT ON COLUMN public.jobs.is_enriched IS
    'True once PATCH /jobs/{id}/enrich (or equivalent) has applied deep-scrape data.';

CREATE INDEX IF NOT EXISTS idx_jobs_pending_deep_enrichment
    ON public.jobs (posted_at DESC)
    WHERE is_enriched = false
      AND source_url IS NOT NULL;

COMMIT;
