-- 053_restore_canonical_tier_model.sql
-- Revert mwana/mwizi/wino to free/starter/professional/super_standard.
-- Restore K125/K250/K500 pricing and match quotas from tier_config.

BEGIN;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS promotion_applied_until TIMESTAMPTZ;

COMMENT ON COLUMN public.users.promotion_applied_until IS
    'First-two-months 50% checkout discount ends at this instant (UTC).';

UPDATE public.users
SET promotion_applied_until = created_at + INTERVAL '2 months'
WHERE promotion_applied_until IS NULL;

-- Drop every tier CHECK on tier_config (inline 037 checks may not be named tier_config_tier_check).
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

ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_subscription_tier_check;
ALTER TABLE public.subscriptions DROP CONSTRAINT IF EXISTS subscriptions_tier_check;

-- Rebuild tier_config (avoid UPDATE on tier PK while old checks may still exist).
DELETE FROM public.tier_config;

INSERT INTO public.tier_config (tier, display_name, price_ngwee, matches_limit, sort_order)
VALUES
    ('free', 'Free', 0, 10, 1),
    ('starter', 'Starter', 12500, 50, 2),
    ('professional', 'Professional', 25000, 125, 3),
    ('super_standard', 'Super Standard', 50000, 99999, 4);

-- Reverse-migrate users and subscriptions that were auto-flipped in 052.
UPDATE public.users SET subscription_tier = 'free' WHERE subscription_tier = 'mwana';
UPDATE public.users SET subscription_tier = 'starter' WHERE subscription_tier = 'mwizi';
UPDATE public.users SET subscription_tier = 'professional' WHERE subscription_tier = 'wino';

UPDATE public.subscriptions SET tier = 'free' WHERE tier = 'mwana';
UPDATE public.subscriptions SET tier = 'starter' WHERE tier = 'mwizi';
UPDATE public.subscriptions SET tier = 'professional' WHERE tier = 'wino';

ALTER TABLE public.users
    ALTER COLUMN subscription_tier SET DEFAULT 'free';

ALTER TABLE public.tier_config ADD CONSTRAINT tier_config_tier_check
    CHECK (tier IN ('free', 'starter', 'professional', 'super_standard'));

ALTER TABLE public.users ADD CONSTRAINT users_subscription_tier_check
    CHECK (subscription_tier IN ('free', 'starter', 'professional', 'super_standard'));

ALTER TABLE public.subscriptions ADD CONSTRAINT subscriptions_tier_check
    CHECK (tier IN ('free', 'starter', 'professional', 'super_standard'));

-- Paid-tier downgrade cron: revert to free tier key.
CREATE OR REPLACE FUNCTION public.downgrade_expired_subscriptions()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    WITH expired AS (
        SELECT u.id AS user_id
        FROM public.users u
        WHERE u.subscription_expires_at IS NOT NULL
          AND u.subscription_expires_at < NOW()
          AND u.subscription_tier <> 'free'
    ),
    subs AS (
        UPDATE public.subscriptions s
        SET
            tier = 'free',
            status = 'cancelled',
            cancelled_at = NOW(),
            current_period_end = NOW(),
            updated_at = NOW()
        FROM expired e
        WHERE s.user_id = e.user_id
          AND s.status = 'active'
        RETURNING s.user_id
    )
    UPDATE public.users u
    SET
        subscription_tier = 'free',
        subscription_expires_at = NULL,
        subscription_renews_at = NULL,
        updated_at = NOW()
    FROM expired e
    WHERE u.id = e.user_id;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;

CREATE OR REPLACE FUNCTION public.users_set_promotion_applied_until()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.promotion_applied_until IS NULL THEN
        NEW.promotion_applied_until := COALESCE(NEW.created_at, NOW()) + INTERVAL '2 months';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS users_promotion_before_insert ON public.users;
CREATE TRIGGER users_promotion_before_insert
    BEFORE INSERT ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.users_set_promotion_applied_until();

COMMIT;
