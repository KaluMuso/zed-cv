-- 061: Nightly batch match runs — batch_run_id on matches + run audit table

ALTER TABLE public.matches
    ADD COLUMN IF NOT EXISTS batch_run_id UUID,
    ADD COLUMN IF NOT EXISTS batch_run_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_matches_user_batch
    ON public.matches (user_id, batch_run_at DESC);

CREATE TABLE IF NOT EXISTS public.match_batch_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    users_processed INTEGER,
    matches_created INTEGER,
    error_count INTEGER,
    notes TEXT
);

COMMENT ON TABLE public.match_batch_runs IS
    'Audit log for nightly POST /admin/batch-match runs (n8n 02:00 CAT).';

COMMENT ON COLUMN public.matches.batch_run_id IS
    'Links rows to a match_batch_runs.id from nightly or onboarding batch.';

COMMENT ON COLUMN public.matches.batch_run_at IS
    'When this row was written for batch_run_id (used for refresh + 7d prune).';
