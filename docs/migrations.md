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
| `059_audit_idempotent.sql` | **Verification only** — assertions, no DDL |

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
