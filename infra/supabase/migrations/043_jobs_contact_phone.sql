-- 043: contact_phone on jobs + admin companies export RPC
--
-- contact_phone: Zambian E.164 (+260XXXXXXXXX) extracted from description
-- via description_body_extractor (backfill: backfill_description_extraction.py).
--
-- admin_export_companies: aggregated rows for GET /admin/export/companies.csv

BEGIN;

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS contact_phone TEXT;

COMMENT ON COLUMN public.jobs.contact_phone IS
    'E.164 phone (+260XXXXXXXXX) extracted from description body. '
    'Populated by description_body_extractor and backfill script.';

CREATE OR REPLACE FUNCTION public.admin_export_companies()
RETURNS TABLE (
    company TEXT,
    primary_apply_email TEXT,
    primary_apply_url TEXT,
    primary_phone TEXT,
    total_jobs BIGINT,
    active_jobs BIGINT,
    review_required_jobs BIGINT,
    latest_posted_at TIMESTAMPTZ,
    source_url_sample TEXT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        j.company,
        MIN(j.apply_email) FILTER (WHERE j.apply_email IS NOT NULL) AS primary_apply_email,
        MIN(j.apply_url) FILTER (
            WHERE j.apply_url IS NOT NULL AND j.apply_url NOT LIKE 'mailto:%'
        ) AS primary_apply_url,
        MIN(j.contact_phone) FILTER (WHERE j.contact_phone IS NOT NULL) AS primary_phone,
        COUNT(*)::BIGINT AS total_jobs,
        COUNT(*) FILTER (WHERE j.is_active = true)::BIGINT AS active_jobs,
        COUNT(*) FILTER (WHERE j.is_review_required = true)::BIGINT AS review_required_jobs,
        MAX(j.posted_at) AS latest_posted_at,
        MIN(j.source_url) AS source_url_sample
    FROM public.jobs j
    WHERE j.company IS NOT NULL AND j.company <> ''
    GROUP BY j.company
    ORDER BY total_jobs DESC;
$$;

COMMENT ON FUNCTION public.admin_export_companies() IS
    'One row per distinct company for admin CSV export (job counts + contact fields).';

GRANT EXECUTE ON FUNCTION public.admin_export_companies() TO service_role;

COMMIT;
