# Admin and service API keys

Zed CV backend routes that power n8n cron, job ingest, and operator tools accept
**service secrets via HTTP headers**, not end-user JWTs. These keys bypass RLS
because the backend uses the Supabase `service_role` key — treat leaks as
full-database write access to ingest and admin surfaces.

## Keys

| Env var | Headers accepted | Purpose |
| --- | --- | --- |
| `INGEST_API_KEY` | `INGEST_API_KEY`, `X-INGEST-API-KEY` | `POST /api/v1/jobs/ingest`, deep-enrich ticks, some scraper callbacks |
| `ADMIN_API_KEY` | `ADMIN_API_KEY`, `X-ADMIN-API-KEY` | Admin cron, email-health, WAHA bootstrap, LLM cost panels. Falls back to `INGEST_API_KEY` when unset. If set **and different** from ingest, n8n must send the admin header — see [RUNBOOK_N8N_ADMIN_AUTH.md](RUNBOOK_N8N_ADMIN_AUTH.md) |

### Admin console (browser) vs automation

The **admin UI** at `/admin/*` signs in with a normal user OTP session. The frontend sends
`Authorization: Bearer <user JWT>` where `users.role` is `admin` or `superadmin`.

**Do not** paste that session JWT into `X-ADMIN-API-KEY` or treat it as `ADMIN_API_KEY`.
Service keys are separate secrets in OCI `.env`; user JWTs expire and are tied to a phone.

| Caller | Auth |
| --- | --- |
| Admin dashboard (Next.js) | Bearer JWT, role `admin` or `superadmin` |
| n8n / cron / curl ops | `X-ADMIN-API-KEY: <ADMIN_API_KEY>` (or `INGEST_API_KEY` where documented) |
| Tier config PATCH | Superadmin JWT **or** admin API key (`require_admin_api_key_or_superadmin`) |

Superadmin **Bearer JWT** can also call many `/admin/*` routes when the DB `users.role`
is `superadmin`. Prefer API keys for n8n automation so tokens are not long-lived user JWTs.

## Operational rules

1. **Rotate quarterly** (or immediately after any suspected leak). Update OCI
   `apps/backend/.env`, then `docker compose up -d --force-recreate zedcv-backend`
   (not `restart` — env is only re-read on `up`).
2. **Never log headers** — Sentry redaction already strips common secret shapes;
   do not add debug logging of `Authorization`, `ADMIN_API_KEY`, or `INGEST_API_KEY`.
3. **Restrict by IP** on nginx when possible (`allow` OCI + n8n egress only for
   `/api/v1/jobs/ingest` and `/api/v1/admin/*`).
4. **Separate dev and prod values** — `.env.example` placeholders must not match
   production. CI uses `test-ingest-key` only in pytest.
5. **Do not expose to Vercel** — frontend bundles must not contain these keys.

## Smoke tests

```bash
# Ingest (expect 401 without key, 200/422 with key on a valid payload)
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST https://api.zedapply.com/api/v1/jobs/ingest \
  -H "Content-Type: application/json" \
  -d '{"api_key":"wrong"}'

# Admin email health
curl -s -H "X-ADMIN-API-KEY: $ADMIN_API_KEY" \
  https://api.zedapply.com/api/v1/admin/email-health | jq .domain_verified
```

See `SECURITY_AUDIT.md` (H2) and `AGENTS.md` §3.5 for env reload gotchas.
