-- 091 — Scope cv_generations RLS to row owner (Supabase advisor: cv_gen_all was
-- USING (true) WITH CHECK (true) for ALL). SELECT own rows only; INSERTs from
-- backend service_role (no authenticated INSERT).

ALTER TABLE public.cv_generations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cv_gen_all ON public.cv_generations;
DROP POLICY IF EXISTS cv_generations_self ON public.cv_generations;

CREATE POLICY cv_gen_select_own ON public.cv_generations
  FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

-- INSERTs come from backend service role; deny authenticated INSERT explicitly.
CREATE POLICY cv_gen_insert_deny ON public.cv_generations
  FOR INSERT
  TO authenticated
  WITH CHECK (false);
