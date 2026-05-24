-- 064_hnsw_and_pruning.sql
--
-- 1) HNSW cosine indexes on all vector(768) embedding columns used for matching.
-- 2) pg_cron daily prune of match_batch_runs + ai_cache (>30 days), 04:00 CAT.
--
-- Vector column inventory (no title_embedding / description_embedding / summary_embedding
-- in this schema — grep + information_schema confirm only these):
--   public.jobs.embedding      — idx_jobs_embedding (001); ensured here
--   public.cvs.embedding       — missing HNSW until this migration
--   public.skills.embedding    — idx_skills_embedding_hnsw (024); ensured here
--
-- Post-apply verification (run in SQL editor as service_role):
--
--   -- Index sizes
--   SELECT indexrelid::regclass AS index_name,
--          pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
--     FROM pg_index
--    WHERE indexrelid::regclass::text IN (
--      'idx_jobs_embedding',
--      'idx_cvs_embedding_hnsw',
--      'idx_skills_embedding_hnsw'
--    );
--
--   -- Representative semantic probe (substitute a real 768-dim CV embedding)
--   EXPLAIN (ANALYZE, BUFFERS)
--   SELECT j.id,
--          (1 - (j.embedding <=> (
--              SELECT c.embedding FROM cvs c
--               WHERE c.is_primary = true AND c.embedding IS NOT NULL
--               LIMIT 1
--          ))) AS similarity
--     FROM jobs j
--    WHERE j.is_active = true
--      AND j.embedding IS NOT NULL
--    ORDER BY j.embedding <=> (
--              SELECT c.embedding FROM cvs c
--               WHERE c.is_primary = true AND c.embedding IS NOT NULL
--               LIMIT 1
--          )
--    LIMIT 50;
--   -- Expect: "Index Scan using idx_jobs_embedding" (HNSW), not Seq Scan on jobs.
--
-- pg_cron: enable "pg_cron" in Supabase Dashboard → Database → Extensions before
-- applying if the extension is not already present. Schedules are evaluated in UTC;
-- 04:00 CAT (UTC+2, no DST) = 02:00 UTC.

BEGIN;

-- ── HNSW indexes (m=16, ef_construction=64, cosine — matches match_jobs_for_user) ──

CREATE INDEX IF NOT EXISTS idx_jobs_embedding
  ON public.jobs USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_cvs_embedding_hnsw
  ON public.cvs USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_skills_embedding_hnsw
  ON public.skills USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

COMMENT ON INDEX public.idx_cvs_embedding_hnsw IS
  'HNSW cosine index for CV embeddings (768d). Pairs with idx_jobs_embedding for '
  'vector matching; params match migration 001 / 024.';

-- ── Daily log/cache prune (30-day retention, 04:00 CAT = 02:00 UTC) ───────────────

DO $zedcv_prune$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
    -- Upsert by job name (Supabase pg_cron replaces an existing job with the same name).
    PERFORM cron.schedule(
      'zedcv-prune-match-batch-and-ai-cache',
      '0 2 * * *',
      $job$
        DELETE FROM public.match_batch_runs
         WHERE started_at < NOW() - INTERVAL '30 days';
        DELETE FROM public.ai_cache
         WHERE created_at < NOW() - INTERVAL '30 days';
      $job$
    );
  ELSE
    RAISE NOTICE
      '064: pg_cron extension not installed — enable it in Supabase Dashboard, '
      'then re-run cron.schedule for job zedcv-prune-match-batch-and-ai-cache.';
  END IF;
END;
$zedcv_prune$;

COMMIT;
