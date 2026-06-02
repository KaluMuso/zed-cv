-- 097: Optional not-interested reason when a user hides a match.

BEGIN;

ALTER TABLE public.matches
    ADD COLUMN IF NOT EXISTS dismiss_reason VARCHAR(40),
    ADD COLUMN IF NOT EXISTS dismissed_at TIMESTAMPTZ;

COMMENT ON COLUMN public.matches.dismiss_reason IS
    'Why the user hid this match: not_relevant, wrong_location, salary_too_low, experience_mismatch, already_applied, other.';

COMMENT ON COLUMN public.matches.dismissed_at IS
    'When status was set to dismissed (UTC).';

CREATE INDEX IF NOT EXISTS idx_matches_dismiss_reason
    ON public.matches (dismiss_reason)
    WHERE dismiss_reason IS NOT NULL;

COMMIT;
