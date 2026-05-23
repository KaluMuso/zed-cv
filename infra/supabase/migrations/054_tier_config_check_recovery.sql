-- 054_tier_config_check_recovery.sql
-- Recovery when 053 fails: tier_config may still have a CHECK that only allows
-- mwana/mwizi/wino (052) while 053 tries to write free/starter/...
-- Drops every CHECK on tier_config, rebuilds rows, re-adds canonical constraint.

BEGIN;

-- Drop all CHECK constraints on tier_config (name may differ from tier_config_tier_check).
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT c.conname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname = 'tier_config'
          AND c.contype = 'c'
    LOOP
        EXECUTE format(
            'ALTER TABLE public.tier_config DROP CONSTRAINT %I',
            r.conname
        );
    END LOOP;
END $$;

DELETE FROM public.tier_config;

INSERT INTO public.tier_config (tier, display_name, price_ngwee, matches_limit, sort_order)
VALUES
    ('free', 'Free', 0, 10, 1),
    ('starter', 'Starter', 12500, 50, 2),
    ('professional', 'Professional', 25000, 125, 3),
    ('super_standard', 'Super Standard', 50000, 99999, 4);

ALTER TABLE public.tier_config
    ADD CONSTRAINT tier_config_tier_check
    CHECK (tier IN ('free', 'starter', 'professional', 'super_standard'));

COMMIT;
