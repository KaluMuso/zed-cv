-- 041: Track 4e — review queue flags and structured description column

BEGIN;

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS is_review_required boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS review_reason text NULL,
    ADD COLUMN IF NOT EXISTS description_markdown text NULL;

CREATE INDEX IF NOT EXISTS idx_jobs_review_required
    ON public.jobs (is_review_required, created_at DESC)
    WHERE is_review_required = true;

COMMENT ON COLUMN public.jobs.is_review_required IS
    'True when job needs admin review (missing apply path and/or deadline) before public listing.';
COMMENT ON COLUMN public.jobs.review_reason IS
    'Comma-separated: no_apply_path, no_deadline, both';
COMMENT ON COLUMN public.jobs.description_markdown IS
    'Markdown-normalized description for UI rendering; description remains raw fallback.';

COMMIT;
