-- 060 — Bwana Interview: mock sessions, aptitude bank, aptitude scores

BEGIN;

CREATE TABLE IF NOT EXISTS public.interview_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role_label text NOT NULL,
    questions jsonb NOT NULL DEFAULT '[]'::jsonb,
    overall_score numeric,
    strengths text[],
    improvements text[],
    practice_areas text[],
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_created
    ON public.interview_sessions (user_id, created_at DESC);

ALTER TABLE public.interview_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS interview_sessions_select_own ON public.interview_sessions;
CREATE POLICY interview_sessions_select_own ON public.interview_sessions
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS interview_sessions_insert_own ON public.interview_sessions;
CREATE POLICY interview_sessions_insert_own ON public.interview_sessions
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS interview_sessions_update_own ON public.interview_sessions;
CREATE POLICY interview_sessions_update_own ON public.interview_sessions
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Question bank: backend service_role reads; no authenticated policies.
CREATE TABLE IF NOT EXISTS public.aptitude_question_bank (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pack text NOT NULL CHECK (pack IN ('numerical', 'verbal', 'abstract')),
    question_text text NOT NULL,
    options jsonb NOT NULL,
    correct_value text NOT NULL,
    difficulty text NOT NULL DEFAULT 'medium',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_aptitude_question_bank_pack
    ON public.aptitude_question_bank (pack);

CREATE TABLE IF NOT EXISTS public.aptitude_scores (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    pack text NOT NULL CHECK (pack IN ('numerical', 'verbal', 'abstract')),
    score numeric NOT NULL,
    percentile numeric,
    elapsed_seconds integer,
    completed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_aptitude_scores_user_completed
    ON public.aptitude_scores (user_id, completed_at DESC);

ALTER TABLE public.aptitude_scores ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS aptitude_scores_select_own ON public.aptitude_scores;
CREATE POLICY aptitude_scores_select_own ON public.aptitude_scores
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS aptitude_scores_insert_own ON public.aptitude_scores;
CREATE POLICY aptitude_scores_insert_own ON public.aptitude_scores
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

COMMIT;
