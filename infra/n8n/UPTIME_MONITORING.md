# Uptime monitoring (UptimeRobot free tier)

External uptime check for the Zed CV API. Uses [UptimeRobot](https://uptimerobot.com/) free plan (50 monitors, 5-minute interval) — no additional cost within the $30/month budget.

## Monitor configuration

| Field | Value |
| --- | --- |
| Monitor type | HTTP(s) |
| Friendly name | Zed CV API health |
| URL | `https://api.zedapply.com/api/v1/health` |
| Monitoring interval | 5 minutes (free tier default) |
| Monitor timeout | 30 seconds |
| HTTP method | GET |

## Expected response

**HTTP status:** `200`

**Content-Type:** `application/json`

**Body fields to assert** (keyword / JSON custom alert optional on paid tiers; on free tier rely on status + manual review):

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "supabase": true,
  "waha": true,
  "redis_configured": true,
  "vapid_configured": true,
  "resend_configured": true,
  "sentry_configured": true,
  "redis": true
}
```

### Status semantics

| `status` | Meaning | UptimeRobot |
| --- | --- | --- |
| `healthy` | Supabase RPC + WAHA session OK | Monitor **Up** |
| `degraded` | Supabase OK, WAHA down | Still HTTP 200 — consider alert on `"waha": false` via log review or Sentry |
| `unhealthy` | Supabase heartbeat failed | Treat as incident — DB or network |

On the free plan, UptimeRobot only checks HTTP reachability and optional keyword. **`status: healthy` is not enforced automatically** — add a weekly manual check or upgrade to keyword monitoring on `"healthy"` if needed.

Recommended keyword (if available on your plan): `"supabase":true` — confirms JSON body, not just TCP.

## Alert contacts

1. UptimeRobot → **My Settings** → **Alert Contacts** → add email (and optional SMS if within quota).
2. Link the contact to the health monitor.
3. Optional: forward UptimeRobot emails to the same operator inbox used for Sentry.

For WhatsApp on downtime, either:

- Rely on Sentry + n8n for application errors (see `docs/SENTRY_ALERTS.md`), or
- Add a second n8n workflow triggered by UptimeRobot webhook (out of scope for Wave A.1 — email alert is sufficient for launch).

## Smoke test after setup

```bash
curl -sS "https://api.zedapply.com/api/v1/health" | python3 -m json.tool
```

Confirm `status`, `supabase`, and `waha` before marking the monitor active.

## Run from OCI (cron alternative)

If UptimeRobot is unavailable, n8n heartbeat already hits Supabase every 6h. **Do not remove** `heartbeat_workflow.json` — it prevents Supabase free-tier pause. UptimeRobot is complementary (API + WAHA path), not a replacement.

## Related checks

```bash
# Full production audit (on OCI, with DB)
docker exec zedcv-backend python scripts/production_readiness_audit.py --production

# Env-only audit (Cloud Agent / CI)
cd apps/backend && python scripts/production_readiness_audit.py --skip-db --production
```
