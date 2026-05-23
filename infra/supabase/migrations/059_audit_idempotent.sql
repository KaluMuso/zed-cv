-- 059_audit_idempotent.sql
-- Post-apply verification for migrations 043–055 (repo filenames after renumber).
-- ASSERTIONS ONLY — no DDL/DML. Safe to re-run in Supabase SQL Editor.
-- Raises EXCEPTION on first failure (fail-fast).

BEGIN;

DO $$
BEGIN
    -- ── 043_jobs_contact_phone ──────────────────────────────────────────
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'jobs'
          AND column_name = 'contact_phone'
    ) THEN
        RAISE EXCEPTION '043: jobs.contact_phone missing';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'admin_export_companies'
    ) THEN
        RAISE EXCEPTION '043: function public.admin_export_companies missing';
    END IF;

    -- ── 044_schema_guard_rls_rpc ────────────────────────────────────────
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'schema_guard_rls'
    ) THEN
        RAISE EXCEPTION '044: function public.schema_guard_rls missing';
    END IF;

    -- ── 045_ai_cache_classifier_metadata ────────────────────────────────
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'ai_cache'
          AND column_name = 'metadata'
    ) THEN
        RAISE EXCEPTION '045: ai_cache.metadata missing';
    END IF;

    -- ── 046_jobs_deep_scrape_enrichment ─────────────────────────────────
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'jobs'
          AND column_name = 'source_platform'
    ) THEN
        RAISE EXCEPTION '046: jobs.source_platform missing';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'jobs'
          AND column_name = 'is_enriched'
    ) THEN
        RAISE EXCEPTION '046: jobs.is_enriched missing';
    END IF;
    IF to_regclass('public.idx_jobs_pending_deep_enrichment') IS NULL THEN
        RAISE EXCEPTION '046: idx_jobs_pending_deep_enrichment missing';
    END IF;

    -- ── 047_create_skills_dictionary ────────────────────────────────────
    IF to_regclass('public.canonical_skills') IS NULL THEN
        RAISE EXCEPTION '047: public.canonical_skills missing';
    END IF;
    IF to_regclass('public.raw_skill_mappings') IS NULL THEN
        RAISE EXCEPTION '047: public.raw_skill_mappings missing';
    END IF;

    -- ── 048_match_jobs_60_30_10_scoring ─────────────────────────────────
    IF NOT EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'match_jobs_for_user'
    ) THEN
        RAISE EXCEPTION '048: function public.match_jobs_for_user missing';
    END IF;

    -- ── 049_user_dashboard_preferences ──────────────────────────────────
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users'
          AND column_name = 'whatsapp_number'
    ) THEN
        RAISE EXCEPTION '049: users.whatsapp_number missing';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users'
          AND column_name = 'alert_frequency'
    ) THEN
        RAISE EXCEPTION '049: users.alert_frequency missing';
    END IF;

    -- ── 050_user_notifications ──────────────────────────────────────────
    IF to_regclass('public.user_notifications') IS NULL THEN
        RAISE EXCEPTION '050: public.user_notifications missing';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'user_notifications'
          AND column_name = 'channel'
    ) THEN
        RAISE EXCEPTION '050: user_notifications.channel missing';
    END IF;

    -- ── 051_generated_documents_dashboard_index ─────────────────────────
    IF to_regclass('public.generated_documents') IS NULL THEN
        RAISE EXCEPTION '051: public.generated_documents missing';
    END IF;
    IF to_regclass('public.idx_generated_documents_user_created') IS NULL THEN
        RAISE EXCEPTION '051: idx_generated_documents_user_created missing';
    END IF;

    -- ── 052_subscription_tier_gating ────────────────────────────────────
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users'
          AND column_name = 'matches_viewed_this_month'
    ) THEN
        RAISE EXCEPTION '052: users.matches_viewed_this_month missing';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users'
          AND column_name = 'billing_cycle_reset'
    ) THEN
        RAISE EXCEPTION '052: users.billing_cycle_reset missing';
    END IF;

    -- ── 053_restore_canonical_tier_model ────────────────────────────────
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users'
          AND column_name = 'promotion_applied_until'
    ) THEN
        RAISE EXCEPTION '053: users.promotion_applied_until missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname = 'tier_config'
          AND c.conname = 'tier_config_tier_check'
          AND pg_get_constraintdef(c.oid) LIKE '%free%'
          AND pg_get_constraintdef(c.oid) LIKE '%super_standard%'
    ) THEN
        RAISE EXCEPTION '053: tier_config_tier_check missing or not canonical';
    END IF;

    IF (SELECT COUNT(*) FROM public.tier_config
        WHERE tier IN ('free', 'starter', 'professional', 'super_standard')) <> 4 THEN
        RAISE EXCEPTION '053: tier_config must have exactly 4 canonical tiers';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = 'downgrade_expired_subscriptions'
    ) THEN
        RAISE EXCEPTION '053: function public.downgrade_expired_subscriptions missing';
    END IF;

    -- ── 054_tier_config_check_recovery (idempotent with 053 if already applied) ─
    IF NOT EXISTS (
        SELECT 1 FROM public.tier_config WHERE tier = 'free' AND price_ngwee = 0
    ) THEN
        RAISE EXCEPTION '054: tier_config free row missing or wrong price';
    END IF;

    -- ── 055_free_tier_promo ─────────────────────────────────────────────
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users'
          AND column_name = 'welcome_match_bonus'
    ) THEN
        RAISE EXCEPTION '055: users.welcome_match_bonus missing';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users'
          AND column_name = 'welcome_match_bonus_until'
    ) THEN
        RAISE EXCEPTION '055: users.welcome_match_bonus_until missing';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_set_welcome_bonus'
    ) THEN
        RAISE EXCEPTION '055: trigger trg_set_welcome_bonus missing';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.tier_config
        WHERE tier = 'free' AND matches_limit = 3
    ) THEN
        RAISE EXCEPTION '055: tier_config free matches_limit must be 3';
    END IF;

    RAISE NOTICE '059 audit: migrations 043–055 schema checks passed.';
END $$;

COMMIT;

-- ── schema_migrations drift repair (run manually if needed) ───────────────
-- Repo filenames were renumbered to match prod; do NOT re-run 043–055 SQL.
-- Only this audit should be applied if verifying drift. Example:
--
-- INSERT INTO supabase_migrations.schema_migrations (version, name)
-- VALUES ('059', '059_audit_idempotent')
-- ON CONFLICT (version) DO NOTHING;
