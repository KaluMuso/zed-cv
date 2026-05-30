# Deployment Readiness Checklist

Use this before every production deploy and before taking paying customers.

---

## Pre-merge (CI)

- [ ] `pytest apps/backend/tests/` — 0 failures (867+ passing baseline)
- [ ] `npm run lint` — no errors
- [ ] `npm run test:coverage` — scoped thresholds pass (or `[skip-coverage]` only for emergencies)
- [ ] `npm run build` — succeeds (Vercel parity)
- [ ] `docker build apps/backend` — succeeds
- [ ] OpenAPI / schema drift guards green on PR
- [ ] New endpoints reflected in `docs/openapi.yaml`

---

## Supabase

- [ ] List applied migrations vs repo `080_apply_url_backfill_log.sql`
- [ ] Apply pending: **073** (if bulk-fix), **074–080** as needed
- [ ] Sentinel probe (automated):

```bash
cd apps/backend && python scripts/production_readiness_audit.py
```

- [ ] `tier_config` has all four consumer tiers
- [ ] `schema_guard_rls` — 10 audited tables enabled
- [ ] No active jobs without `apply_url` or `apply_email` (audit red = blocker)
- [ ] n8n heartbeat workflow enabled (6h)

---

## OCI backend (`~/n8n-docker`)

- [ ] `cd ~/zedcv && git pull origin master`
- [ ] `docker compose build zedcv-backend` (not just `up --force-recreate`)
- [ ] `docker compose up -d --force-recreate zedcv-backend` (re-reads `.env`)
- [ ] Container healthy: `curl -s https://api.zedapply.com/api/v1/health | jq`
  - [ ] `supabase: true`
  - [ ] `waha: true` (degraded OK only if WhatsApp intentionally down)
- [ ] `DEBUG=false`
- [ ] `SENTRY_DSN` set
- [ ] `REDIS_URL` set (recommended)
- [ ] `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_EMAIL` set (if push enabled) — see [docs/WEB_PUSH_VAPID.md](docs/WEB_PUSH_VAPID.md)
- [ ] Lenco: `LENCO_ENVIRONMENT=production`, `LENCO_VERIFY_SIGNATURES=true`, webhook secret set
- [ ] WeasyPrint: image includes `libpango` / `libcairo` (post-audit Dockerfile)

---

## Vercel frontend

- [ ] `NEXT_PUBLIC_API_URL` → production API
- [ ] `NEXT_PUBLIC_VAPID_PUBLIC_KEY` set (must match OCI `VAPID_PUBLIC_KEY`) — [docs/WEB_PUSH_VAPID.md](docs/WEB_PUSH_VAPID.md)
- [ ] `NEXT_PUBLIC_SENTRY_DSN` set
- [ ] Lenco **production** public key + widget URL
- [ ] Deploy **without** build cache after env changes
- [ ] Smoke: login OTP, `/matches`, `/pricing` payment widget loads

---

## Integrations smoke

| Integration | Test |
|-------------|------|
| WhatsApp OTP | Request OTP → delivered |
| Email OTP | Resend `domain_verified` + inbox delivery |
| Welcome email | New user signup → one email, `welcome_email_sent` |
| Lenco | K10 payment → tier activates → refund |
| CV upload | PDF upload → parse → matches appear |
| Tailored CV | Pro user → tailor → cached second call |
| Web push | Subscribe on `/matches` → `POST /admin/push/test` — [docs/WEB_PUSH_VAPID.md](docs/WEB_PUSH_VAPID.md) |
| Employer consent | Request contact → YES on WhatsApp → employer sees phone |
| Daily digest | Cron or manual trigger → WhatsApp/email |

---

## Data / ops scripts

Run **inside** backend container or venv with `requirements.txt` installed:

```bash
docker exec -it zedcv-backend python scripts/backfill_apply_urls_v2.py
docker exec -it zedcv-backend python scripts/backfill_job_quality.py --dry-run
```

- [ ] Deep-link backfill dry-run reviewed
- [ ] `--apply` only after spot-checking 10 URLs

---

## Go / no-go

**Go** if: audit script 0 red, health OK, Lenco prod smoke done, migrations through 080 applied, Vercel build green.

**No-go** if: any P0 in `TODO.md` open, WAHA down, or active jobs missing apply paths.

---

## Rollback

1. OCI: `git checkout <previous-sha>` → rebuild → `force-recreate`
2. Vercel: promote previous deployment
3. Supabase: do **not** roll back migrations in place — forward-fix only
4. Lenco: revert to sandbox keys if payment regression

---

*Automated helper:* `cd apps/backend && python scripts/production_readiness_audit.py`*
