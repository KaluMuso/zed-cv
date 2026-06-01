-- 093: Bwana phase 2 — custom FAQ intents, escalation ticket IDs, chat analytics.

BEGIN;

ALTER TABLE public.bwana_platform_config
    ADD COLUMN IF NOT EXISTS faq_intents_json jsonb NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.bwana_platform_config.faq_intents_json IS
    'Admin-editable FAQ intents: [{intent_id, enabled, triggers[], response}]';

ALTER TABLE public.bwana_escalation_log
    ADD COLUMN IF NOT EXISTS ticket_id text;

UPDATE public.bwana_escalation_log
SET ticket_id = 'ZD-' || upper(substr(replace(id::text, '-', ''), 1, 8))
WHERE ticket_id IS NULL;

ALTER TABLE public.bwana_escalation_log
    ALTER COLUMN ticket_id SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_bwana_escalation_log_ticket_id
    ON public.bwana_escalation_log (ticket_id);

-- Append ticket reference to default templates (idempotent text replace).
UPDATE public.bwana_platform_config
SET
    human_escalation_reply_template = human_escalation_reply_template
        || E'\n\nReference: {ticket_id}',
    unsatisfied_reply_template = unsatisfied_reply_template
        || E'\n\nReference: {ticket_id}'
WHERE id = 1
  AND human_escalation_reply_template NOT LIKE '%{ticket_id}%';

CREATE TABLE IF NOT EXISTS public.bwana_event_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES public.users(id) ON DELETE SET NULL,
    session_id text,
    source text NOT NULL CHECK (source IN ('faq', 'llm', 'escalated')),
    intent_id text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bwana_event_log_created
    ON public.bwana_event_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_bwana_event_log_intent
    ON public.bwana_event_log (intent_id, created_at DESC)
    WHERE intent_id IS NOT NULL;

ALTER TABLE public.bwana_event_log ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.bwana_event_log IS
    'Per-turn Bwana chat analytics (service-role writes only).';

COMMIT;
