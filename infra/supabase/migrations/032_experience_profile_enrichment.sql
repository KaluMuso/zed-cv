-- 032_experience_profile_enrichment.sql
--
-- Track 4a-extend:
--   - Job LLM enrichment columns (experience, seniority, qualifications)
--   - User profile enrichment columns (seniority, qualifications, highest_qual)
--   - matches.experience_score for transparency
--   - match_jobs_for_user() soft experience-gap penalty (0.5..1.0 multiplier)
--
-- Idempotent: IF NOT EXISTS columns; DROP + CREATE RPC.
-- Apply ordering: 032 after 031.

BEGIN;

-- ── jobs: structured requirements from LLM enrichment ───────────────
ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS experience_min_years INTEGER,
    ADD COLUMN IF NOT EXISTS experience_max_years INTEGER,
    ADD COLUMN IF NOT EXISTS seniority_level TEXT,
    ADD COLUMN IF NOT EXISTS qualifications_required TEXT[];

COMMENT ON COLUMN public.jobs.experience_min_years IS
    'Minimum years of experience when stated in the posting. NULL = unknown.';
COMMENT ON COLUMN public.jobs.experience_max_years IS
    'Maximum years of experience when a range is stated. NULL = open-ended.';
COMMENT ON COLUMN public.jobs.seniority_level IS
    'intern | entry | mid | senior | lead | executive. Validated in app layer.';
COMMENT ON COLUMN public.jobs.qualifications_required IS
    'Degrees/certs required (verbatim strings from LLM enrichment).';

-- ── users: profile fields extracted from CV on parse ───────────────
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS seniority_level TEXT,
    ADD COLUMN IF NOT EXISTS highest_qualification TEXT,
    ADD COLUMN IF NOT EXISTS qualifications TEXT[];

COMMENT ON COLUMN public.users.seniority_level IS
    'Career band inferred from primary CV (intern..executive).';
COMMENT ON COLUMN public.users.highest_qualification IS
    'Highest degree/diploma/cert from CV enrichment.';
COMMENT ON COLUMN public.users.qualifications IS
    'All credentials listed on the CV (LLM extraction).';

-- ── matches: persist experience multiplier for UI transparency ─────
ALTER TABLE public.matches
    ADD COLUMN IF NOT EXISTS experience_score REAL;

COMMENT ON COLUMN public.matches.experience_score IS
    'Experience-gap multiplier (0.5..1.0) applied to final_score at match time.';

-- ── match_jobs_for_user: experience soft penalty ───────────────────
DROP FUNCTION IF EXISTS public.match_jobs_for_user(uuid, real, integer);

CREATE FUNCTION public.match_jobs_for_user(
    p_user_id    UUID,
    p_min_score  REAL    DEFAULT 50.0,
    p_limit      INTEGER DEFAULT 20
)
RETURNS TABLE (
    job_id            UUID,
    job_title         TEXT,
    job_company       TEXT,
    job_location      TEXT,
    vector_score      REAL,
    skill_score       REAL,
    bonus_score       REAL,
    experience_score  REAL,
    final_score       REAL,
    matched_skills    TEXT[],
    missing_skills    TEXT[]
) LANGUAGE plpgsql AS $$
DECLARE
    v_user_embedding VECTOR(768);
    v_user_skills    TEXT[];
    v_user_location  VARCHAR;
    v_user_years     INTEGER;
BEGIN
    SELECT c.embedding INTO v_user_embedding
    FROM cvs c
    WHERE c.user_id = p_user_id AND c.is_primary = true
    LIMIT 1;

    IF v_user_embedding IS NULL THEN
        RAISE EXCEPTION 'User has no primary CV with embedding';
    END IF;

    SELECT ARRAY_AGG(s.name) INTO v_user_skills
    FROM user_skills us
    JOIN skills s ON s.id = us.skill_id
    WHERE us.user_id = p_user_id;

    SELECT u.location, COALESCE(u.years_experience, 0)
      INTO v_user_location, v_user_years
      FROM users u WHERE u.id = p_user_id;

    RETURN QUERY
    WITH job_scores AS (
        SELECT
            j.id              AS j_id,
            j.title::TEXT     AS j_title,
            j.company::TEXT   AS j_company,
            j.location::TEXT  AS j_location,
            ((1 - (j.embedding <=> v_user_embedding)) * 100)::REAL AS v_score,
            (COALESCE(
                (SELECT COUNT(*)::REAL
                   FROM job_skills js2
                   JOIN skills s2 ON s2.id = js2.skill_id
                  WHERE js2.job_id = j.id AND s2.name = ANY(v_user_skills))
                / NULLIF((SELECT COUNT(*)::REAL FROM job_skills js3 WHERE js3.job_id = j.id), 0)
                * 100,
                0
            ))::REAL AS s_score,
            (CASE WHEN j.location = v_user_location THEN 30 ELSE 0 END +
             CASE WHEN j.quality_score > 70 THEN 20 ELSE 0 END +
             CASE WHEN j.closing_date > CURRENT_DATE THEN 20 ELSE 0 END +
             CASE WHEN j.posted_at > NOW() - INTERVAL '7 days' THEN 30 ELSE 0 END
            )::REAL AS b_score,
            (CASE
                WHEN j.experience_min_years IS NULL THEN 1.0::REAL
                WHEN v_user_years >= j.experience_min_years THEN 1.0::REAL
                ELSE GREATEST(
                    0.5::REAL,
                    (1.0 - 0.075 * (j.experience_min_years - v_user_years))::REAL
                )
             END) AS exp_score,
            ARRAY(SELECT s2.name
                    FROM job_skills js2
                    JOIN skills s2 ON s2.id = js2.skill_id
                   WHERE js2.job_id = j.id AND s2.name = ANY(v_user_skills))::TEXT[] AS m_skills,
            ARRAY(SELECT s2.name
                    FROM job_skills js2
                    JOIN skills s2 ON s2.id = js2.skill_id
                   WHERE js2.job_id = j.id AND NOT (s2.name = ANY(v_user_skills)))::TEXT[] AS miss_skills
        FROM jobs j
        WHERE j.is_active = true
          AND j.embedding IS NOT NULL
          AND (j.closing_date IS NULL OR j.closing_date >= CURRENT_DATE)
    )
    SELECT
        js.j_id,
        js.j_title,
        js.j_company,
        js.j_location,
        js.v_score,
        js.s_score,
        js.b_score,
        js.exp_score,
        (js.v_score * 0.6 + js.s_score * 0.3 + js.b_score * 0.1) * js.exp_score,
        js.m_skills,
        js.miss_skills
    FROM job_scores js
    WHERE (js.v_score * 0.6 + js.s_score * 0.3 + js.b_score * 0.1) * js.exp_score >= p_min_score
    ORDER BY (js.v_score * 0.6 + js.s_score * 0.3 + js.b_score * 0.1) * js.exp_score DESC
    LIMIT p_limit;
END;
$$;

COMMIT;
