# Apply URL backfill v2 — OCI runbook

**Migration:** `080_apply_url_backfill_log.sql` (table `apply_url_backfill_log`)  
**Script:** `apps/backend/scripts/backfill_apply_urls_v2.py`  
**Target:** active jobs with aggregator `apply_url` ~108 → **&lt;20** remaining  
**Parsers:** `apps/backend/app/services/deep_link_parsers/` (per-domain registry + redirect follow)

Run all steps on the **OCI production host** (`ubuntu@OCI`). Do **not** use host `python3` — dependencies live in the `zedcv-backend` container.

---

## Prerequisites

| Check | Command / query |
| --- | --- |
| Migration 080 applied | Supabase → `apply_url_backfill_log` exists |
| Backend image includes script | `docker exec zedcv-backend test -f /app/scripts/backfill_apply_urls_v2.py && echo ok` |
| Env in container | `docker exec zedcv-backend printenv SUPABASE_URL SUPABASE_KEY \| head -2` (non-empty) |
| Baseline aggregator count | See [Pre-flight SQL](#pre-flight-sql) (~107 as of 2026-05-30) |

If the script is missing, rebuild from `~/zedcv` per [DEPLOY.md](../DEPLOY.md) OCI redeploy section (`docker compose build` + `force-recreate`).

---

## 1. Pre-flight SQL

Run in **Supabase SQL Editor** (or `psql`) before any backfill:

```sql
-- Total active jobs still pointing at known Zambian aggregators
SELECT COUNT(*) AS aggregator_apply_urls
FROM jobs
WHERE is_active = true
  AND apply_url IS NOT NULL
  AND (
    apply_url ILIKE '%jobwebzambia.com%'
    OR apply_url ILIKE '%gozambiajobs.com%'
    OR apply_url ILIKE '%jobsearchzambia.com%'
    OR apply_url ILIKE '%jobsearchzm.com%'
    OR apply_url ILIKE '%careersinafrica.com%'
    OR apply_url ILIKE '%everjobs.com.zm%'
  );

-- Per-domain breakdown (matches script per_domain_jobs)
SELECT
  regexp_replace(
    lower(split_part(split_part(apply_url, '://', 2), '/', 1)),
    '^www\.', ''
  ) AS domain,
  COUNT(*) AS total
FROM jobs
WHERE is_active = true
  AND apply_url IS NOT NULL
  AND (
    apply_url ILIKE '%jobwebzambia.com%'
    OR apply_url ILIKE '%gozambiajobs.com%'
    OR apply_url ILIKE '%jobsearchzambia.com%'
    OR apply_url ILIKE '%jobsearchzm.com%'
    OR apply_url ILIKE '%careersinafrica.com%'
    OR apply_url ILIKE '%everjobs.com.zm%'
  )
GROUP BY 1
ORDER BY total DESC;
```

**Baseline (2026-05-30):** `aggregator_apply_urls = 107`, all on `jobwebzambia.com`.

---

## 2. Dry-run (default — no DB job updates)

Dry-run **writes audit rows** to `apply_url_backfill_log` with `dry_run = true` but does **not** update `jobs.apply_url`.

```bash
# ~107 jobs × 1s throttle ≈ 2 minutes; use -it for Ctrl+C if needed
docker exec -it zedcv-backend python scripts/backfill_apply_urls_v2.py
```

Optional smoke on a subset:

```bash
docker exec -it zedcv-backend python scripts/backfill_apply_urls_v2.py --limit 10
```

### Expected stdout (key lines)

| Line | Meaning |
| --- | --- |
| `aggregator_apply_urls_before: N` | Count of active jobs whose `apply_url` hostname is in `AGGREGATOR_DOMAINS` |
| `aggregator_apply_urls_after: N` | Same as `before` in dry-run (jobs table unchanged) |
| `confidence_update_threshold: 0.7` | Global floor; per-parser thresholds also printed in `parser_thresholds` |
| `per_domain_jobs:` | `domain: total=T proposed_fix=F` — candidates per hostname and how many would update |
| `proposed_update: N` | Parser confident + resolved URL is non-aggregator and differs from original |
| `still_aggregator: N` | Parser ran but URL would stay on aggregator (manual queue) |
| `proposed_changes_sample:` | Up to **10** spot-check rows: job id prefix, parser, confidence, old → new URL |
| `remaining_aggregator_sample (manual queue):` | Up to **15** jobs that would **not** be fixed — see below |
| `Dry-run: pass --apply to persist...` | Reminder |

### Spot-check the 10 URL sample

For each block under `proposed_changes_sample`:

1. **Parser** — expect `jobwebzambia` for current prod mix; `generic_fallback` is acceptable if confidence ≥ threshold.
2. **Confidence** — must be ≥ `0.7` (and ≥ per-parser threshold, e.g. `jobwebzambia` 0.75).
3. **New URL** — must be an **employer** site (company careers, ATS, gov/edu), not another board or social-only link.
4. **Sanity** — open 2–3 new URLs in a browser; confirm listing matches job title.

Reject `--apply` if samples show wrong employer, broken redirects, or mostly social (`facebook.com`, `linkedin.com`) without a real apply path.

### `remaining_aggregator_sample` interpretation

These are jobs the script would **leave unchanged** after a full run:

| Situation | Typical cause |
| --- | --- |
| Listing has only email/phone, no external apply link | Parser finds contact but `should_update_apply_url` requires a **non-aggregator URL** |
| Page fetch failed (timeout, 403, empty body) | `resolve_apply_contacts_from_aggregator_url` returns empty → still aggregator |
| Confidence below threshold | Parser uncertain; no update |
| Resolved URL still on aggregator | Redirect loop or board-only “apply on site” |
| Resolved URL equals original | No-op |

Use this list as the **manual remediation queue** after `--apply`. Target: combined `still_aggregator` + post-apply SQL count **&lt; 20**. If dry-run `still_aggregator` alone is already &lt; 20 after a high `proposed_update`, you are on track.

### Dry-run audit in Supabase

```sql
SELECT
  COUNT(*) AS rows,
  COUNT(*) FILTER (WHERE new_apply_url IS NOT NULL) AS would_update,
  COUNT(*) FILTER (WHERE new_apply_url IS NULL) AS would_skip
FROM apply_url_backfill_log
WHERE dry_run = true
  AND created_at > NOW() - INTERVAL '1 hour';
```

---

## 3. Human approval gate

**Proceed with `--apply` only if all are true:**

| # | Criterion |
| --- | --- |
| 1 | `proposed_update` + `still_aggregator` = total candidates (sanity on stats) |
| 2 | `aggregator_apply_urls_before - proposed_update` ≤ **20** (projected remaining) |
| 3 | All **10** `proposed_changes_sample` URLs reviewed — employer apply links look correct |
| 4 | `remaining_aggregator_sample` titles/URLs are acceptable manual backlog or known dead listings |
| 5 | Ops owner explicitly replies **Y** on the approval thread |

**Do not apply** if proposed URLs are mostly wrong, fetch errors dominate, or projected remaining &gt; 20 without a plan for manual fixes.

---

## 4. Apply (persist updates)

```bash
docker exec -it zedcv-backend python scripts/backfill_apply_urls_v2.py --apply
```

- Updates `jobs.apply_url` (+ `apply_source = 'enriched'`, optional email/phone if empty).
- Writes `apply_url_backfill_log` with `dry_run = false`.
- Progress file: `/tmp/zedcv_apply_url_backfill_v2_progress.json` inside container — resumes interrupted runs.
- Re-run from scratch: add `--reset-progress` (deletes progress file at start).

**Runtime:** ~1 second per candidate job (HTTP fetch throttle). Full 107-job run ≈ **2 minutes**.

Stdout after apply:

- `aggregator_apply_urls_after` — should drop toward **&lt; 20**
- `delta` — number of aggregator URLs removed from `jobs`
- `applied` — rows actually patched

---

## 5. Post-apply verification SQL

Run in Supabase after `--apply` completes:

```sql
-- Primary success metric (same definition as script)
SELECT COUNT(*) AS aggregator_apply_urls_remaining
FROM jobs
WHERE is_active = true
  AND apply_url IS NOT NULL
  AND (
    apply_url ILIKE '%jobwebzambia.com%'
    OR apply_url ILIKE '%gozambiajobs.com%'
    OR apply_url ILIKE '%jobsearchzambia.com%'
    OR apply_url ILIKE '%jobsearchzm.com%'
    OR apply_url ILIKE '%careersinafrica.com%'
    OR apply_url ILIKE '%everjobs.com.zm%'
  );

-- Per-domain remainder
SELECT
  regexp_replace(
    lower(split_part(split_part(apply_url, '://', 2), '/', 1)),
    '^www\.', ''
  ) AS domain,
  COUNT(*) AS remaining
FROM jobs
WHERE is_active = true
  AND apply_url IS NOT NULL
  AND (
    apply_url ILIKE '%jobwebzambia.com%'
    OR apply_url ILIKE '%gozambiajobs.com%'
    OR apply_url ILIKE '%jobsearchzambia.com%'
    OR apply_url ILIKE '%jobsearchzm.com%'
    OR apply_url ILIKE '%careersinafrica.com%'
    OR apply_url ILIKE '%everjobs.com.zm%'
  )
GROUP BY 1
ORDER BY remaining DESC;

-- Apply run audit
SELECT
  COUNT(*) FILTER (WHERE dry_run = false) AS apply_log_rows,
  COUNT(*) FILTER (WHERE dry_run = false AND new_apply_url IS NOT NULL) AS jobs_updated,
  MAX(created_at) FILTER (WHERE dry_run = false) AS last_apply_at
FROM apply_url_backfill_log;

-- Sample still-aggregator for manual queue (post-apply)
SELECT id, title, apply_url
FROM jobs
WHERE is_active = true
  AND apply_url IS NOT NULL
  AND apply_url ILIKE '%jobwebzambia.com%'
ORDER BY updated_at DESC NULLS LAST
LIMIT 15;
```

**Pass:** `aggregator_apply_urls_remaining` **&lt; 20**.

---

## 6. Rollback notes

- **Jobs:** no automatic rollback. Restore from `apply_url_backfill_log.old_apply_url` if needed (one-off SQL update by `job_id`).
- **Log table:** append-only audit; safe to keep.
- **Progress file:** remove inside container if re-running apply:  
  `docker exec zedcv-backend rm -f /tmp/zedcv_apply_url_backfill_v2_progress.json`

---

## Reference

| Item | Value |
| --- | --- |
| Aggregator domains | `jobwebzambia.com`, `gozambiajobs.com`, `jobsearchzambia.com`, `jobsearchzm.com`, `careersinafrica.com`, `everjobs.com.zm` |
| Global confidence floor | `0.7` (`CONFIDENCE_UPDATE_THRESHOLD`) |
| Throttle | `1.0` s between fetches |
| Related | [DEPLOY.md](../DEPLOY.md) § Ops scripts, [DEPLOYMENT_READINESS_CHECKLIST.md](../DEPLOYMENT_READINESS_CHECKLIST.md) |
