-- Backfill supabase_migrations.schema_migrations for 073–080 applied manually in prod.
-- Idempotent: ON CONFLICT DO NOTHING.
BEGIN;

INSERT INTO supabase_migrations.schema_migrations (version, name)
VALUES
    ('20260528000001', '073_job_quality_sections'),
    ('20260528000002', '074_cv_generations_match_link'),
    ('20260528000003', '075_application_status'),
    ('20260528000004', '076_employer_portal'),
    ('20260528000005', '077_cover_letter_versions'),
    ('20260528000006', '078_cvs_pdf_path'),
    ('20260528000007', '079_web_push_subscriptions'),
    ('20260528000008', '080_apply_url_backfill_log')
ON CONFLICT (version) DO NOTHING;

COMMIT;
