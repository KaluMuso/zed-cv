# Supabase migrations — apply order

All SQL lives in `infra/supabase/migrations/`. **Never edit an applied migration** — add a new numbered file instead.

## Duplicate prefixes resolved (2026-05)

Several features landed with conflicting `043_*` / `046_*` / `047_*` filenames. Prod schema was applied under the **old** names; the repo was renumbered to a strict sequence **043–055** (file renames only — do not re-execute that SQL on Supabase).

| File | Purpose |
|------|---------|
| `043_jobs_contact_phone.sql` | `jobs.contact_phone` + `admin_export_companies()` |
| `044_schema_guard_rls_rpc.sql` | `schema_guard_rls()` for production audit |
| `045_ai_cache_classifier_metadata.sql` | `ai_cache.metadata` + classifier index |
| `046_jobs_deep_scrape_enrichment.sql` | Deep-scrape columns on `jobs` |
| `047_create_skills_dictionary.sql` | `canonical_skills`, `raw_skill_mappings` |
| `048_match_jobs_60_30_10_scoring.sql` | `match_jobs_for_user` 60/30/10 RPC |
| `049_user_dashboard_preferences.sql` | User prefs: WhatsApp number, currency, alerts |
| `050_user_notifications.sql` | Digest dedup tracking |
| `051_generated_documents_dashboard_index.sql` | Index on `generated_documents` |
| `052_subscription_tier_gating.sql` | Monthly match counters + mwana/mwizi/wino |
| `053_restore_canonical_tier_model.sql` | Revert to free/starter/professional/super_standard |
| `054_tier_config_check_recovery.sql` | Recovery when tier_config CHECK blocks 053 |
| `055_free_tier_promo.sql` | Free tier 3 matches + welcome 7/mo bonus |
| `056_canonical_skills_parent_notes.sql` | `canonical_skills.parent_skill` + `notes` columns |
| `057_interview_prep.sql` | Bwana Interview: mock sessions, aptitude bank, scores |
| `059_audit_idempotent.sql` | **Verification only** — assertions, no DDL |
| `060_match_jobs_v2_weighted.sql` | Weighted v2 hybrid matching (50/20/15/10/5) + 35 floor |

### Renamed (old → new)

| Old filename | New filename |
|--------------|--------------|
| `043_schema_guard_rls_rpc.sql` | `044_schema_guard_rls_rpc.sql` |
| `044_ai_cache_classifier_metadata.sql` | `045_ai_cache_classifier_metadata.sql` |
| `045_jobs_deep_scrape_enrichment.sql` | `046_jobs_deep_scrape_enrichment.sql` |
| `046_create_skills_dictionary.sql` | `047_create_skills_dictionary.sql` |
| `046_match_jobs_60_30_10_scoring.sql` | `048_match_jobs_60_30_10_scoring.sql` |
| `046_user_dashboard_preferences.sql` | `049_user_dashboard_preferences.sql` |
| `047_user_notifications.sql` | `050_user_notifications.sql` |
| `047_generated_documents_dashboard_index.sql` | `051_generated_documents_dashboard_index.sql` |
| `047_subscription_tier_gating.sql` | `052_subscription_tier_gating.sql` |
| `048_restore_canonical_tier_model.sql` | `053_restore_canonical_tier_model.sql` |
| `049_tier_config_check_recovery.sql` | `054_tier_config_check_recovery.sql` |
| `053_free_tier_promo.sql` | `055_free_tier_promo.sql` |
| `054_canonical_skills_parent_notes.sql` | `056_canonical_skills_parent_notes.sql` |
| `060_interview_prep.sql` | `057_interview_prep.sql` |

Slot **058** remains reserved for a future migration. After PR #101 renumbered 043–055, **056** was the first open slot used for canonical skills parent/notes; interview prep lives at **057** so **060** is exclusively `match_jobs_v2_weighted`.

## Verifying prod (Supabase SQL Editor)

If schema from the old-numbered files is **already applied**, run **only**:

```sql
-- infra/supabase/migrations/059_audit_idempotent.sql
```

Expect: `NOTICE: 059 audit: migrations 043–055 schema checks passed.`

Do **not** re-run `043`–`055` migration bodies — that would be redundant and risks drift on idempotent guards.

## Local / CI

```bash
# Supabase CLI (fresh database only — applies full chain)
supabase db push
```

For drift repair on `supabase_migrations.schema_migrations`, see comments at the bottom of `059_audit_idempotent.sql`.

## Invariants after 055

- Tier keys: `free`, `starter`, `professional`, `super_standard` only.
- `tier_config` free tier: `matches_limit = 3`.
- `users.welcome_match_bonus` / `welcome_match_bonus_until` + `trg_set_welcome_bonus` on insert.

## Apply order after 055

| Order | File | Notes |
|-------|------|-------|
| 1 | `056_canonical_skills_parent_notes.sql` | DDL — `parent_skill` + `notes` on `canonical_skills` |
| 2 | `057_interview_prep.sql` | DDL — apply once on fresh DBs; prod may already have this schema under the old `060_interview_prep` filename |
| 3 | `059_audit_idempotent.sql` | Safe to re-run — verification only |
| 4 | `060_match_jobs_v2_weighted.sql` | DDL — weighted matching RPC |

## Migration 064-067 numbering correction 2026-05-25

Three migrations were committed with the **`064_` prefix** on disk:

| File (on disk) | Status |
|----------------|--------|
| `064_deletion_export_consent.sql` | **Canonical 064** — keep this number (prod: `deletion_safety_allowlist`, etc.) |
| `064_hnsw_and_pruning.sql` | Renamed → `066_hnsw_and_pruning.sql` |
| `064_job_expiration_cron.sql` | Renamed → `067_job_expiration_cron.sql` |

All three were **already applied to prod** (HNSW indexes, pg_cron jobs `zedcv-prune-match-batch-and-ai-cache` and `zedcv-deactivate-expired-jobs`). This PR is **file/registry alignment only** — do **not** re-run the migration bodies on Supabase.

### Renamed (old → new)

| Old filename | New filename |
|--------------|--------------|
| `064_hnsw_and_pruning.sql` | `066_hnsw_and_pruning.sql` |
| `064_job_expiration_cron.sql` | `067_job_expiration_cron.sql` |

### Expected apply order (06x slot)

| Order | File |
|-------|------|
| … | `060_match_jobs_v2_weighted.sql` |
| … | `061_match_batches.sql` |
| … | `062_dual_channel_notifications.sql` |
| … | `063_seed_legal_docs.sql`, `063_trusted_devices_and_sensitive_actions.sql` |
| … | `064_deletion_export_consent.sql` |
| … | `065_llm_usage_log.sql` |
| … | `066_hnsw_and_pruning.sql` |
| … | `067_job_expiration_cron.sql` |

### Prod registry backfill

After merge, run once in the SQL Editor:

```sql
-- scripts/backfill_renamed_migrations_in_registry.sql
```

Then verify:

```sql
SELECT name FROM supabase_migrations.schema_migrations
 WHERE name LIKE '06%' ORDER BY name;
-- Expect: … 064_deletion_export_consent, 065_llm_usage_log,
--         066_hnsw_and_pruning, 067_job_expiration_cron
```

## Notifications train (099–106)

See [NOTIFICATIONS_MIGRATIONS.md](NOTIFICATIONS_MIGRATIONS.md) and [MIGRATION_RENUMBER_2026_06.md](MIGRATION_RENUMBER_2026_06.md) for apply order, prod ledger drift, and retention policy.

| File | Purpose |
|------|---------|
| `100_in_app_notifications.sql` | In-app inbox (`notifications` table) |
| `101_admin_broadcast_notifications.sql` | Admin broadcast campaigns |
| `102_admin_stats_jobs_active_public.sql` | Admin stats RPC |
| `103_zambia_skill_aliases_fix.sql` | Skill alias repair |
| `104_user_notifications_retention.sql` | 90-day prune for digest dedup ledger (`user_notifications`); weekly pg_cron |
| `105_referral_paid_status.sql` | Referral `paid` / `paid_at` |
| `106_notifications_train_schema_guard.sql` | Idempotent schema guard (prod drift) |
| `scripts/notifications_train_ledger_backfill.sql` | Manual `schema_migrations` backfill (SQL Editor only) |

**Retention:** `104` prunes **`user_notifications` only** (dedup ledger). The **`notifications`** inbox (100) is not pruned — target 30d visible / 90d archive is documented for a future product migration.
