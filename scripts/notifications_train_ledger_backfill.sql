-- Manual prod repair: backfill supabase_migrations.schema_migrations for notifications train.
-- Run in Supabase SQL Editor (service_role) — NOT via supabase db push / Dashboard migrations.
--
-- Why not infra/supabase/migrations/: Dashboard/CLI parsers treat a leading
-- "107_" filename as numeric version 107 + invalid suffix (42601).
--
-- Prerequisite: schema from 099–106 already applied (run 106 guard first if unsure).
-- Keeps legacy row 20260603081919 / 099_admin_stats_job_review_counts.
--
-- Verify:
--   SELECT version, name FROM supabase_migrations.schema_migrations
--    WHERE version >= '20260603990001' ORDER BY version;

BEGIN;

INSERT INTO supabase_migrations.schema_migrations (version, name, statements)
SELECT version, name, statements
FROM (VALUES
    (
        '20260603990001',
        '099_match_dismiss_note',
        ARRAY['-- registry backfill: applied out-of-band']::text[]
    ),
    (
        '20260604000001',
        '100_in_app_notifications',
        ARRAY['-- registry backfill: applied out-of-band']::text[]
    ),
    (
        '20260604010001',
        '101_admin_broadcast_notifications',
        ARRAY['-- registry backfill: applied out-of-band']::text[]
    ),
    (
        '20260604020001',
        '102_admin_stats_jobs_active_public',
        ARRAY['-- registry backfill: applied out-of-band']::text[]
    ),
    (
        '20260604030001',
        '103_zambia_skill_aliases_fix',
        ARRAY['-- registry backfill: applied out-of-band']::text[]
    ),
    (
        '20260604040001',
        '104_user_notifications_retention',
        ARRAY['-- registry backfill: applied out-of-band']::text[]
    ),
    (
        '20260604050001',
        '105_referral_paid_status',
        ARRAY['-- registry backfill: applied out-of-band']::text[]
    ),
    (
        '20260604060001',
        '106_notifications_train_schema_guard',
        ARRAY['-- registry backfill: applied via 106 or equivalent']::text[]
    )
) AS t(version, name, statements)
WHERE NOT EXISTS (
    SELECT 1
    FROM supabase_migrations.schema_migrations sm
    WHERE sm.version = t.version
);

COMMIT;
