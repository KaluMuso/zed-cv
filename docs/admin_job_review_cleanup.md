# Admin job review queue — auto-hide vs needs review

## Customer visibility (`/jobs`, `/matches`)

A job is **publicly listable** when all of the following hold (`app/services/job_publication.py`):

| Rule | Field / check |
|------|----------------|
| Not soft-deleted | `is_active = true` |
| Cleared review gate | `is_review_required = false` |
| Apply path (unless force-published) | `apply_url`, `apply_email`, or `contact_phone` present, **or** `admin_published = true` |

The public jobs API also filters `is_review_required = false`. The `match_jobs_for_user` RPC excludes `is_review_required` rows.

## Ingest auto-hide (no admin queue)

On scraper/manual ingest, `apply_ingest_quality_to_job_data` may set `is_active = false` and `deactivation_reason` without entering review:

| Reason | Trigger |
|--------|---------|
| `missing_source_url` | No usable `source_url` / `apply_url` after sanitization |
| `aggregator_root_url` | Listing URL is a job-board homepage, not a vacancy |
| `thin_description` | Description shorter than 300 chars (when no apply URL) |
| Invalid phone cleared | `contact_phone` present but fails ZM E.164 normalization |

These rows are **hidden immediately**; they may still get `is_review_required` from Track 4e if deadline/apply rules also fail.

## Review queue (`is_review_required = true`)

Set by `compute_review_state` (`app/services/job_activation.py`) on ingest and deep-enrich:

| `review_reason` | Meaning | Typical `is_active` |
|-----------------|---------|---------------------|
| `no_apply_path` | No apply URL, email, or phone | `false` |
| `no_deadline` | No `closing_date` | `true` if apply path exists |
| `both` | Missing apply path **and** deadline | `false` |

Legacy `admin_review_reason` mirrors these for older admin UI paths.

### Needs manual admin work

- **`no_deadline`** with apply path present — add `closing_date` or run deadline backfill (`scripts/backfill_deadline_extraction.py`).
- **`no_apply_path`** with rich description — extract contacts (`backfill_description_extraction.py`) or deep-enrich tick.
- Suspected **duplicates** — `POST /admin/review-jobs/bulk-mark-duplicate`.
- Junk listings — `POST /admin/review-jobs/bulk-permanently-inactive` or dismiss on legacy queue.

### Bulk dismiss criteria (human-only `quality_score`)

These tools **only** clear `is_review_required` / set `admin_reviewed_at`. They never change
`quality_score` and never hard-delete rows.

| Criterion | When safe | Endpoint | `review_reason` after |
|-----------|-----------|----------|-------------------------|
| **No contact** (hidden) | `is_active=false`, `review_reason` in `both`, `no_apply_path` | `POST …/bulk-auto-dismiss-hidden` | `auto_dismissed_hidden` |
| **Expired** | `closing_date` &lt; today, still in queue | `POST …/bulk-dismiss-expired` | `auto_dismissed_expired` |
| **Junk description / bad URL** | `is_active=false`, `deactivation_reason` contains `thin_description`, `missing_source_url`, or `aggregator_root_url` | `POST …/bulk-dismiss-junk` | `auto_dismissed_junk` |
| **Duplicate** (manual selection) | Admin confirms duplicate listing | `POST …/bulk-mark-duplicate` | `duplicate` |
| **All safe (preview/apply)** | Runs hidden + expired + junk | `POST …/bulk-dismiss-safe` | (per row) |

CLI for hidden backlog only:

```bash
cd apps/backend
python3 scripts/batch_dismiss_hidden_review_queue.py --dry-run
python3 scripts/batch_dismiss_hidden_review_queue.py --apply
```

Does **not** auto-dismiss `no_deadline` rows that are still `is_active=true` (may only need a date).

## Active · no deadline · has apply path (~47 rows, human-only)

These jobs are **`is_active=true`**, **`review_reason=no_deadline`**, and already have
`apply_url`, `apply_email`, or `contact_phone`. They appear on `/jobs` but stay out of
matches until `is_review_required` is cleared (usually by setting `closing_date`).

**Do not** include this bucket in safe bulk dismiss, hidden auto-dismiss, or any mass
auto-dismiss script. Each row needs a human decision.

### Admin UI

| Control | Location |
|---------|----------|
| Filter preset **Active · no deadline · has apply path** | `/admin/jobs/review` queue dropdown |
| Overview pill **Active, no deadline** | Review queue overview strip |
| **Mark selected duplicate** | Select checkboxes → bulk action (clears review, sets `review_reason=duplicate`) |
| **Save & publish** | Per-row: set `closing_date` (and apply fields if needed) → clears review |

API: `GET /admin/review-jobs?preset=active_no_deadline`

### Example: Chengelo PE teacher duplicate

Two scraper ingestions for the same role can land in this bucket:

| Row | Title (example) | Source | Action |
|-----|-----------------|--------|--------|
| A | Physical Education Teacher | `scraper` / school site | Keep — open source posting, add `closing_date` from the ad (e.g. `2026-07-15`), **Save & publish** |
| B | PE Teacher – Chengelo School | `scraper` / jobs board | **Mark selected duplicate** if it is the same vacancy as A (weaker copy, same employer + duties) |

Workflow:

1. Filter **Active · no deadline · has apply path**.
2. Open **View original posting** on both rows; confirm same employer and role.
3. If duplicate: select the weaker row → **Mark selected duplicate** (do not dismiss via safe bulk clear).
4. If not duplicate: add `closing_date` from the listing (or run `scripts/backfill_deadline_extraction.py` for a batch) → **Save & publish**.

### When to backfill `closing_date` vs dismiss vs approve

| Situation | Action |
|-----------|--------|
| Source page states a closing date (or “apply by …”) | Set `closing_date` on the keeper row → **Save & publish** (or deadline backfill script for many rows) |
| Same vacancy already published under another `job_id` | **Mark selected duplicate** on the extra row(s) |
| Listing is expired, closed, or spam (not a duplicate of a keeper) | **Permanently inactive** (not safe bulk dismiss) |
| No date on source and role is ongoing | Set a conservative `closing_date` (e.g. 30–90 days out) after ops policy, then **Save & publish** |

**Approve** in the legacy queue sense = Track 4e **Save & publish** once apply path + `closing_date` satisfy `can_publish_after_admin_edit`.

## Expired jobs

`deactivate_expired_jobs()` (cron + `POST /admin/jobs/bulk-deactivate` with `expired_only=true`) sets `is_active = false` when `closing_date < today`. Then run `bulk-dismiss-expired` to clear review flags on the backlog.

## Ops snapshot (2026-06-03 prod)

| Metric | Count |
|--------|------:|
| Need review (unreviewed) | 517 |
| Already inactive in queue | 471 |
| Auto-dismiss eligible (`both` / `no_apply_path` + inactive) | 446 |
| Active but missing deadline only | 47 |

Sample ingest issues: scraper batches (e.g. Mulungushi University) with `review_reason=both`, `quality_score=35`, no apply channels — hidden from users but still counted in admin “need review”.

## Prod runbook

Human operator steps (dry-run → apply, expected ~446 → ~71 backlog): **[RUNBOOK_REVIEW_QUEUE_CLEAR.md](RUNBOOK_REVIEW_QUEUE_CLEAR.md)** and `scripts/admin_review_queue_dry_run.sh`.

## Related endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /admin/review-jobs` | Track 4e queue (`is_review_required`) |
| `GET /admin/jobs/review-queue` | Legacy queue (`admin_review_reason`) |
| `POST /admin/review-jobs/bulk-auto-dismiss-hidden` | Clear hidden backlog |
| `POST /admin/jobs/bulk-deactivate?expired_only=true` | Expire by `closing_date` |
| `GET /admin/stats` | `jobs_need_review`, `jobs_deactivated`, `jobs_active_public` |
| `GET /admin/review-jobs/overview` | Review backlog + safe-dismiss eligibility counts |
| `POST /admin/review-jobs/bulk-dismiss-expired` | Clear review on past-deadline rows |
| `POST /admin/review-jobs/bulk-dismiss-junk` | Clear review on ingest-hidden junk |
| `POST /admin/review-jobs/bulk-dismiss-safe` | Hidden + expired + junk in one call |
