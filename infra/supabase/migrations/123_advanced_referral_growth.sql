-- migration: 113_advanced_referral_growth

BEGIN;

-- Configuration for referral reward thresholds and values
CREATE TABLE IF NOT EXISTS public.referral_config (
    reward_type TEXT PRIMARY KEY CHECK (reward_type IN ('matches', 'cash', 'tier_promo')),
    required_count INTEGER NOT NULL,
    reward_value INTEGER NOT NULL, -- e.g. 2 for 2 matches, 5000 for K50 cash
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Default configuration proposed by user
INSERT INTO public.referral_config (reward_type, required_count, reward_value) VALUES
    ('matches', 10, 2),        -- 2 extra matches for 10 registrations
    ('cash', 5, 5000),         -- K50 (5000 ngwee) for 5 paid users
    ('tier_promo', 20, 1)      -- 1 month starter promo for 20 registrations
ON CONFLICT (reward_type) DO NOTHING;

-- Ledger for rewards earned by users
CREATE TABLE IF NOT EXISTS public.referral_rewards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    reward_type TEXT NOT NULL REFERENCES public.referral_config(reward_type),
    reward_value INTEGER NOT NULL,
    milestone_count INTEGER NOT NULL, -- The threshold they hit (e.g., 10th user)
    status TEXT NOT NULL DEFAULT 'pending_payout' 
        CHECK (status IN ('pending_payout', 'credited', 'rejected')),
    earned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, reward_type, milestone_count)
);

-- RLS so users can see their own rewards
ALTER TABLE public.referral_rewards ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS referral_rewards_owner ON public.referral_rewards;
CREATE POLICY referral_rewards_owner ON public.referral_rewards
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

-- Add a column to users to track first payment date for efficient querying
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS first_payment_at TIMESTAMPTZ;

COMMIT;
