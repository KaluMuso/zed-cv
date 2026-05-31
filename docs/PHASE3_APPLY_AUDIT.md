# Phase 3 — Apply links & job detail audit

**Date:** 2026-05-31  
**Branch:** `cursor/apply-links-job-detail-211d`

## 1. Aggregator-only `apply_url` count (SQL probe)

Run in Supabase SQL Editor (same definition as `backfill_apply_urls_v2.py` / runbook):

```sql
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
```

**Baseline (from runbook, 2026-05-30):** ~107 active jobs, predominantly `jobwebzambia.com`.  
**Target after human-approved `--apply`:** &lt; 20 remaining (see `docs/APPLY_URL_BACKFILL_V2_RUNBOOK.md`).

Agents must **not** run `--apply` on production; dry-run only in CI/local.

## 2. Scraper source tags in candidate UI

| Surface | Finding | Action |
| --- | --- | --- |
| `formatJobSource()` | Only referenced in unit tests, not rendered on `/jobs` or job detail | No user-facing scraper labels |
| Admin review / Jobs tab | Shows raw `job.source` (`scraper`, etc.) | Intentional — admin only |
| Job descriptions | Footer lines like “Scraped from …” in DB text | Stripped at ingest (`strip_scraper_metadata`) and on render (`jobDetailHtml.ts`, `JobDescription.tsx`) |

## 3. Description sanitization

| Layer | Mechanism |
| --- | --- |
| Ingest | `_strip_html()` → `strip_scraper_metadata()` in `jobs.py` |
| Quality pipeline | `apply_ingest_quality_to_job_data()` normalizes markdown then strips footers |
| Frontend | `stripDescriptionHtml()` / `stripScraperMetadata()` for legacy `description` field; markdown path in `JobDescription` |

## 4. Apply resolution consistency

- **Canonical module:** `apps/frontend/src/lib/applyLink.ts`
- **`resolveApplyUrl`:** alias of `resolveApplyAction` (cards, external links)
- **`resolveApplyContactMethods`:** all channels for job detail + `ApplyModal` (re-exported as `buildApplyContactMethods`)
- **Aggregator URLs:** skipped for “Apply on company site”; falls through to email/phone when present

## 5. Job detail UX

- Primary Apply CTA with external icon when `apply_url` is employer-hosted
- `mailto:` with prefilled subject/body for `apply_email`
- `DeadlineBadge`: “Closes in X days” / “Closed” from `closing_date`
- Multiple channels → “Apply now” opens `ApplyModal` with primary + list
