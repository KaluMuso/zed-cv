-- Job closure lifecycle: grey recently-closed listings for 3 days, then hide from default feeds.
--
-- hidden_after is computed on jobs_user_facing only. PostgreSQL GENERATED STORED
-- columns require immutable expressions (42P17). View column renames likewise
-- require DROP + CREATE — CREATE OR REPLACE cannot rename "available" (087).

DROP VIEW IF EXISTS public.jobs_user_facing;

CREATE VIEW public.jobs_user_facing AS
  SELECT
    j.*,
    (
      COALESCE(
        j.closing_date::timestamptz,
        CASE WHEN j.is_active IS FALSE THEN j.updated_at END,
        j.created_at
      ) + INTERVAL '3 days'
    ) AS hidden_after,
    CASE
      WHEN j.is_active IS TRUE
        AND (j.closing_date IS NULL OR j.closing_date >= CURRENT_DATE)
        THEN 'open'
      WHEN j.closing_date IS NOT NULL
        AND j.closing_date < CURRENT_DATE
        AND j.closing_date >= CURRENT_DATE - INTERVAL '3 days'
        THEN 'recently_closed'
      ELSE 'archived'
    END AS visibility_status,
    -- Legacy alias from migration 087 (open listings only).
    (
      j.is_active IS TRUE
      AND (j.closing_date IS NULL OR j.closing_date >= CURRENT_DATE)
    ) AS available
  FROM public.jobs j;

COMMENT ON VIEW public.jobs_user_facing IS
  'Jobs with visibility_status, hidden_after, and legacy available flag for feeds.';
