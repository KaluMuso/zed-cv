# Admin WhatsApp alerts

Operational alerts notify Kaluba (`+260761359005`) via WAHA when the job review backlog crosses configured thresholds.

## Review queue alert

When `public.jobs` has at least **10** rows with `is_review_required = true`, the backend can send a WhatsApp message. Re-alerts fire only when the count crosses a **new** threshold since the last alert:

| Threshold | Example count |
| --- | --- |
| 10 | 10–24 jobs |
| 25 | 25–49 jobs |
| 50 | 50–99 jobs |
| 100 | 100+ jobs |

Idempotency state is stored in `ai_cache` under cache key `admin_alerts:review_queue_last_count` (`cache_type = admin_alert`).

### Message format

```
ZedApply Admin Alert
Review queue has 12 jobs needing attention.
Visit: https://www.zedapply.com/admin/review-jobs
Last alert: 2026-05-21 14:00 (5 jobs)
```

The “Last alert” line is omitted on the first alert.

### API (n8n cron)

- **Endpoint:** `POST /api/v1/admin/check-review-queue`
- **Auth:** `INGEST_API_KEY` or `X-INGEST-API-KEY` header (same secret as job ingest / match cron)
- **Implementation:** `apps/backend/app/services/admin_alerts.py`, route in `apps/backend/app/api/v1/admin_ingest.py`

### n8n workflow

Import `infra/n8n/review_queue_alert_hourly.json` into the OCI n8n instance:

1. Set workflow env (or n8n credentials): `FASTAPI_URL`, `INGEST_API_KEY`
2. Toggle **Active**
3. Schedule: every 1 hour (built into the workflow)

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENABLE_ADMIN_WHATSAPP_ALERTS` | `true` | Set `false` to stop sending (cron still runs, returns `reason: disabled`) |
| `ADMIN_ALERT_PHONE` | `+260761359005` | E.164 recipient for admin alerts |
| `WAHA_API_URL` | `http://waha:3000` (prod) | WAHA base URL |
| `WAHA_API_KEY` | (required in prod) | WAHA API key |
| `WAHA_SESSION_NAME` | `default` | WAHA session |
| `INGEST_API_KEY` | (required) | Protects the cron endpoint |

### Disable alerts on OCI

In `~/n8n-docker/.env` (backend service):

```bash
ENABLE_ADMIN_WHATSAPP_ALERTS=false
```

Recreate the backend container so env is re-read:

```bash
docker compose up -d --force-recreate zedcv-backend
```

## Deploy checklist

1. Set `ENABLE_ADMIN_WHATSAPP_ALERTS=true` on OCI `.env` (unless intentionally off).
2. Import `review_queue_alert_hourly.json` into n8n; configure `FASTAPI_URL` and `INGEST_API_KEY` on the HTTP node / workflow env.
3. Activate the workflow.
4. Confirm WAHA session is `WORKING` (`GET /api/v1/health` → `waha: true`).

## Manual test

```bash
curl -sS -X POST "https://api.zedapply.com/api/v1/admin/check-review-queue" \
  -H "INGEST_API_KEY: $INGEST_API_KEY"
```

Example response when no new threshold:

```json
{
  "review_count": 12,
  "current_threshold": 10,
  "last_threshold": 10,
  "alerts_enabled": true,
  "alerted": false,
  "reason": "already_alerted_for_threshold"
}
```
