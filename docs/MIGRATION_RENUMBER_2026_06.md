# Migration renumber audit — 099 / 100 train (June 2026)

**Branch:** `cursor/migration-099-100-audit-9e6a`  
**Prod project:** `chnesgmcuxyhwhzomdov`  
**Rule:** Never edit applied migration files on prod. Forward-only fixes only.

---

## 1. Repo inventory (`099*` and `100*`)

Audited on 2026-06-03. After PR #260 linearization there is **one file per prefix** in `master`:

| Prefix | File | Purpose |
| --- | --- | --- |
| **099** | `099_match_dismiss_note.sql` | `matches.dismiss_note` (hide-match “other”) |
| **100** | `100_in_app_notifications.sql` | `notifications` inbox + RLS |

### Removed duplicate (do not restore)

| Former file | Fate |
| --- | --- |
| `099_admin_stats_job_review_counts.sql` | **Deleted** in #260; body merged into `102_admin_stats_jobs_active_public.sql` |

### Renumbered from conflicting PR branches (#248 / #249 / #256)

| Old filename | Current filename |
| --- | --- |
| `100_admin_broadcast_notifications.sql` | `101_admin_broadcast_notifications.sql` |
| `101_admin_stats_jobs_active_public.sql` | `102_admin_stats_jobs_active_public.sql` |
| `102_zambia_skill_aliases_fix.sql` | `103_zambia_skill_aliases_fix.sql` |

### Related train (not `099`/`100` but same deploy batch)

| # | File |
| --- | --- |
| 101 | `101_admin_broadcast_notifications.sql` |
| 102 | `102_admin_stats_jobs_active_public.sql` |
| 103 | `103_zambia_skill_aliases_fix.sql` |
| 104 | `104_user_notifications_retention.sql` |
| 105 | `105_referral_paid_status.sql` (renumbered from duplicate `104_referral_*`) |
| 106 | `106_notifications_train_schema_guard.sql` |
| — | `scripts/notifications_train_ledger_backfill.sql` (manual SQL Editor only; **not** under `migrations/`) |

---

## 2. Prod migration history (how to query)

### Canonical ledger (Supabase)

```sql
SELECT version, name
FROM supabase_migrations.schema_migrations
WHERE name LIKE '%099%'
   OR name LIKE '%100%'
   OR name LIKE '%101%'
   OR name LIKE '%102%'
   OR name LIKE '%103%'
   OR name LIKE '%104%'
   OR name LIKE '%105%'
ORDER BY version;
```

Latest train-related row on prod (2026-06-03 audit):

| version | name |
| --- | --- |
| `20260603081919` | `099_admin_stats_job_review_counts` |

**Not** present in ledger: `099_match_dismiss_note`, `100_in_app_notifications`, `101`–`105`.

There is **no** separate `migration_ledger` table in prod; use `supabase_migrations.schema_migrations` only (see `082_migration_ledger_backfill.sql` for prior backfill pattern).

### Schema reality vs ledger (prod 2026-06-03)

| Object | In prod schema? | In ledger? |
| --- | --- | --- |
| `matches.dismiss_note` | Yes | No (`099_match` missing) |
| `notifications` + RLS | Yes | No (`100` missing) |
| `admin_notification_*` tables | Yes | No (`101` missing) |
| `admin_stats()` incl. `jobs_active_public` | Yes | Partial (`099_admin_stats` only) |
| `prune_user_notifications()` | Yes | No (`104` missing) |
| `referral_events.paid_at` | Yes | No (`105` missing) |

Conclusion: **only one `099_*` ledger row** on prod (the old admin-stats name). Schema was applied manually or from branch SQL; ledger drifted. This is **not** the “both 099 applied” case.

---

## 3. Decision matrix

| Scenario | Action |
| --- | --- |
| **Both** `099_admin_stats_job_review_counts` **and** `099_match_dismiss_note` in ledger | Add idempotent consolidation only (originally planned as `103_*`; use `106_*` because `103` is skill aliases). |
| **Prod (actual):** one legacy `099_admin_stats` + schema ahead of ledger | Apply `106` in SQL Editor, then `scripts/notifications_train_ledger_backfill.sql`. |
| **Fresh env / CI** | `supabase db push` through `106`. Run ledger script only if registry drift appears. |

### Why ledger backfill is not migration `107_*`

Supabase Dashboard / CLI migration runners parse filenames like `107_notifications_train_ledger_backfill.sql` as numeric version `107` plus invalid suffix, causing:

`ERROR: 42601: trailing junk after numeric literal at or near "107_notifications_train_ledger_backfill"`

Registry-only SQL belongs under `scripts/`, not `infra/supabase/migrations/`.

---

## 4. Apply order — OCI / Supabase Dashboard

### A. Production (drifted ledger, schema mostly present)

Run in **Supabase SQL Editor** (project `chnesgmcuxyhwhzomdov`), in order:

1. `infra/supabase/migrations/106_notifications_train_schema_guard.sql` — idempotent; refreshes `admin_stats()` to `102` definition.
2. `scripts/notifications_train_ledger_backfill.sql` — registry only; does not drop `20260603081919`.
3. Optionally run bodies of `103` and `104` if skill aliases or pg_cron prune job still missing (prod already had prune + `paid_at` on audit date).

**Do not** re-apply deleted `099_admin_stats_job_review_counts.sql`.

Verify:

```sql
SELECT version, name FROM supabase_migrations.schema_migrations
 WHERE version >= '20260603081919' ORDER BY version;

SELECT public.admin_stats();

SELECT column_name FROM information_schema.columns
 WHERE table_name = 'matches' AND column_name = 'dismiss_note';
```

### B. Fresh database / `supabase db push`

Full numeric order:

```
098_zambia_skill_aliases.sql
099_match_dismiss_note.sql
100_in_app_notifications.sql
101_admin_broadcast_notifications.sql
102_admin_stats_jobs_active_public.sql
103_zambia_skill_aliases_fix.sql
104_user_notifications_retention.sql
105_referral_paid_status.sql
106_notifications_train_schema_guard.sql
```

Ledger backfill (prod drift only): `scripts/notifications_train_ledger_backfill.sql`

### C. OCI backend after DB

```bash
docker compose build zedcv-backend
docker compose up -d --force-recreate zedcv-backend
```

Smoke: `GET /api/v1/health`, authenticated `GET /api/v1/notifications`, admin overview stats.

---

## 5. Duplicate `104_*` fix (fresh env)

Two files shared prefix `104`:

- `104_user_notifications_retention.sql` — **keeps** `104`
- `104_referral_paid_status.sql` → **`105_referral_paid_status.sql`**

Supabase CLI applies one migration per version; duplicate prefixes break ordering.

---

## 6. References

- [NOTIFICATIONS_MIGRATIONS.md](./NOTIFICATIONS_MIGRATIONS.md) — train semantics and retention
- [SMOKE_2026_06.md](./SMOKE_2026_06.md) — prod smoke that surfaced ledger drift
- [migrations.md](./migrations.md) — general renumber policy
