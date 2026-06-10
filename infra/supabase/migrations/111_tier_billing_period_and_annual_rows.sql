-- migration: 111_tier_billing_period_and_annual_rows

BEGIN;

-- Add billing_period_days. Default 30 for backwards compatibility.
ALTER TABLE public.tier_config
  ADD COLUMN billing_period_days INTEGER NOT NULL DEFAULT 30;

-- Drop the existing PK (assumed on `tier`) if any, replace with composite.
-- Verify the existing constraint name before running this in production:
ALTER TABLE public.tier_config DROP CONSTRAINT IF EXISTS tier_config_pkey;
ALTER TABLE public.tier_config
  ADD CONSTRAINT tier_config_pkey PRIMARY KEY (tier, billing_period_days);

-- Insert annual variants — ~30% off the monthly × 12 sticker.
-- starter: K125 × 12 = K1500/yr → K1050 (~30% off, rounds nicely)
-- professional: K250 × 12 = K3000/yr → K2100
-- super_standard: K500 × 12 = K6000/yr → K4200
INSERT INTO public.tier_config
  (tier, display_name, price_ngwee, matches_limit, sort_order,
   billing_period_days)
VALUES
  ('starter',        'Starter (Annual)',        105000, 50,    2, 365),
  ('professional',   'Professional (Annual)',   210000, 125,   3, 365),
  ('super_standard', 'Super Standard (Annual)', 420000, 99999, 4, 365)
ON CONFLICT (tier, billing_period_days) DO NOTHING;

COMMIT;
