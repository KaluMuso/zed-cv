-- 078_cvs_pdf_path.sql
-- Store server-generated PDF object path for scratch-built CVs (WeasyPrint export).

BEGIN;

ALTER TABLE public.cvs
    ADD COLUMN IF NOT EXISTS generated_pdf_path TEXT;

COMMENT ON COLUMN public.cvs.generated_pdf_path IS
    'Supabase Storage path for a server-rendered PDF (e.g. cvs/{user_id}/generated/{cv_id}.pdf). '
    'Null for upload-only rows until the user exports from the manual CV wizard.';

COMMIT;
