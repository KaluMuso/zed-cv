# ZedApply production cutover checklist

Move from sandbox integrations to production credentials and soft launch.
Run `python scripts/production_readiness_audit.py` from `apps/backend/` before
each phase and after deploys.

**Repo migrations:** `001`–`055` under `infra/supabase/migrations/` (latest
schema: `055_free_tier_promo.sql`). If prod already has that schema under
**old** duplicate prefixes, run **only** `059_audit_idempotent.sql` to verify —
see `docs/migrations.md`. Do not re-apply renumbered files.

---

## PHASE 1 — Lenco sandbox → production credentials

| Step | Owner | Action |
|------|-------|--------|
| 1.1 | Kaluba | Contact Lenco support: request **production API key** + **public key** (`pub-...`) |
| 1.2 | Vercel | `NEXT_PUBLIC_LENCO_PUBLIC_KEY` = production `pub-...` |
| 1.3 | Vercel | `NEXT_PUBLIC_LENCO_WIDGET_URL` = `https://pay.lenco.co/js/v1/inline.js` |
| 1.4 | OCI `~/n8n-docker/.env` | `LENCO_API_KEY` = production secret |
| 1.5 | OCI `~/n8n-docker/.env` | `LENCO_API_URL` = `https://api.lenco.co/access/v2/` |
| 1.6 | Vercel | Redeploy frontend **without build cache** (fresh Sentry DSN inline if changed) |
| 1.7 | OCI | `cd /home/ubuntu/zedcv && git pull origin master` |
| 1.8 | OCI | `cd ~/n8n-docker && docker compose build --no-cache zedcv-backend` |
| 1.9 | OCI | `docker compose up -d --force-recreate zedcv-backend` |
| 1.10 | Kaluba | **Smoke test:** real **K125** charge to MTN (`+260…`), confirm Lenco widget opens, payment completes, subscription tier = `starter` |

**Verify:** audit script shows green for `DEBUG=false`, `LENCO_API_URL` (prod), `SENTRY_DSN`, `WAHA WORKING`.

**Rollback:** revert Vercel/OCI env to sandbox URLs and keys; force-recreate backend; redeploy frontend.

---

## PHASE 2 — Email infrastructure

| Step | Owner | Action |
|------|-------|--------|
| 2.1 | Vercel/OCI | `RESEND_API_KEY` = production key |
| 2.2 | DNS | Verify **zedapply.com** (or primary domain) **SPF**, **DKIM**, **DMARC** in Resend dashboard |
| 2.3 | Kaluba | Send signup/OTP test email → confirm delivery to Gmail and Yahoo (inbox, not spam) |

**Verify:** Resend dashboard shows verified domain; test message `delivered`.

---

## PHASE 3 — Observability

| Step | Owner | Action |
|------|-------|--------|
| 3.1 | Frontend | Add `src/app/global-error.js` (or `.tsx`) for React render errors → Sentry |
| 3.2 | Frontend | Confirm `tracesSampleRate: 0.1` in `sentry.shared.ts` (adjust if cost allows) |
| 3.3 | Sentry | Alert rule: **≥5 errors/min** on route `/matches` → notify Kaluba (WhatsApp or email) |

**Verify:** trigger a test error in staging; event appears in Sentry with environment `production`.

---

## PHASE 4 — Backups & disaster recovery

| Step | Owner | Action |
|------|-------|--------|
| 4.1 | Supabase | Confirm **automatic backups** enabled (upgrade to Pro if free tier insufficient) |
| 4.2 | Docs | Maintain `docs/disaster_recovery.md` (restore steps, RPO/RTO, contacts) |
| 4.3 | Kaluba | Test restore on a **Supabase preview branch** from latest backup |

**Verify:** preview branch has expected row counts on `users`, `jobs`, `cvs`.

---

## PHASE 5 — Soft launch

| Step | Owner | Action |
|------|-------|--------|
| 5.1 | Kaluba | Invite **10 beta users** via WhatsApp |
| 5.2 | Ops | Monitor Sentry for new crashes daily |
| 5.3 | Product | Track signup → CV upload → pay funnel (analytics or manual spreadsheet) |
| 5.4 | Team | Iterate on feedback; keep `is_review_required` queue near zero before marketing push |

**Go/no-go:** all audit checks green; no active jobs without apply path; WAHA `WORKING`; Lenco prod smoke passed.

---

## Quick commands

```bash
# Production readiness (from apps/backend, with .env loaded)
cd apps/backend && python scripts/production_readiness_audit.py

# OCI backend deploy (after merge to master)
cd /home/ubuntu/zedcv && git pull origin master
cd ~/n8n-docker && docker compose build --no-cache zedcv-backend
docker compose up -d --force-recreate zedcv-backend

# Health
curl -s https://api.zedcv.com/api/v1/health | jq .
```

---

## Related docs

- `DEPLOY.md` — routine deploy steps
- `AGENTS.md` §3 — known failure modes (CORS, WAHA, matching)
- `docs/CI_SCHEMA_GUARD.md` — schema drift guards
