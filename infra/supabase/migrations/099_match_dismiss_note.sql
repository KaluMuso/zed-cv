-- 099: Free-text note when user picks "other" on hide-match.

BEGIN;

ALTER TABLE public.matches
    ADD COLUMN IF NOT EXISTS dismiss_note VARCHAR(500);

COMMENT ON COLUMN public.matches.dismiss_note IS
    'Optional detail when dismiss_reason is other (max 500 chars).';

COMMIT;
