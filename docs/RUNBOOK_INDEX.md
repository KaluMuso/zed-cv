# Operations runbook index

Single entry point for humans and AI agents. **Read [AGENTS.md](../AGENTS.md) first** (invariants + failure modes). For deploy steps, see [DEPLOY.md](../DEPLOY.md). For staging, see [staging.md](staging.md).

---

## Quick triage

| Symptom | Start here |
|---------|------------|
| Browser "CORS" on API | [AGENTS.md §3.1](../AGENTS.md) — usually backend 500, not CORS |
| Zero job matches | [AGENTS.md §3.2](../AGENTS.md) — embedding model / dim drift |
| WhatsApp OTP 503 | [AGENTS.md §3.3](../AGENTS.md) — WAHA session recovery |
| Email OTP 503 | [AGENTS.md §3.8](../AGENTS.md) — Resend domain |
| Payment widget broken | [lenco_production_smoke_test.md](lenco_production_smoke_test.md) |
| User sees 40+ matches / admin shows 0/7 delivered | Admin → Users → **Repair quota** (or `POST /admin/users/{id}/repair-delivery-quota`) — see § Admin match delivery below |
| Schema 500 after deploy | [migrations.md](migrations.md) + `production_readiness_audit.py` |

---

## Runbooks by topic

### Payments — Lenco

| Doc | When to use |
|-----|-------------|
| [lenco_production_smoke_test.md](lenco_production_smoke_test.md) | Sandbox or prod smoke: K10/K125 charge, tier activation, refund |
| [lenco_production_cutover.md](lenco_production_cutover.md) | Swap sandbox → production keys (OCI + Vercel) |
| [lenco_production_activation_guide.md](lenco_production_activation_guide.md) | Merchant activation, webhook URL, widget setup |
| [LENCO_ANDROID_TEST_PLAN.md](LENCO_ANDROID_TEST_PLAN.md) | Mobile browser checkout checklist |
| [production_cutover.md](production_cutover.md) | Full soft-launch phases (Lenco, email, Sentry, backups) |

DPO Pay: [DEPLOY.md §1.4](../DEPLOY.md), webhooks in [openapi.yaml](openapi.yaml).

---

### WhatsApp — WAHA

| Doc | When to use |
|-----|-------------|
| [AGENTS.md §3.3](../AGENTS.md) | Session not `WORKING`, OTP 503, bootstrap order |
| [disaster_recovery.md](disaster_recovery.md) | Session file backup path, OCI recovery |
| [whatsapp_scraping.md](whatsapp_scraping.md) | Channel ingest, webhook URL, `WHATSAPP_SCRAPER_WEBHOOK_TOKEN` |
| [DEPLOY.md §3.9](../DEPLOY.md) | Initial QR pairing |

**Recovery commands (prod):**

1. `POST /api/v1/admin/waha/bootstrap-session` (admin key)
2. `docker compose up -d --force-recreate zedcv-backend`
3. Re-scan QR at WAHA dashboard if session revoked

---

### Email — Resend

| Doc | When to use |
|-----|-------------|
| [AGENTS.md §3.8](../AGENTS.md) | `email_domain_unverified`, OTP 503 |
| [production_cutover.md](production_cutover.md) Phase 2 | SPF/DKIM/DMARC for **vergeo.company** |
| [auth.md](auth.md) | OTP channels (email vs WhatsApp) |

**Verify:** `GET /api/v1/admin/email-health` → `domain_verified: true`.

---

### Bwana chatbot

| Doc | When to use |
|-----|-------------|
| [BWANA_ADMIN.md](BWANA_ADMIN.md) | Admin contact/escalation config, test WAHA, migration **092** |
| [BWANA_KNOWLEDGE_BOUNDARIES.md](BWANA_KNOWLEDGE_BOUNDARIES.md) | What Bwana must never disclose |
| [bwana_faq.md](bwana_faq.md) | FAQ intent table + escalation reasons |

**Admin UI:** `/admin/bwana` · **Public config:** `GET /api/v1/bwana/public-config`

---

### Database — migrations & schema

| Doc | When to use |
|-----|-------------|
| [migrations.md](migrations.md) | Apply order, 043–055 renumber, 064–067 registry |
| [production_cutover.md](production_cutover.md) | Cutover checklist; latest migration **088** |
| [DEPLOYMENT_READINESS_CHECKLIST.md](../DEPLOYMENT_READINESS_CHECKLIST.md) | Pre-deploy migration list |
| [CI_SCHEMA_GUARD.md](CI_SCHEMA_GUARD.md) | CI drift guards, compose env vs `.env.example` |
| [disaster_recovery.md](disaster_recovery.md) | Backup restore on preview branch |

**Audit:**

```bash
cd apps/backend && python scripts/production_readiness_audit.py
```

---

### Data backfills — apply URLs & quality

| Doc | When to use |
|-----|-------------|
| [APPLY_URL_BACKFILL_V2_RUNBOOK.md](APPLY_URL_BACKFILL_V2_RUNBOOK.md) | Deep-link v2 backfill: dry-run, approval gate, `--apply` |
| [DEPLOYMENT_READINESS_CHECKLIST.md § Data / ops](../DEPLOYMENT_READINESS_CHECKLIST.md) | Run scripts via `docker exec` |

**Never** run `--apply` on prod without dry-run + human spot-check of 10 URLs.

---

### Admin — match delivery quota

| Action | When to use |
|--------|-------------|
| **Admin UI → Users → Repair quota** | Free user saw too many matches; admin credits show `0/N` this month but `/matches` lists many rows; welcome window missing (`welcome_match_bonus_until` empty). |
| `POST /api/v1/admin/users/{user_id}/repair-delivery-quota` | Same as button; body `{ "apply_welcome": true, "reset_month_credits": true }` (both default true). Superadmin JWT required. |

**What it does:**

1. **Welcome window** (free tier, `apply_welcome`): sets `welcome_match_bonus=7` if unset; sets `welcome_match_bonus_until` to `created_at + 31 days` if missing or expired.
2. **Re-credit** (`reset_month_credits`): clears `credited_at` for matches credited in the current billing month, then runs `backfill_match_credits` so only the top scores up to the effective tier limit get `credited_at` again.
3. User should refresh `/matches` — list shows only quota-delivered rows.

Replaces manual Supabase SQL on `users` + `matches`. Apply migrations **097** (dismiss reason) and **098** (skill aliases) when deploying this release.

---

### n8n — ingest, digests, heartbeat

| Doc | When to use |
|-----|-------------|
| [infra/n8n/README.md](../infra/n8n/README.md) | Workflow inventory, digest vs notification, **secret rotation** |
| [ADMIN_API_KEYS.md](ADMIN_API_KEYS.md) | `INGEST_API_KEY` / `ADMIN_API_KEY` headers |
| [admin_alerts.md](admin_alerts.md) | Review queue → WhatsApp cron |
| [SENTRY_ALERTS.md](SENTRY_ALERTS.md) | Sentry webhook → n8n → WAHA |
| [whatsapp_scraping.md](whatsapp_scraping.md) | Channel scraper webhook |

**Ingest key rotation (summary):** generate new `INGEST_API_KEY` → update OCI `apps/backend/.env` + n8n workflow env → remove hardcoded keys from Job Scraper node → `force-recreate` backend. Details: [infra/n8n/README.md § Secret rotation](../infra/n8n/README.md).

**OpenRouter cost (job scraper):** re-import `infra/n8n/job_scraper.json`; set `OPENROUTER_MODEL=google/gemini-2.0-flash` (default in repo). Workflow uses `max_tokens: 8192` per parse (was 32768). Monitor `llm_usage_log` after deploy.

**Heartbeat:** must stay active every 6h on every Supabase free-tier project ([AGENTS.md invariant](../AGENTS.md)).

---

### Observability & incidents

| Doc | When to use |
|-----|-------------|
| [SENTRY_ALERTS.md](SENTRY_ALERTS.md) | Error → WhatsApp alert pipeline |
| [WEB_PUSH_VAPID.md](WEB_PUSH_VAPID.md) | VAPID keygen, OCI + Vercel env, push smoke |
| [disaster_recovery.md](disaster_recovery.md) | RPO/RTO, contacts, restore steps |
| [PRODUCTION_GAP_ANALYSIS.md](../PRODUCTION_GAP_ANALYSIS.md) | Launch readiness score / gaps |

---

### Deploy & staging

| Doc | When to use |
|-----|-------------|
| [DEPLOY.md](../DEPLOY.md) | Greenfield prod deploy (OCI + Vercel) |
| [staging.md](staging.md) | Supabase branch / second project / env matrix |
| [production_cutover.md](production_cutover.md) | Production credential swap & go/no-go |

---

## API keys reference

See [ADMIN_API_KEYS.md](ADMIN_API_KEYS.md) for which routes accept `INGEST_API_KEY` vs `ADMIN_API_KEY`. Never log key values.

---

## For AI coding agents

1. [AGENTS.md](../AGENTS.md) — contract (read before code)
2. [AI_CONTEXT.md](../AI_CONTEXT.md) — architecture (768-dim `gemini-embedding-001`, weighted matching)
3. [openapi.yaml](openapi.yaml) — API source of truth
4. This index — ops procedures only, no code changes
