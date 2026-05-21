# Admin companies CSV export

## Endpoint

`GET /api/v1/admin/export/companies.csv`

- **Auth:** Bearer JWT; caller must have `role` of `admin` or `superadmin` (`require_admin`).
- **Response:** `text/csv` with `Content-Disposition: attachment; filename="companies.csv"`.

## Columns

| Column | Source |
| --- | --- |
| `company` | Distinct `jobs.company` |
| `primary_apply_email` | `MIN(apply_email)` where not null |
| `primary_apply_url` | `MIN(apply_url)` excluding `mailto:` URLs |
| `primary_phone` | `MIN(contact_phone)` where not null |
| `total_jobs` | Row count per company |
| `active_jobs` | Count where `is_active = true` |
| `review_required_jobs` | Count where `is_review_required = true` |
| `latest_posted_at` | `MAX(posted_at)` |
| `source_url_sample` | `MIN(source_url)` |

Aggregation is implemented in Postgres as `admin_export_companies()` (migration `043_jobs_contact_phone.sql`).

## Contact phone backfill

`jobs.contact_phone` is populated from job descriptions by `description_body_extractor` (patterns: `+260XXXXXXXXX`, `0XXXXXXXXX`, and spaced/dashed variants).

Backfill existing rows:

```bash
cd apps/backend
python3 scripts/backfill_description_extraction.py
```

Use `--dry-run` to preview patches without writing.

## Frontend

Admin **Overview** tab includes **Export Companies CSV**. The download uses the authenticated API client (same pattern as Settings → export data) because `window.open` cannot attach the Bearer token cross-origin.
