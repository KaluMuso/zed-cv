# Deployment Readiness Checklist — Zed CV / ZedApply

Use this checklist before directing paying customers to the platform.  
**Legend:** ✅ Verified in repo | ⚠️ Partial | ❌ Missing / not verified

---

## 1. Code & tests

| Item | Status | Notes |
|------|--------|-------|
| Backend pytest green | ⚠️ | 867 passed locally; 2 failures (`test_notification_channels`, `test_seed_canonical_skills`); CI must be green on `master` |
| Frontend Vitest green | ✅ | 220 tests, 45 files |
| Frontend `npm run build` | ✅ | CI job `frontend-build` |
| Backend Docker build | ✅ | CI job `backend-docker` |
| OpenAPI updated for new endpoints | ✅ | Policy in AGENTS.md; guard enforces |
| Schema drift guard | ⚠️ | Needs `SUPABASE_URL` + service key in CI secrets |
| E2E tests (Playwright/Cypress) | ❌ | Not in repo |

---

## 2. Database

| Item | Status | Notes |
|------|--------|-------|
| Migrations sequential / no duplicate prefix | ⚠️ | **Two `063_*` files** — verify apply order on staging |
| `059_audit_idempotent` applied | ⚠️ | Run post-migrate on staging |
| HNSW indexes (`066`) | ✅ | In migrations |
| Tier constraints canonical (`053`, `054`) | ✅ | Migrations present |
| RLS on PII tables | ⚠️ | Run `schema_guard_rls()` live |
| pg_cron prune jobs | ⚠️ | Defined in `066`; confirm enabled on Supabase plan |
| Seed / prod data cleanup | ❌ | Manual — remove test jobs per ops runbook |

---

## 3. Backend (OCI)

| Item | Status | Notes |
|------|--------|-------|
| `.env` complete (no placeholders) | ⚠️ | Use `.env.production.example` |
| `docker compose up --force-recreate` after env change | ✅ | Documented in AGENTS.md |
| `LENCO_VERIFY_SIGNATURES=true` | ✅ | Enforced at startup in prod |
| `DEBUG=false` | ⚠️ | Verify deployed value |
| Redis `REDIS_URL` for rate limits | ⚠️ | Optional but recommended multi-instance |
| Health check `/api/v1/health` | ✅ | Includes WAHA status |
| WAHA session WORKING | ⚠️ | Ops smoke after deploy |
| WAHA image digest-pinned | ❌ | Prod compose uses `latest` |
| n8n workflows imported | ⚠️ | `infra/n8n/*.json` |
| Deep-enrich cron | ✅ | `deep_enrich_cron_6h.json` → POST tick |

---

## 4. Frontend (Vercel)

| Item | Status | Notes |
|------|--------|-------|
| `NEXT_PUBLIC_API_URL` set (prod API) | ⚠️ | Must not rely on localhost fallback |
| `NEXT_PUBLIC_SUPABASE_*` | ⚠️ | Anon key only |
| `NEXT_PUBLIC_SENTRY_DSN` | ⚠️ | Client init uses DSN presence |
| Lenco public key / widget env | ⚠️ | Per `docs/lenco_production_cutover.md` |
| Build cache bust if chunk 404s | ⚠️ | Redeploy without cache if needed |
| Custom domain + HTTPS | ⚠️ | Ops |

---

## 5. Payments

| Item | Status | Notes |
|------|--------|-------|
| DPO sandbox → prod keys | ⚠️ | |
| Lenco sandbox → prod keys | ⚠️ | |
| Webhook URLs registered at gateways | ⚠️ | |
| Lenco signature verification tested | ⚠️ | `tests/test_lenco_webhook.py` |
| DPO token/HMAC verification tested | ⚠️ | `tests/test_dpo_webhook_auth.py` |
| Tier prices match DB `tier_config` | ⚠️ | ngwee integers |
| Webhook idempotency (duplicate events) | ⚠️ | Verify in handler code before launch |

---

## 6. Communications

| Item | Status | Notes |
|------|--------|-------|
| WAHA OTP delivery | ⚠️ | |
| Resend domain verified | ⚠️ | `vergeo.company` per AGENTS.md §3.8 |
| Email OTP fallback | ✅ | Channel selection in auth |
| WhatsApp match digest cron | ⚠️ | n8n |
| Supabase heartbeat (6h) | ⚠️ | n8n — do not disable |

---

## 7. Security & compliance

| Item | Status | Notes |
|------|--------|-------|
| Secret rotation completed | ❌ | See SECURITY_AUDIT.md SEC-C02 |
| Legal pages live (`/legal/*`) | ✅ | Seeded content |
| Consent on signup | ⚠️ | `consent_accepted` on new user path |
| Account deletion flow | ✅ | `DELETE /profile` |
| Privacy policy mentions ZDPA | ✅ | In seeded docs |
| Cookie policy | ⚠️ | Route exists — verify content |

---

## 8. Observability

| Item | Status | Notes |
|------|--------|-------|
| Sentry backend | ⚠️ | `main.py` init with redaction |
| Sentry frontend | ⚠️ | DSN-gated client init |
| Uptime monitoring | ❌ | Not in repo |
| Log aggregation | ❌ | |
| LLM cost dashboard | ⚠️ | `llm_usage_log` + admin routes |
| Plausible / analytics | ⚠️ | CSP allows plausible.io |

---

## 9. Disaster recovery

| Item | Status | Notes |
|------|--------|-------|
| Supabase automated backups enabled | ⚠️ | Dashboard — Pro tier |
| Backup restore tested | ❌ | `docs/disaster_recovery.md` |
| OCI volume backups (WAHA sessions) | ⚠️ | Bind mount documented in AGENTS.md |
| Rollback procedure documented | ✅ | DEPLOY.md, AGENTS.md |

---

## 10. Staging (strongly recommended)

| Item | Status | Notes |
|------|--------|-------|
| Staging Supabase project | ❌ | |
| Staging API host | ❌ | CORS entry exists for `staging.zedapply.com` |
| Staging Vercel env | ❌ | |
| Migration apply on staging first | ❌ | |

---

## Sign-off

| Role | Name | Date | Go / No-Go |
|------|------|------|------------|
| Engineering | | | |
| Security | | | |
| Product | | | |
| Ops | | | |

**Minimum for soft launch:** Sections 1–6 complete with no Critical items open in `SECURITY_AUDIT.md`.
