-- 060: Weighted v2 hybrid matching (50/20/15/10/5) + 35 hard floor
--
-- Components (additive, max 100):
--   Semantic:   (1 - cosine_distance) * 50
--   Skills:     required-skill overlap * 20
--   Experience: compute_experience_score(years, min, max) * 15
--   Location:   exact location or remote/hybrid * 10
--   Recency:    linear decay over 30 days * 5
--
-- Rows with final_score < 35 are never returned or stored by callers
-- that respect the RPC. p_min_score defaults to 50 (user-facing);
-- pass 35 for admin analytics.

BEGIN;

ALTER TABLE public.matches
    ADD COLUMN IF NOT EXISTS location_score REAL,
    ADD COLUMN IF NOT EXISTS recency_score REAL;

DROP FUNCTION IF EXISTS public.compute_experience_score(integer, integer);

CREATE OR REPLACE FUNCTION public.compute_experience_score(
    p_user_years INTEGER,
    p_job_min_years INTEGER,
    p_job_max_years INTEGER DEFAULT NULL
)
RETURNS REAL
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE
        WHEN p_job_min_years IS NULL AND p_job_max_years IS NULL THEN 1.0::REAL
        WHEN p_job_max_years IS NOT NULL
             AND COALESCE(p_user_years, 0) > p_job_max_years THEN
            GREATEST(
                0.5::REAL,
                (1.0 - 0.1 * (COALESCE(p_user_years, 0) - p_job_max_years))::REAL
            )
        WHEN p_job_min_years IS NOT NULL
             AND COALESCE(p_user_years, 0) < p_job_min_years THEN
            GREATEST(
                0.5::REAL,
                (1.0 - 0.1 * (p_job_min_years - COALESCE(p_user_years, 0)))::REAL
            )
        ELSE 1.0::REAL
    END;
$$;

COMMENT ON FUNCTION public.compute_experience_score(INTEGER, INTEGER, INTEGER) IS
    'Experience-fit multiplier in [0.5, 1.0] for v2 match scoring (min/max years).';

DROP FUNCTION IF EXISTS public.match_jobs_for_user(uuid, real, integer);

CREATE FUNCTION public.match_jobs_for_user(
    p_user_id    UUID,
    p_min_score  REAL    DEFAULT 50.0,
    p_limit      INTEGER DEFAULT 50
)
RETURNS TABLE (
    job_id            UUID,
    score             REAL,
    semantic_score    REAL,
    skills_score      REAL,
    experience_score  REAL,
    location_score    REAL,
    recency_score     REAL,
    matched_skills    TEXT[],
    missing_skills    TEXT[],
    explanation       TEXT,
    -- Legacy aliases for callers not yet migrated off 046 column names
    vector_score      REAL,
    skill_score       REAL,
    bonus_score       REAL,
    final_score       REAL
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_user_embedding VECTOR(768);
    v_user_skills    TEXT[];
    v_user_location  TEXT;
    v_user_years     INTEGER;
BEGIN
    SELECT c.embedding INTO v_user_embedding
    FROM cvs c
    WHERE c.user_id = p_user_id AND c.is_primary = true
    LIMIT 1;

    IF v_user_embedding IS NULL THEN
        RAISE EXCEPTION 'User has no primary CV with embedding';
    END IF;

    SELECT COALESCE(ARRAY_AGG(s.name), ARRAY[]::TEXT[]) INTO v_user_skills
    FROM user_skills us
    JOIN skills s ON s.id = us.skill_id
    WHERE us.user_id = p_user_id;

    SELECT u.location::TEXT, COALESCE(u.years_experience, 0)
      INTO v_user_location, v_user_years
      FROM users u WHERE u.id = p_user_id;

    RETURN QUERY
    WITH job_scores AS (
        SELECT
            j.id AS j_id,
            (GREATEST(
                0::REAL,
                (1 - (j.embedding <=> v_user_embedding)) * 50
            ))::REAL AS sem_score,
            (COALESCE(
                (SELECT COUNT(*)::REAL
                   FROM job_skills js_req
                   JOIN skills s_req ON s_req.id = js_req.skill_id
                  WHERE js_req.job_id = j.id
                    AND js_req.is_required = true
                    AND s_req.name = ANY(v_user_skills))
                / NULLIF(
                    (SELECT COUNT(*)::REAL
                       FROM job_skills js_tot
                      WHERE js_tot.job_id = j.id
                        AND js_tot.is_required = true),
                    0
                )
                * 20,
                0
            ))::REAL AS sk_score,
            (
                public.compute_experience_score(
                    v_user_years,
                    j.experience_min_years,
                    j.experience_max_years
                ) * 15
            )::REAL AS exp_score,
            (
                CASE
                    WHEN v_user_location IS NOT NULL
                         AND j.location IS NOT NULL
                         AND LOWER(TRIM(v_user_location)) = LOWER(TRIM(j.location))
                    THEN 10
                    WHEN LOWER(TRIM(COALESCE(j.work_arrangement, ''))) IN ('remote', 'hybrid')
                    THEN 10
                    ELSE 0
                END
            )::REAL AS loc_score,
            (
                GREATEST(
                    0::REAL,
                    (1.0 - LEAST(
                        EXTRACT(EPOCH FROM (NOW() - COALESCE(j.posted_at, j.created_at)))
                        / 86400.0 / 30.0,
                        1.0
                    )) * 5
                )
            )::REAL AS rec_score,
            ARRAY(
                SELECT s2.name::TEXT
                  FROM job_skills js2
                  JOIN skills s2 ON s2.id = js2.skill_id
                 WHERE js2.job_id = j.id
                   AND js2.is_required = true
                   AND s2.name = ANY(v_user_skills)
            )::TEXT[] AS m_skills,
            ARRAY(
                SELECT s2.name::TEXT
                  FROM job_skills js2
                  JOIN skills s2 ON s2.id = js2.skill_id
                 WHERE js2.job_id = j.id
                   AND js2.is_required = true
                   AND NOT (s2.name = ANY(v_user_skills))
            )::TEXT[] AS miss_skills
        FROM jobs j
        WHERE j.is_active = true
          AND COALESCE(j.is_review_required, false) = false
          AND j.embedding IS NOT NULL
          AND (j.closing_date IS NULL OR j.closing_date >= CURRENT_DATE)
    ),
    ranked AS (
        SELECT
            js.j_id,
            js.sem_score,
            js.sk_score,
            js.exp_score,
            js.loc_score,
            js.rec_score,
            (js.sem_score + js.sk_score + js.exp_score + js.loc_score + js.rec_score)::REAL AS f_score,
            js.m_skills,
            js.miss_skills
        FROM job_scores js
        WHERE (js.sem_score + js.sk_score + js.exp_score + js.loc_score + js.rec_score) >= 35
    )
    SELECT
        r.j_id,
        r.f_score,
        r.sem_score,
        r.sk_score,
        r.exp_score,
        r.loc_score,
        r.rec_score,
        r.m_skills,
        r.miss_skills,
        format(
            'Semantic %s/50, skills %s/20, experience %s/15, location %s/10, recency %s/5.',
            ROUND(r.sem_score::numeric, 1),
            ROUND(r.sk_score::numeric, 1),
            ROUND(r.exp_score::numeric, 1),
            ROUND(r.loc_score::numeric, 1),
            ROUND(r.rec_score::numeric, 1)
        )::TEXT,
        r.sem_score,
        r.sk_score,
        (r.loc_score + r.rec_score)::REAL,
        r.f_score
    FROM ranked r
    WHERE r.f_score >= p_min_score
    ORDER BY r.f_score DESC
    LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION public.match_jobs_for_user(UUID, REAL, INTEGER) IS
    'Hybrid job match v2: 50 semantic + 20 required skills + 15 experience + 10 location + 5 recency; hard floor 35.';

GRANT EXECUTE ON FUNCTION public.compute_experience_score(INTEGER, INTEGER, INTEGER)
    TO authenticated, service_role;

COMMIT;
