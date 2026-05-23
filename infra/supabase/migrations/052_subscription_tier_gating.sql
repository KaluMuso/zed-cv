-- 052_subscription_tier_gating.sql
--
-- Monthly match-view counters on users + Zambian tier keys (mwana/mwizi/wino).
-- Product limits: Mwana 5/mo, Mwizi 25/mo, Wino unlimited. Cover letters: Wino only.
--
-- Apply ordering: 052 after 047–051 migrations.

BEGIN;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS matches_viewed_this_month INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS billing_cycle_reset DATE;

COMMENT ON COLUMN public.users.matches_viewed_this_month IS
    'API-enforced monthly match list views; reset when billing_cycle_reset is reached.';
COMMENT ON COLUMN public.users.billing_cycle_reset IS
    'Calendar date (UTC) when matches_viewed_this_month resets to 0.';

-- Seed billing_cycle_reset for existing rows (first day of next calendar month).
UPDATE public.users
SET billing_cycle_reset = (
    date_trunc('month', (NOW() AT TIME ZONE 'UTC')::date)::date + INTERVAL '1 month'
)::date
WHERE billing_cycle_reset IS NULL;

-- Map legacy tier keys to mwana / mwizi / wino.
UPDATE public.users
SET subscription_tier = CASE subscription_tier
    WHEN 'free' THEN 'mwana'
    WHEN 'starter' THEN 'mwizi'
    WHEN 'professional' THEN 'wino'
    WHEN 'super_standard' THEN 'wino'
    WHEN 'mwezi' THEN 'mwizi'
    WHEN 'bwino' THEN 'wino'
    ELSE subscription_tier
END
WHERE subscription_tier IN (
    'free', 'starter', 'professional', 'super_standard', 'mwezi', 'bwino'
);

UPDATE public.subscriptions
SET tier = CASE tier
    WHEN 'free' THEN 'mwana'
    WHEN 'starter' THEN 'mwizi'
    WHEN 'professional' THEN 'wino'
    WHEN 'super_standard' THEN 'wino'
    WHEN 'mwezi' THEN 'mwizi'
    WHEN 'bwino' THEN 'wino'
    ELSE tier
END
WHERE tier IN (
    'free', 'starter', 'professional', 'super_standard', 'mwezi', 'bwino'
);

ALTER TABLE public.users
    DROP CONSTRAINT IF EXISTS users_subscription_tier_check;
ALTER TABLE public.users
    ADD CONSTRAINT users_subscription_tier_check
    CHECK (subscription_tier IN ('mwana', 'mwizi', 'wino'));

ALTER TABLE public.users
    ALTER COLUMN subscription_tier SET DEFAULT 'mwana';

ALTER TABLE public.subscriptions
    DROP CONSTRAINT IF EXISTS subscriptions_tier_check;
ALTER TABLE public.subscriptions
    ADD CONSTRAINT subscriptions_tier_check
    CHECK (tier IN ('mwana', 'mwizi', 'wino'));

-- tier_config: replace legacy rows with canonical tiers + quotas.
DELETE FROM public.tier_config
WHERE tier IN ('free', 'starter', 'professional', 'super_standard');

ALTER TABLE public.tier_config
    DROP CONSTRAINT IF EXISTS tier_config_tier_check;
ALTER TABLE public.tier_config
    ADD CONSTRAINT tier_config_tier_check
    CHECK (tier IN ('mwana', 'mwizi', 'wino'));

INSERT INTO public.tier_config (tier, display_name, price_ngwee, matches_limit, sort_order)
VALUES
    ('mwana', 'Mwana', 0, 5, 0),
    ('mwizi', 'Mwizi', 7900, 25, 1),
    ('wino', 'Wino', 19900, 99999, 2)
ON CONFLICT (tier) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    price_ngwee = EXCLUDED.price_ngwee,
    matches_limit = EXCLUDED.matches_limit,
    sort_order = EXCLUDED.sort_order,
    updated_at = NOW();

-- Paid-tier downgrade cron uses mwana instead of free.
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
          AND u.subscription_tier <> 'mwana'
    ),
    subs AS (
        UPDATE public.subscriptions s
        SET
            tier = 'mwana',
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
        subscription_tier = 'mwana',
        subscription_expires_at = NULL,
        subscription_renews_at = NULL,
        updated_at = NOW()
    FROM expired e
    WHERE u.id = e.user_id;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;

COMMIT;
