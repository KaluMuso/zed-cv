-- 009_fix_match_rpc_type_mismatch.sql
--
-- Purpose:
--   Fix a return-type mismatch in match_jobs_for_user() that has caused
--   every call against production to fail with:
--     ERROR  42804: structure of query does not match function result type
--     DETAIL: Returned type character varying(500) does not match expected
--             type text in column 2.
--
--   The function declares
--     RETURNS TABLE (... job_title TEXT, job_company TEXT, job_location TEXT, ...)
--   but RETURN QUERY selects j.title / j.company / j.location, which are
--   VARCHAR(500) on the jobs table. PostgreSQL is strict about RETURN
--   QUERY column types — they must exactly match the declared RETURNS
--   TABLE types — so the mismatch turns every invocation into a runtime
--   error.
--
-- Carrier history:
--   - Bug shipped first in 001_initial_schema.sql:222-279.
--   - Carried verbatim into 007_align_embedding_dim_to_768.sql when that
--     migration adopted the prod signature as canonical without auditing
--     the body. On a fresh clone applying 001-007, the broken RPC ships.
--
-- Verified prod symptom (slice 2D-1f, 2026-05-10, project
-- chnesgmcuxyhwhzomdov via Supabase MCP):
--   - 1 user, 1 CV, 12 jobs, 0 matches ever generated.
--   - Failure was masked by a silent `except Exception: pass` in the
--     backend's _run_matching_task; that symptom is patched in the same
--     slice (apps/backend/app/api/v1/matches.py).
--
-- Fix:
--   Keep the RETURNS TABLE columns as TEXT (cleaner contract — the Python
--   layer already treats them as strings) and add explicit ::TEXT casts
--   on the three problem source columns inside the CTE projection.
--
--   The text-vs-varchar mismatch on columns 2-4 was masking a second
--   class of mismatch on the numeric scoring columns. After the column-2
--   fix landed, prod surfaced:
--     ERROR 42804: Returned type double precision does not match
--                  expected type real in column 5.
--   Cause: pgvector's <=> operator returns DOUBLE PRECISION, so the
--   v_score expression `(1 - (j.embedding <=> v_user_embedding)) * 100`
--   is double precision, not REAL as the RETURNS TABLE declares.
--   `f_score` (the weighted sum involving `* 0.6` numeric literals)
--   is also double precision/numeric for the same reason.
--   This migration therefore also adds explicit ::REAL casts on
--   v_score, s_score (defensive), and f_score so every numeric column
--   exits the function as REAL. b_score is already cast inline.
--
--   Scoring formula, weights (60/30/10), skill aggregation, bonus CASE
--   block, ORDER BY, LIMIT — all unchanged from migration 007 byte for
--   byte. Only the type casts differ.
--
-- Idempotency:
--   Pure DROP FUNCTION IF EXISTS … ; CREATE FUNCTION …. No data
--   migration. No schema change. Safe to re-run.
--
-- Apply ordering: run after 008.
--
-- Apply-to-prod note: this migration corrects a bug that has shipped
-- silently in 001 and 007 — apply to prod immediately after merge to
-- actually unblock matching.

-- Drop both possible signatures so CREATE is unambiguous.
DROP FUNCTION IF EXISTS public.match_jobs_for_user(uuid, integer, real);
DROP FUNCTION IF EXISTS public.match_jobs_for_user(uuid, real, integer);

CREATE FUNCTION public.match_jobs_for_user(
    p_user_id    UUID,
    p_min_score  REAL    DEFAULT 50.0,
    p_limit      INTEGER DEFAULT 20
)
RETURNS TABLE (
    job_id          UUID,
    job_title       TEXT,
    job_company     TEXT,
    job_location    TEXT,
    vector_score    REAL,
    skill_score     REAL,
    bonus_score     REAL,
    final_score     REAL,
    matched_skills  TEXT[],
    missing_skills  TEXT[]
) LANGUAGE plpgsql AS $$
DECLARE
    v_user_embedding VECTOR(768);
    v_user_skills    TEXT[];
    v_user_location  VARCHAR;
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

    SELECT u.location INTO v_user_location FROM users u WHERE u.id = p_user_id;

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
            ARRAY(SELECT s2.name
                    FROM job_skills js2
                    JOIN skills s2 ON s2.id = js2.skill_id
                   WHERE js2.job_id = j.id AND s2.name = ANY(v_user_skills)) AS m_skills,
            ARRAY(SELECT s2.name
                    FROM job_skills js2
                    JOIN skills s2 ON s2.id = js2.skill_id
                   WHERE js2.job_id = j.id AND NOT (s2.name = ANY(v_user_skills))) AS miss_skills
        FROM jobs j
        WHERE j.is_active = true AND j.embedding IS NOT NULL
    )
    SELECT
        js.j_id,
        js.j_title,
        js.j_company,
        js.j_location,
        js.v_score,
        js.s_score,
        js.b_score,
        (js.v_score * 0.6 + js.s_score * 0.3 + js.b_score * 0.1)::REAL AS f_score,
        js.m_skills,
        js.miss_skills
    FROM job_scores js
    WHERE (js.v_score * 0.6 + js.s_score * 0.3 + js.b_score * 0.1) >= p_min_score
    ORDER BY f_score DESC
    LIMIT p_limit;
END;
$$;
