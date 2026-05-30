-- 084: Align prod columns referenced by backend but missing on live DB
-- (caught when ci_schema_guard runs in live mode with schema_guard_columns RPC).

BEGIN;

ALTER TABLE public.cv_generations
    ADD COLUMN IF NOT EXISTS cv_id UUID REFERENCES public.cvs(id) ON DELETE SET NULL;

COMMENT ON COLUMN public.cv_generations.cv_id IS
    'Source CV row for /cv/generate history (nullable for legacy rows).';

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS whatsapp_alerts BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS language VARCHAR(5) NOT NULL DEFAULT 'en';

ALTER TABLE public.users
    DROP CONSTRAINT IF EXISTS users_language_check;

ALTER TABLE public.users
    ADD CONSTRAINT users_language_check CHECK (language IN ('en', 'bem'));

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS referral_match_bonus INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN public.users.referral_match_bonus IS
    'Extra monthly match quota from referral rewards (added to tier limit).';

COMMIT;
