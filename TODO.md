# Production Launch TODO — Zed CV / ZedApply

Prioritized from deep audit (2026-05-28).  
**Do not treat CSV task files as source of truth** — many rows are stale; this list is re-verified against the repo.

---

## P0 — Launch blockers (do first)

- [ ] **Staging environment:** Supabase staging project + Vercel preview env + OCI staging compose; run all pending migrations before prod
- [ ] **Fix migration `063` collision:** Two files `063_trusted_devices_*` and `063_seed_legal_docs.sql` — renumber one to unused prefix; backfill `supabase_migrations` if needed
- [ ] **Secret rotation:** Supabase service role, JWT secret, Gemini, OpenRouter, WAHA, DPO, Lenco, Resend — assume historical exposure
- [ ] **Payment webhooks smoke:** Lenco prod webhook + `LENCO_VERIFY_SIGNATURES=true`; DPO prod with token/HMAC; test duplicate event idempotency
- [ ] **CI green on master:** Fix failing tests; ensure `pywebpush` in `requirements.txt` if `test_web_push` is kept
- [ ] **WAHA production hardening:** Pin image digest in `docker-compose.prod.yml`; verify session mount; run OTP smoke after deploy
- [ ] **Remove localhost API fallback:** Fail `next build` if `NEXT_PUBLIC_API_URL` unset (replace silent fallback in `api.ts` and server-side fetches)

---

## P1 — Pre-launch (1–2 weeks)

- [ ] **OTP timing-safe verify:** Compare HMAC with `hmac.compare_digest` after phone-only lookup
- [ ] **DPO HMAC:** Set `DPO_PAY_WEBHOOK_SECRET` when available; document token-only fallback deprecation
- [ ] **Redis for SlowAPI:** Set `REDIS_URL` on OCI for stable rate limits across restarts/replicas
- [ ] **Automated backups:** Cron `pg_dump` → OCI Object Storage; quarterly restore drill (`docs/disaster_recovery.md`)
- [ ] **Uptime alerts:** UptimeRobot/Better Stack on `/api/v1/health` + WAHA session
- [ ] **GitHub Actions deploy:** SSH pull + `docker compose build` + migrate — remove manual-only deploy
- [ ] **Admin RBAC review:** Align `admin.py` doc vs `require_admin`; limit destructive actions to superadmin
- [ ] **Production data scrub:** Remove test jobs/skills; strip HTML from legacy job descriptions
- [ ] **Resend domain:** Confirm `RESEND_FROM_EMAIL` on verified domain (`info@vergeo.company`)
- [ ] **Drift guards:** Ensure CI secrets for live schema guard on PRs to `master`

---

## P2 — Post-soft-launch hardening

- [ ] **Match batch worker:** Move heavy matching off request path for marketing spikes (`batch_matching.py` + queue)
- [ ] **E2E tests:** Signup → CV upload → match → apply (Playwright)
- [ ] **Dependabot:** Enable dependency alerts
- [ ] **WAHA → Meta Cloud API:** Long-term OTP/digest reliability (large effort)
- [ ] **Employer portal GA:** Complete B2B UI, billing, and quota enforcement UX
- [ ] **AI budget alerts:** Dashboard on `llm_usage_log` vs monthly budget ($30)
- [ ] **CSP tighten:** Reduce `unsafe-eval` when Lenco allows
- [ ] **Lighthouse CI:** Gate PWA/mobile scores on staging

---

## P3 — Product / growth (after stable ops)

- [ ] Application kanban polish (`075_application_status`)
- [ ] Interview prep + aptitude full UX for Super Standard tier
- [ ] Employer revenue (K500/K2500) GTM
- [ ] SEO: Search Console, Bing, social share buttons
- [ ] Referral program ops (`069_user_referrals`)

---

## Completed since external task CSV (reference)

- [x] `POST /jobs/deep-enrich-tick`
- [x] Lenco webhook + signature verification
- [x] SlowAPI rate limits (auth, cv, matches, etc.)
- [x] Bwana chat API (`/bwana/chat`)
- [x] Apply modal + track apply click
- [x] Resend OTP wired in auth UI
- [x] Vitest suite (220+ tests)
- [x] Legal docs seeded + routes
- [x] JSON-LD JobPosting + sitemap
- [x] HNSW migration `066`
- [x] CV parser Pydantic guard (`CVParseResult`)
- [x] Global ErrorBoundary
- [x] Account deletion `DELETE /profile`
- [x] CI schema/openapi/compose guards
- [x] Sentry PII redaction tests

---

## Quick verification commands

```bash
# Backend tests
cd apps/backend && pip install -r requirements.txt && pytest tests/ -q

# Frontend tests + build
cd apps/frontend && npm ci && npm test -- --run && npm run build

# Migration audit SQL (on staging, as service_role)
# Run contents of infra/supabase/migrations/059_audit_idempotent.sql

# Health
curl -s https://api.zedapply.com/api/v1/health | jq .
```
