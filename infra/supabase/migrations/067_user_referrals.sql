-- 067: Referral codes, referred-by attribution, and signup event log.

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS referral_code VARCHAR(12),
  ADD COLUMN IF NOT EXISTS referred_by_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL;

COMMENT ON COLUMN public.users.referral_code IS
  'Stable invite code shown on profile; unique per user.';
COMMENT ON COLUMN public.users.referred_by_user_id IS
  'Set once at signup when the invite ref resolves to another user.';

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code
  ON public.users (referral_code)
  WHERE referral_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_referred_by
  ON public.users (referred_by_user_id)
  WHERE referred_by_user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.referral_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  referred_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  status VARCHAR(20) NOT NULL DEFAULT 'signed_up'
    CHECK (status IN ('signed_up', 'qualified', 'rewarded')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  qualified_at TIMESTAMPTZ,
  CONSTRAINT referral_events_referred_user_unique UNIQUE (referred_user_id)
);

CREATE INDEX IF NOT EXISTS idx_referral_events_referrer
  ON public.referral_events (referrer_user_id, created_at DESC);

COMMENT ON TABLE public.referral_events IS
  'Audit log when a new user signs up via an invite link.';

-- Backfill referral_code for existing users (collision-safe loop).
DO $$
DECLARE
  r RECORD;
  code TEXT;
  tries INT;
BEGIN
  FOR r IN SELECT id FROM public.users WHERE referral_code IS NULL LOOP
    tries := 0;
    LOOP
      code := UPPER(SUBSTRING(MD5(r.id::text || ':' || tries::text) FROM 1 FOR 8));
      EXIT WHEN NOT EXISTS (
        SELECT 1 FROM public.users u WHERE u.referral_code = code
      );
      tries := tries + 1;
      IF tries > 20 THEN
        RAISE EXCEPTION 'Could not assign referral_code for user %', r.id;
      END IF;
    END LOOP;
    UPDATE public.users SET referral_code = code WHERE id = r.id;
  END LOOP;
END $$;

ALTER TABLE public.users
  ALTER COLUMN referral_code SET NOT NULL;
