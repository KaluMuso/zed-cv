-- migration: 113_match_shares
--
-- Forwardable match cards: one shareable public preview per (sender, match).
-- Sender generates a short urlsafe token; recipients can view a blurred
-- preview at /m/<token> with a CTA to sign up via sender's referral_code.
--
-- Reuses the existing referral_events flow for attribution and rewards.

BEGIN;

CREATE TABLE IF NOT EXISTS public.match_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID NOT NULL REFERENCES public.matches(id) ON DELETE CASCADE,
    sender_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    view_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- A user can only have one share per match; reusing the same token
    -- across shares of the same match keeps the public URL stable.
    UNIQUE (match_id, sender_user_id)
);

CREATE INDEX IF NOT EXISTS idx_match_shares_token
  ON public.match_shares (token);
CREATE INDEX IF NOT EXISTS idx_match_shares_sender
  ON public.match_shares (sender_user_id);

-- RLS: sender sees and manages their own shares; service_role bypasses
-- for the public GET path. Public read by token is intentionally NOT
-- exposed via PostgREST — it goes through the backend so we can blur
-- fields and increment view counts atomically.
ALTER TABLE public.match_shares ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS match_shares_owner ON public.match_shares;
CREATE POLICY match_shares_owner ON public.match_shares
  FOR ALL
  TO authenticated
  USING (sender_user_id = auth.uid())
  WITH CHECK (sender_user_id = auth.uid());

-- Atomic view-count increment for the public preview path. Returns the
-- new view_count or NULL if the token does not exist.
CREATE OR REPLACE FUNCTION public.increment_match_share_views(p_token TEXT)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_catalog
AS $$
DECLARE
    v_new INTEGER;
BEGIN
    UPDATE public.match_shares
    SET view_count = view_count + 1
    WHERE token = p_token
    RETURNING view_count INTO v_new;
    RETURN v_new;
END;
$$;

GRANT EXECUTE ON FUNCTION public.increment_match_share_views(TEXT) TO authenticated, anon;

COMMIT;
