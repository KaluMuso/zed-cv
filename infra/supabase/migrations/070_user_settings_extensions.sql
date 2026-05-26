-- 070: Dashboard settings extensions (quiet hours, visibility, email toggles).

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS quiet_hours_start TIME NOT NULL DEFAULT '20:00',
  ADD COLUMN IF NOT EXISTS quiet_hours_end TIME NOT NULL DEFAULT '07:00',
  ADD COLUMN IF NOT EXISTS profile_visible_to_employers BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS hidden_employer_name TEXT,
  ADD COLUMN IF NOT EXISTS notify_product_updates BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS display_timezone TEXT NOT NULL DEFAULT 'Africa/Lusaka';

COMMENT ON COLUMN public.users.quiet_hours_start IS
  'No WhatsApp digests before this local time (user display_timezone).';
COMMENT ON COLUMN public.users.quiet_hours_end IS
  'WhatsApp digests resume after this local time.';
COMMENT ON COLUMN public.users.profile_visible_to_employers IS
  'When true, featured employers may view CV when relevant.';
COMMENT ON COLUMN public.users.hidden_employer_name IS
  'Optional employer name to exclude from match suggestions.';
COMMENT ON COLUMN public.users.notify_product_updates IS
  'Marketing and product update emails.';
COMMENT ON COLUMN public.users.display_timezone IS
  'IANA timezone for quiet hours and digest scheduling display.';
