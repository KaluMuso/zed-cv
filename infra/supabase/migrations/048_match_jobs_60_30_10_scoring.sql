-- 048: Transparent 60/30/10 hybrid matching scores
--
-- Components (additive, max 100 total):
--   Semantic:  (1 - cosine_distance) * 60
--   Skills:    (|user ∩ job_skills| / |job_skills|) * 30
--   Bonus:     +5 location match or Remote, +5 salary range overlap
--
-- Preserves p_user_id wrapper signature for existing RPC callers.
-- experience_score is returned for transparency but is NOT multiplied
-- into final_score (strict 60+30+10 sum per product spec).

BEGIN;

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
    v_user_location  TEXT;
    v_salary_min     INTEGER;
    v_salary_max     INTEGER;
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

    SELECT up.salary_min, up.salary_max
      INTO v_salary_min, v_salary_max
      FROM user_preferences up
      WHERE up.user_id = p_user_id
      LIMIT 1;

    RETURN QUERY
    WITH job_scores AS (
        SELECT
            j.id              AS j_id,
            j.title::TEXT     AS j_title,
            j.company::TEXT   AS j_company,
            j.location::TEXT  AS j_location,
            (GREATEST(
                0::REAL,
                (1 - (j.embedding <=> v_user_embedding)) * 60
            ))::REAL AS v_score,
            (COALESCE(
                (SELECT COUNT(*)::REAL
                   FROM job_skills js2
                   JOIN skills s2 ON s2.id = js2.skill_id
                  WHERE js2.job_id = j.id
                    AND s2.name = ANY(v_user_skills))
                / NULLIF(
                    (SELECT COUNT(*)::REAL FROM job_skills js3 WHERE js3.job_id = j.id),
                    0
                )
                * 30,
                0
            ))::REAL AS s_score,
            (
                CASE
                    WHEN v_user_location IS NOT NULL
                         AND (
                             LOWER(TRIM(j.location)) = LOWER(TRIM(v_user_location))
                             OR LOWER(TRIM(j.location)) = 'remote'
                             OR LOWER(TRIM(j.location)) LIKE '%remote%'
                         )
                    THEN 5
                    ELSE 0
                END
                + CASE
                    WHEN (v_salary_min IS NOT NULL OR v_salary_max IS NOT NULL)
                         AND (j.salary_min IS NOT NULL OR j.salary_max IS NOT NULL)
                         AND COALESCE(v_salary_min, 0) <= COALESCE(j.salary_max, 2147483647)
                         AND COALESCE(j.salary_min, 0) <= COALESCE(v_salary_max, 2147483647)
                    THEN 5
                    ELSE 0
                END
            )::REAL AS b_score,
            public.compute_experience_score(
                v_user_years,
                j.experience_min_years
            )::REAL AS exp_score,
            ARRAY(
                SELECT s2.name::TEXT
                  FROM job_skills js2
                  JOIN skills s2 ON s2.id = js2.skill_id
                 WHERE js2.job_id = j.id
                   AND s2.name = ANY(v_user_skills)
            )::TEXT[] AS m_skills,
            ARRAY(
                SELECT s2.name::TEXT
                  FROM job_skills js2
                  JOIN skills s2 ON s2.id = js2.skill_id
                 WHERE js2.job_id = j.id
                   AND NOT (s2.name = ANY(v_user_skills))
            )::TEXT[] AS miss_skills
        FROM jobs j
        WHERE j.is_active = true
          AND COALESCE(j.is_review_required, false) = false
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
        (js.v_score + js.s_score + js.b_score)::REAL AS f_score,
        js.m_skills,
        js.miss_skills
    FROM job_scores js
    WHERE (js.v_score + js.s_score + js.b_score) >= p_min_score
    ORDER BY (js.v_score + js.s_score + js.b_score) DESC
    LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION public.match_jobs_for_user(UUID, REAL, INTEGER) IS
    'Hybrid job match: 60 semantic + 30 skills overlap + 10 bonus (location/salary).';

COMMIT;
