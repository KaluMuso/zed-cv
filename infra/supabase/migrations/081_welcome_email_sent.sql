-- Track welcome email delivery (dedupe on OTP signup).
BEGIN;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS welcome_email_sent BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN public.users.welcome_email_sent IS
    'True after post-signup welcome email was sent successfully via Resend.';

COMMIT;
