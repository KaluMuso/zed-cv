-- 035_activate_subscription_rpc.sql
--
-- Postgres RPC for paid subscription activation after DPO/Lenco webhooks.
-- Python app/services/subscription_billing.py delegates here so prod DB
-- has a single source of truth (pg_proc) even if 033 columns were applied
-- without this function.
--
-- Apply ordering: 035 after 034_experience_penalty_0_1.

BEGIN;

CREATE OR REPLACE FUNCTION public.activate_subscription_after_payment(
    p_user_id UUID,
    p_payment_id UUID,
    p_new_tier TEXT,
    p_subscription_id UUID DEFAULT NULL,
    p_lenco_subscription_ref TEXT DEFAULT NULL,
    p_period_days INTEGER DEFAULT 30,
    p_existing_period_end TIMESTAMPTZ DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_now TIMESTAMPTZ := NOW();
    v_base TIMESTAMPTZ;
    v_period_start TIMESTAMPTZ;
    v_period_end TIMESTAMPTZ;
    v_sub_id UUID;
    v_started_at TIMESTAMPTZ;
BEGIN
    v_period_start := v_now;

    IF p_existing_period_end IS NOT NULL AND p_existing_period_end > v_now THEN
        v_base := p_existing_period_end;
    ELSE
        v_base := v_now;
    END IF;

    v_period_end := v_base + make_interval(days => p_period_days);

    v_sub_id := p_subscription_id;

    IF v_sub_id IS NOT NULL THEN
        SELECT started_at INTO v_started_at
        FROM subscriptions
        WHERE id = v_sub_id;

        UPDATE subscriptions
        SET
            tier = p_new_tier,
            status = 'active',
            current_period_start = v_period_start,
            current_period_end = v_period_end,
            cancelled_at = NULL,
            started_at = COALESCE(started_at, v_period_start),
            lenco_subscription_ref = COALESCE(p_lenco_subscription_ref, lenco_subscription_ref),
            updated_at = v_now
        WHERE id = v_sub_id;
    ELSE
        INSERT INTO subscriptions (
            user_id,
            tier,
            status,
            started_at,
            current_period_start,
            current_period_end,
            lenco_subscription_ref
        )
        VALUES (
            p_user_id,
            p_new_tier,
            'active',
            v_period_start,
            v_period_start,
            v_period_end,
            p_lenco_subscription_ref
        )
        RETURNING id INTO v_sub_id;
    END IF;

    UPDATE users
    SET
        subscription_tier = p_new_tier,
        subscription_expires_at = v_period_end,
        subscription_renews_at = v_period_end,
        subscription_started_at = COALESCE(subscription_started_at, v_period_start),
        updated_at = v_now
    WHERE id = p_user_id;

    UPDATE payments
    SET subscription_id = v_sub_id
    WHERE id = p_payment_id;

    RETURN jsonb_build_object(
        'subscription_id', v_sub_id,
        'period_start', v_period_start,
        'period_end', v_period_end
    );
END;
$$;

COMMENT ON FUNCTION public.activate_subscription_after_payment(
    UUID, UUID, TEXT, UUID, TEXT, INTEGER, TIMESTAMPTZ
) IS
    'Activate or renew a paid subscription after successful payment webhook.';

GRANT EXECUTE ON FUNCTION public.activate_subscription_after_payment(
    UUID, UUID, TEXT, UUID, TEXT, INTEGER, TIMESTAMPTZ
) TO service_role;

COMMIT;
