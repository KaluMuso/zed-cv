# Staging environment overview

Staging mirrors production topology with **isolated credentials** and **synthetic data only**. Nothing in staging should reference production Supabase, production payment keys, or real user PII.

## URLs

| Surface | URL | Notes |
| --- | --- | --- |
| Frontend (stable) | https://preview.zedapply.com | Vercel custom domain on branch `develop` |
| Frontend (PR previews) | `https://zed-cv-*-vercel.app` | Ephemeral; existing regex CORS |
| Backend API | https://staging-api.zedapply.com | OCI host port `8001` → Caddy |
| Production (do not use for QA) | https://zedapply.com / https://api.zedapply.com | `master` only |

Health checks:

```bash
curl -sS https://staging-api.zedapply.com/api/v1/health | jq
curl -sS https://staging-api.zedapply.com/api/v1/health/ready | jq
```

## Supabase

| | Production | Staging |
| --- | --- | --- |
| Project | `chnesgmcuxyhwhzomdov` | **New project** `zedapply-staging` (create in dashboard) |
| Migrations | Applied in prod | Apply same files `infra/supabase/migrations/001_*.sql` → latest |
| Data | Real users | **Synthetic only** — run `python scripts/seed_staging.py` |

Store in 1Password (or team vault):

- **ZedApply Staging — Supabase service role**
- **ZedApply Staging — Supabase anon** (for Vercel Preview env)

Never copy `users`, `cvs`, `matches`, or `payments` rows from production.

### Bootstrap staging database

1. Create project in same org/region as production.
2. Apply migrations in order (CLI `supabase db push` or SQL editor).
3. Verify schema parity:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY 1;
```

4. Seed:

```bash
export STAGING_SUPABASE_URL=https://<ref>.supabase.co
export STAGING_SUPABASE_SERVICE_KEY=<service_role>
python scripts/seed_staging.py
```

`tier_config` and RLS come from migrations; seed adds users, jobs, matches.

### Synthetic test users

| Phone | Tier | Purpose |
| --- | --- | --- |
| `+260971000001` | free | Default smoke-test user (has sample matches) |
| `+260971000002` | starter | Paid tier UX |
| `+260971000003` | professional | Paid tier UX |
| `+260971000004` | super_standard | Unlimited quota UX |
| `+260971000005` | starter | “Employer” persona (company-facing flows) |

## Vercel (Preview environment)

Assign **`preview.zedapply.com`** to the **`develop`** branch (Project → Settings → Domains).

**Preview** environment variables (not Production):

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Staging Supabase URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Staging anon key |
| `NEXT_PUBLIC_API_URL` | `https://staging-api.zedapply.com/api/v1` |
| `NEXT_PUBLIC_SENTRY_DSN` | Staging Sentry DSN (`zedapply-staging` project) |
| `NEXT_PUBLIC_ENV` | `staging` |
| `NEXT_PUBLIC_LENCO_PUBLIC_KEY` | Lenco **sandbox** public key |
| `NEXT_PUBLIC_LENCO_WIDGET_URL` | `https://pay.sandbox.lenco.co/js/v1/inline.js` |

DNS (Porkbun): `CNAME preview` → `cname.vercel-dns.com` (confirm exact target in Vercel domain UI).

## OCI backend stack

Path on server: `~/n8n-docker-staging/`

- Template: [infra/staging/docker-compose.yml](../infra/staging/docker-compose.yml)
- Secrets template: [infra/staging/.env.example](../infra/staging/.env.example)
- Caddy: [infra/staging/Caddyfile.snippet](../infra/staging/Caddyfile.snippet)

DNS: `A` record `staging-api` → OCI public IP (same VM as production).

Build and run:

```bash
cd ~/n8n-docker-staging
docker compose build backend
docker compose up -d
docker compose ps
```

**No n8n** in staging — scrapers/crons remain production-only ([n8n.md](./n8n.md)).

**WAHA:** separate container `zedcv-waha-staging`, session `default-staging`. Keep unpaired or pair a burner number; `ENABLE_ADMIN_WHATSAPP_ALERTS=false` in staging `.env`.

## Sentry

Create project **`zedapply-staging`** (frontend + backend DSNs). Do not reuse production DSN on staging surfaces.

## CI secrets (GitHub)

Optional strict gate for `develop` → `master` PRs:

- `STAGING_SUPABASE_URL`
- `STAGING_SUPABASE_SERVICE_KEY`

## Audits

```bash
# From repo root with staging credentials exported or infra/staging/.env present
python scripts/production_audit.py --env staging
python scripts/production_audit.py --env production
```

## Access

| Who | Access |
| --- | --- |
| Engineering | Supabase staging dashboard, OCI `~/n8n-docker-staging`, Vercel Preview env |
| Kaluba | Production promotion approval (`develop` → `master`) |

## Out of scope (by design)

- Staging n8n workflows
- Nightly prod → staging data sync
- Staging WAHA paired to production business number
