# Track 4e — Job activation, apply paths, review queue (2026-05-21)

## Problem

- Jobs showed "Application link unavailable" while emails existed in the description body.
- Listings without apply path or deadline were visible on `/jobs` and `/matches`.
- Descriptions rendered as a single plain-text block with no structure or deadline UX.

## Backend

| Component | Path |
|-----------|------|
| Migration 041 | `infra/supabase/migrations/041_job_review_queue.sql` — `is_review_required`, `review_reason`, `description_markdown` |
| Migration 042 | `infra/supabase/migrations/042_match_jobs_review_required_filter.sql` — RPC excludes review-pending jobs |
| Description extract | `app/services/description_body_extractor.py` |
| Deadline extract | `app/services/job_deadline_extractor.py` (OpenRouter Gemini Flash + regex fallback) |
| Activation rules | `app/services/job_activation.py` |
| Markdown normalize | `app/services/description_markdown.py` |
| Deep link | `app/services/deep_link_enricher.py` — also scans description on enrich |
| Admin API | `GET/PATCH /admin/review-jobs`, bulk duplicate/inactive |
| Ingest | `app/api/v1/jobs.py` — merge extraction, deadline, markdown, review state |

### Activation rules

- No `apply_url` and no `apply_email` (and no contact in instructions) → `is_active=false`, `is_review_required=true`, `review_reason=no_apply_path`
- No `closing_date` → `is_review_required=true` (`no_deadline` or `both`)
- Public list + matches: `is_active=true` AND `is_review_required=false`

### Backfill scripts

```bash
cd apps/backend
python3 scripts/backfill_description_extraction.py [--limit N] [--dry-run]
python3 scripts/backfill_deadline_extraction.py [--limit N] [--dry-run]
python3 scripts/backfill_review_queue.py [--limit N] [--dry-run]
```

## Frontend

- `src/lib/applyLink.ts` — email vs URL, secondary "Or email instead"
- `src/components/jobs/JobDescription.tsx` — react-markdown + remark-gfm
- `src/components/jobs/DeadlineBadge.tsx` — color-coded countdown
- `src/app/admin/_tabs/ReviewJobsTab.tsx` — Track 4e admin queue tab

## Ops (WhatsApp channel H)

Add channel ID to OCI `WHATSAPP_SCRAPE_CHANNELS`:

`0029Vak3jNIJENxu0QIAnE15` — https://whatsapp.com/channel/0029Vak3jNIJENxu0QIAnE15

Ensure WAHA session is `WORKING` and channel is followed; verify via webhook log on test post.

## Tests

```bash
cd apps/backend && python3 -m pytest tests/test_track4e.py -v
cd apps/frontend && npm test -- applyLink
```
