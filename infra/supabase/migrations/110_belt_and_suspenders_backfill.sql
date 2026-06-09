-- migration: 110_belt_and_suspenders_backfill
BEGIN;
UPDATE public.jobs SET apply_url = NULL, updated_at = NOW()
WHERE apply_url ~* '^https?://(www\.)?whatsapp\.com/channel/'
   OR apply_url ~* '^https?://(www\.)?whatsapp\.com/c/'
   OR apply_url ~* '^https?://wa\.me/channel/'
   OR apply_url ~* '^https?://(www\.)?facebook\.com/(pages|groups)/'
   OR apply_url ~* '^https?://(www\.)?linkedin\.com/company/';

UPDATE public.jobs SET contact_phone = NULL, updated_at = NOW()
WHERE contact_phone = '+260813252760';

UPDATE public.jobs SET contact_whatsapp = NULL, updated_at = NOW()
WHERE contact_whatsapp = '+260813252760';
COMMIT;
