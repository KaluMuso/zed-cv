-- 055_free_tier_promo.sql
-- Free tier baseline 10 → 3; welcome 7 matches/mo for first 2 months on free tier.

BEGIN;

UPDATE public.tier_config SET matches_limit = 3 WHERE tier = 'free';

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS welcome_match_bonus INTEGER DEFAULT 7,
    ADD COLUMN IF NOT EXISTS welcome_match_bonus_until TIMESTAMPTZ;

COMMENT ON COLUMN public.users.welcome_match_bonus IS
    'Monthly match quota override for free tier during welcome window (default 7).';

COMMENT ON COLUMN public.users.welcome_match_bonus_until IS
    'Welcome match bonus ends at this instant (UTC); then tier_config free limit applies.';

UPDATE public.users
SET welcome_match_bonus_until = NOW() + INTERVAL '2 months'
WHERE subscription_tier = 'free' AND welcome_match_bonus_until IS NULL;

CREATE OR REPLACE FUNCTION public.set_welcome_bonus()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.welcome_match_bonus IS NULL THEN
        NEW.welcome_match_bonus := 7;
    END IF;
    IF NEW.welcome_match_bonus_until IS NULL THEN
        NEW.welcome_match_bonus_until := COALESCE(NEW.created_at, NOW()) + INTERVAL '2 months';
    END IF;
    IF NEW.promotion_applied_until IS NULL THEN
        NEW.promotion_applied_until := COALESCE(NEW.created_at, NOW()) + INTERVAL '2 months';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS users_promotion_before_insert ON public.users;
DROP TRIGGER IF EXISTS trg_set_welcome_bonus ON public.users;

CREATE TRIGGER trg_set_welcome_bonus
    BEFORE INSERT ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.set_welcome_bonus();

COMMIT;
