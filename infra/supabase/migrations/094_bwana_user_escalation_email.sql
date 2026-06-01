-- 094: Optional acknowledgement email to the user when Bwana escalates to a human.

BEGIN;

ALTER TABLE public.bwana_platform_config
    ADD COLUMN IF NOT EXISTS enable_user_escalation_ack boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS user_escalation_ack_template text;

UPDATE public.bwana_platform_config
SET user_escalation_ack_template = COALESCE(
    user_escalation_ack_template,
    'Thanks for reaching out. Reference {ticket_id}. {operator} will follow up within {sla} hours at {email} or {phone}.'
)
WHERE id = 1;

ALTER TABLE public.bwana_platform_config
    ALTER COLUMN user_escalation_ack_template SET NOT NULL;

COMMENT ON COLUMN public.bwana_platform_config.enable_user_escalation_ack IS
    'When true and the user has an email on file, send escalation acknowledgement via Resend.';

COMMIT;
