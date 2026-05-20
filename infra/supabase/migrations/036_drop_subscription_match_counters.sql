-- 036_drop_subscription_match_counters.sql
--
-- Match quota is derived from matches.credited_at within the active billing
-- period (see app/services/matching.py). Legacy subscriptions.matches_used
-- and matches_limit columns drift when not written — drop them.
--
-- Apply ordering: 036 after 035_activate_subscription_rpc.

BEGIN;

-- Remove matches_limit write from downgrade cron (redefined without counters).
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

ALTER TABLE public.subscriptions
    DROP COLUMN IF EXISTS matches_used,
    DROP COLUMN IF EXISTS matches_limit;

COMMIT;
