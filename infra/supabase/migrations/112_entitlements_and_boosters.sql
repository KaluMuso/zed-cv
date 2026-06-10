-- migration: 112_entitlements_and_boosters

BEGIN;

-- Catalog of one-off SKUs (pay-per-use). Hardcoded in seed for now.
CREATE TABLE IF NOT EXISTS public.booster_sku (
    sku TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL,
    price_ngwee INTEGER NOT NULL CHECK (price_ngwee > 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order SMALLINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO public.booster_sku
  (sku, display_name, description, price_ngwee, sort_order)
VALUES
  ('tailored_cv',  'Tailored CV',  'AI-tailor your CV for this exact job in 60 seconds.', 2000, 1),
  ('cover_letter', 'Cover Letter', 'AI-write a cover letter targeted at this role.',       1500, 2),
  ('interview_prep','Interview Prep','Get 10 likely interview questions + model answers for this role.', 4000, 3)
ON CONFLICT (sku) DO NOTHING;

-- User entitlement ledger — each row is one consumed-or-pending use of a
-- booster. Tied to a specific job (the moment the user is applying to).
CREATE TABLE IF NOT EXISTS public.user_entitlements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    sku TEXT NOT NULL REFERENCES public.booster_sku(sku),
    job_id UUID REFERENCES public.jobs(id) ON DELETE SET NULL,
    payment_id UUID REFERENCES public.payments(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','paid','consumed','refunded','failed')),
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_entitlements_user_status
  ON public.user_entitlements (user_id, status);
CREATE INDEX IF NOT EXISTS idx_user_entitlements_job
  ON public.user_entitlements (job_id) WHERE job_id IS NOT NULL;

-- RLS: a user sees only their own entitlements; service_role bypasses.
ALTER TABLE public.user_entitlements ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS user_entitlements_owner ON public.user_entitlements;
CREATE POLICY user_entitlements_owner ON public.user_entitlements
  FOR ALL TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

ALTER TABLE public.booster_sku ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS booster_sku_read ON public.booster_sku;
CREATE POLICY booster_sku_read ON public.booster_sku
  FOR SELECT TO authenticated
  USING (is_active = true);

COMMIT;
