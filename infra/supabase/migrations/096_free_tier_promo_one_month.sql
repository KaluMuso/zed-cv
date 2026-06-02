-- Shorten free-tier welcome window and paid promo from 2 months to 1 month.
-- Does not shorten users who already have a later welcome_match_bonus_until.

BEGIN;

CREATE OR REPLACE FUNCTION public.set_welcome_bonus()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.welcome_match_bonus IS NULL THEN
        NEW.welcome_match_bonus := 7;
    END IF;
    IF NEW.welcome_match_bonus_until IS NULL THEN
        NEW.welcome_match_bonus_until := COALESCE(NEW.created_at, NOW()) + INTERVAL '1 month';
    END IF;
    IF NEW.promotion_applied_until IS NULL THEN
        NEW.promotion_applied_until := COALESCE(NEW.created_at, NOW()) + INTERVAL '1 month';
    END IF;
    RETURN NEW;
END;
$$;

COMMIT;
