-- LLM / embedding inference cost tracking (Prompt 4F).
-- Immutable prior migrations; this adds observability for OpenRouter + Gemini spend.

CREATE TABLE IF NOT EXISTS llm_usage_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id VARCHAR(64),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    route VARCHAR(128) NOT NULL DEFAULT 'unknown',
    feature VARCHAR(32) NOT NULL,
    provider VARCHAR(16) NOT NULL CHECK (provider IN ('openrouter', 'gemini', 'openai')),
    model VARCHAR(80) NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0 CHECK (prompt_tokens >= 0),
    completion_tokens INTEGER NOT NULL DEFAULT 0 CHECK (completion_tokens >= 0),
    cost_usd NUMERIC(14, 8) NOT NULL DEFAULT 0 CHECK (cost_usd >= 0)
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_log_created_at
    ON llm_usage_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_usage_log_feature_created
    ON llm_usage_log (feature, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_usage_log_model_created
    ON llm_usage_log (model, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_usage_log_user_created
    ON llm_usage_log (user_id, created_at DESC)
    WHERE user_id IS NOT NULL;

COMMENT ON TABLE llm_usage_log IS
    'Per-request AI inference usage for cost monitoring (OpenRouter chat, Gemini embed, OpenAI cover letters).';

-- Daily roll-up for admin dashboards and budget alerts.
CREATE OR REPLACE VIEW llm_usage_daily AS
SELECT
    (created_at AT TIME ZONE 'UTC')::date AS usage_date,
    feature,
    model,
    provider,
    COUNT(*)::bigint AS request_count,
    COALESCE(SUM(prompt_tokens), 0)::bigint AS prompt_tokens,
    COALESCE(SUM(completion_tokens), 0)::bigint AS completion_tokens,
    COALESCE(SUM(cost_usd), 0)::numeric(14, 8) AS cost_usd
FROM llm_usage_log
GROUP BY 1, 2, 3, 4;

-- Service role only — no RLS on usage logs (admin reads via backend).
ALTER TABLE llm_usage_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY llm_usage_log_service_role ON llm_usage_log
    FOR ALL
    USING (false)
    WITH CHECK (false);
