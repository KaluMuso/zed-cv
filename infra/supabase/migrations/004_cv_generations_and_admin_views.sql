-- 004 — CV generations table + cv_analysis cache type
-- Adds storage for AI-generated CVs (separate from generated_documents because the
-- generator accepts free-form job_title/company and does not require a jobs.id FK)
-- and broadens ai_cache to allow caching CV analysis results.

CREATE TABLE IF NOT EXISTS cv_generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cv_id UUID REFERENCES cvs(id) ON DELETE SET NULL,
    job_title VARCHAR(500) NOT NULL,
    company VARCHAR(255),
    content TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cv_generations_user_recent
    ON cv_generations(user_id, created_at DESC);

ALTER TABLE cv_generations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS cv_generations_self ON cv_generations;
CREATE POLICY cv_generations_self ON cv_generations FOR ALL USING (user_id = auth.uid());

-- Allow ai_cache to store CV analysis results so re-opening the analysis tab
-- doesn't re-bill the LLM until the CV is replaced.
ALTER TABLE ai_cache DROP CONSTRAINT IF EXISTS ai_cache_cache_type_check;
ALTER TABLE ai_cache
    ADD CONSTRAINT ai_cache_cache_type_check
    CHECK (cache_type IN ('embedding', 'cv_parse', 'cv_analysis', 'cover_letter', 'explanation'));
