-- 044_ai_cache_classifier_metadata.sql
-- Store WhatsApp classifier decision telemetry on ai_cache rows.

ALTER TABLE public.ai_cache
    ADD COLUMN IF NOT EXISTS metadata JSONB;

COMMENT ON COLUMN public.ai_cache.metadata IS
    'Optional telemetry, e.g. {classifier_decision, llm_response, took_ms} for whatsapp_classify cache rows.';

CREATE INDEX IF NOT EXISTS idx_ai_cache_whatsapp_classify_created
    ON public.ai_cache (created_at DESC)
    WHERE cache_type = 'whatsapp_classify';
