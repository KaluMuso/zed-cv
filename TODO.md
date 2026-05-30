# Production Launch TODO

Prioritized from the 2026-05-28 audit. **P0 = launch blocker.**

---

## P0 — Launch blockers

- [x] Pin `pywebpush` in `apps/backend/requirements.txt`
- [x] Add WeasyPrint system libs to `apps/backend/Dockerfile`
- [x] Fix frontend build (employer LencoPay types, manual CV `gpa`, push `BufferSource`)
- [ ] **Apply Supabase migrations 074–080** on prod (confirm 073 if using bulk-fix)
- [ ] **OCI:** rebuild & `force-recreate` backend after merging audit fixes
- [ ] **Vercel:** production deploy with green `npm run build`
- [x] **VAPID:** runbook in `docs/WEB_PUSH_VAPID.md`; prod `vapid_configured: true` (verify smoke on Chrome)
- [ ] **Lenco production smoke** — `docs/lenco_production_smoke_test.md`
- [ ] **WAHA** session `WORKING` — `POST /admin/waha/bootstrap-session` if needed
- [ ] **Resend:** verify `vergeo.company`; smoke welcome + OTP email
- [ ] Run `production_readiness_audit.py` on OCI (full DB, no `--skip-db`) — all green
- [ ] **Sentry → WhatsApp alerts** (Wave A.1) — n8n workflow + test fire

---

## P1 — Before marketing / paid ads

- [ ] Set `REDIS_URL` on OCI (Upstash free)
- [ ] Dry-run + apply `backfill_apply_urls_v2.py` (target aggregator URLs &lt; 20)
- [ ] Mobile smoke: Kanban drag on real phone
- [ ] Employer consent E2E screenshot on prod WAHA
- [ ] LLM prompt-injection guards on tailor CV / cover letter
- [ ] Daily `llm_usage_log` cost review + alert threshold
- [x] Extend `/health` with `redis_configured`, `vapid_configured`, `resend_configured` (env flags)
- [x] Fix 2 failing backend tests (`test_notification_channels`, `test_seed_canonical_skills`)
- [ ] Document running backfills via `docker exec` (not host `python3`)

---

## P2 — Post-launch (2–4 weeks)

- [ ] RLS on `employers`, `employer_subscriptions`, `cv_access_audit`
- [ ] CSP headers on Next.js
- [ ] `npm audit` / `pip audit` in CI (advisory)
- [ ] UptimeRobot on `/api/v1/health`
- [ ] Supabase backup restore drill on preview branch
- [ ] Update `AI_CONTEXT.md` embedding dim (768, not 1536)
- [ ] Expand Vitest coverage to employer + applications routes
- [ ] Status page for users

---

## P3 — Scale / enterprise

- [ ] Queue worker for LLM (Redis + dedicated process)
- [ ] Prometheus metrics export
- [ ] Multi-instance backend behind load balancer
- [ ] Employer verification workflow (KYC-lite)
- [ ] Whole-app 50%+ test coverage

---

## Completed this audit (branch `cursor/production-audit-fixes-211d`)

- [x] `pywebpush` dependency
- [x] Dockerfile WeasyPrint libs
- [x] Frontend TS build fixes
- [x] Audit script sentinels for migrations 074–079
- [x] `production_cutover.md` migration range updated
- [x] `PRODUCTION_GAP_ANALYSIS.md`, `SECURITY_AUDIT.md`, this file
