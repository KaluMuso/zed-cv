-- =============================================================================
-- One-time backfill: supabase_migrations.schema_migrations (prod chnesgmcuxyhwhzomdov)
-- Run in Supabase SQL Editor. NOT a repo migration — do not commit to migrations/.
-- Author: Kaluba (via Zed CV repo script) — 2026-05-24
-- =============================================================================
--
-- BACKFILL COUNT: 35 migration names (026 through 062 on disk).
-- Reserved slots with no file: 028, 058.
--
-- REGISTRY STATUS BEFORE RUN (verified 2026-05-24):
--   ~12 rows in supabase_migrations.schema_migrations; latest name is
--   025_canonicalize_skill_refs. Schema for 026–062 is already applied on prod;
--   only the registry is stale.
--
-- NOT IN THIS SCRIPT (already in registry or absent on disk):
--   001–025_* — do not re-insert (latest registered: 025_canonicalize_skill_refs).
--   028_*, 058_* — reserved; no .sql in repo.
--
-- IDEMPOTENT: WHERE NOT EXISTS on name; safe to re-run.
--
-- IF THIS FAILS:
--   1. Read the error (duplicate version vs duplicate name vs permission).
--   2. SELECT name, version FROM supabase_migrations.schema_migrations ORDER BY version;
--   3. Fix conflicting rows manually; re-run only this script (skips existing names).
--   4. Do NOT re-run migration bodies from infra/supabase/migrations/ on prod.
--
-- VERIFY AFTER:
--   SELECT COUNT(*) FROM supabase_migrations.schema_migrations;
--   -- Expect 60 rows total (60 repo files). If COUNT is 47, registry
--   -- still lacks 001–024 rows — address separately; this script only repairs 026+.
--   SELECT name FROM supabase_migrations.schema_migrations ORDER BY version DESC LIMIT 5;
--   -- Expect top names: 062_dual_channel_notifications, 061_match_batches,
--   -- 060_match_jobs_v2_weighted, 059_audit_idempotent, 057_interview_prep
-- =============================================================================

BEGIN;

INSERT INTO supabase_migrations.schema_migrations (version, name, statements)
SELECT * FROM (VALUES
    ('20260517130000', '026_user_preferences', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517130100', '027_admin_jobs_audit', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517130200', '029_jobs_review_match_crediting_auto_match', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517130300', '030_create_saved_jobs', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517130400', '031_saved_jobs_rls', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517130500', '032_experience_profile_enrichment', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517130600', '033_subscription_billing_periods', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517130700', '034_experience_penalty_0_1', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517130800', '035_activate_subscription_rpc', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517130900', '036_drop_subscription_match_counters', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517131000', '037_tier_config', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517131100', '038_whatsapp_job_ingest_columns', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517131200', '039_apply_source_tracking', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517131300', '040_rls_policies_track1', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517131400', '041_job_review_queue', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517131500', '042_match_jobs_review_required_filter', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517131600', '043_jobs_contact_phone', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517131700', '044_schema_guard_rls_rpc', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517131800', '045_ai_cache_classifier_metadata', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517131900', '046_jobs_deep_scrape_enrichment', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517132000', '047_create_skills_dictionary', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517132100', '048_match_jobs_60_30_10_scoring', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517132200', '049_user_dashboard_preferences', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517132300', '050_user_notifications', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517132400', '051_generated_documents_dashboard_index', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517132500', '052_subscription_tier_gating', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517132600', '053_restore_canonical_tier_model', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517132700', '054_tier_config_check_recovery', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517132800', '055_free_tier_promo', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517132900', '056_canonical_skills_parent_notes', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517133000', '057_interview_prep', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517133100', '059_audit_idempotent', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517133200', '060_match_jobs_v2_weighted', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517133300', '061_match_batches', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[]),
    ('20260517133400', '062_dual_channel_notifications', ARRAY['-- backfilled by Kaluba 2026-05-24']::text[])) AS t(version, name, statements)
WHERE NOT EXISTS (
  SELECT 1 FROM supabase_migrations.schema_migrations sm WHERE sm.name = t.name
);

COMMIT;
