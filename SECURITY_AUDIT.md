# Security Audit — Zed Apply

**Date:** 2026-05-28  
**Auditor perspective:** Practical OWASP-style review for a solo SaaS on FastAPI + Supabase + Vercel.

---

## Summary

| Severity | Count (actionable) |
|----------|-------------------|
| Critical | 1 (resolved: missing `pywebpush` could block deploy; dependency integrity) |
| High | 6 |
| Medium | 12 |
| Low | 8 |

Overall: **acceptable for soft launch** after P0/P1 items below. Not yet at enterprise SOC2 level.

---

## Critical

### C1 — Missing runtime dependency (`pywebpush`)

- **Finding:** `app/services/web_push.py` imports `pywebpush` but it was absent from `requirements.txt` (fixed in audit branch).
- **Impact:** Container fails at import → total API outage.
- **Fix:** Pin dependency; rebuild image; verify `pytest tests/test_web_push.py`.

---

## High

### H1 — Supabase service role on backend

- **Finding:** All DB access uses service key; RLS not enforced server-side.
- **Impact:** Any missing `.eq("user_id", …)` filter is IDOR.
- **Mitigation:** Grep audit for `table(` calls; add cross-user tests on `/matches`, `/users/me`, employer routes.

### H2 — Admin / ingest API keys

- **Finding:** `ADMIN_API_KEY`, `INGEST_API_KEY` grant broad access via headers.
- **Impact:** Key leak → job ingest, admin stats, tier config.
- **Mitigation:** Rotate keys quarterly; never log headers; restrict source IP on nginx if possible.

### H3 — LLM prompt injection via CV/job text

- **Finding:** Tailored CV / cover letter prompts embed user-controlled markdown.
- **Impact:** Instruction override, toxic output, token burn.
- **Mitigation:** System prompt: ignore instructions in user content; strip XML-like tags; cap input length (partially present).

### H4 — File upload

- **Finding:** CV upload uses libmagic + size cap (5MB) + allowlist — **good**.
- **Residual:** ZIP bombs / polyglot edge cases — low likelihood.
- **Mitigation:** Keep current checks; consider async virus scan only if abuse appears.

### H5 — Payment webhooks

- **Finding:** Lenco production requires `LENCO_VERIFY_SIGNATURES=true` + secret — **good** (PR #160).
- **DPO:** Verify same `compare_digest` pattern on DPO routes.
- **Mitigation:** Run `docs/lenco_production_smoke_test.md`; log breadcrumb only masked fields.

### H6 — Rate limiting without Redis

- **Finding:** In-memory slowapi resets on `force-recreate`.
- **Impact:** OTP brute force window after deploy.
- **Mitigation:** Set `REDIS_URL` (Upstash free tier).

---

## Medium

### M1 — CORS + error masking

- **Finding:** Unhandled 500 returns plain text without CORS → browser shows "CORS error" (documented in AGENTS.md).
- **Mitigation:** Keep global exception handlers; never debug with CORS widen.

### M2 — JWT auth (custom, not Supabase Auth)

- **Finding:** Access + refresh tokens signed with `JWT_SECRET`.
- **Good:** OTP stored hashed; trusted devices for login skip.
- **Gap:** No refresh rotation / reuse detection documented.
- **Mitigation:** Short access TTL; monitor refresh abuse.

### M3 — Employer candidate data

- **Finding:** Consent via WhatsApp YES + `profile_visible_to_employers` gate — **good design**.
- **Gap:** ~~`employers` / `employer_subscriptions` lack RLS (service-only today).~~ **Addressed (088):** RLS + org-scoped SELECT policies on `employers`, `employer_subscriptions`, `cv_access_audit`; backend still uses service_role.
- **Mitigation:** Keep employer reads/writes on FastAPI routes; do not expose service key to clients.

### M4 — XSS

- **Finding:** Legal admin uses bleach; frontend uses rehype-sanitize for markdown — **good**.
- **Gap:** User-generated cover letter preview — ensure sanitize on render (CoverLetterEditor uses react-markdown + sanitize).

### M5 — SSRF

- **Finding:** Deep-link fetchers pull job board URLs.
- **Mitigation:** Block private IP ranges in fetch client if not already; timeout limits.

### M6 — Secrets in repo

- **Finding:** `.env.example` only — no committed secrets observed.
- **Mitigation:** Continue; scan git history before open-sourcing.

### M7 — Webhook endpoints

- **Finding:** WAHA uses `X-Webhook-Token`; WhatsApp employer consent in `webhooks.py`.
- **Mitigation:** Rotate WAHA token; reject missing token with 401.

### M8 — Session / PII in Sentry

- **Finding:** `send_default_pii=False` + `before_send` redaction — **good**.

### M9 — CSRF

- **Finding:** API uses Bearer tokens — CSRF risk low for JSON API.
- **Note:** If cookie auth added later, require CSRF tokens.

### M10 — Dependency vulnerabilities

- **Finding:** No automated `pip audit` / `npm audit` gate in CI.
- **Mitigation:** Add weekly Dependabot or `npm audit --production` in CI (non-blocking initially).

### M11 — Superadmin phone bypass

- **Finding:** `SUPERADMIN_PHONE` env for unlimited access — intentional.
- **Mitigation:** Protect OCI `.env`; audit superadmin role in DB.

### M12 — Web Push subscriptions

- **Finding:** Endpoints stored per user; admin test push endpoint.
- **Mitigation:** Admin test push must stay `require_admin`; no PII in payload (current design OK).

---

## Low

- OpenAPI/docs exposed only when `DEBUG=true` — verify `DEBUG=false` prod.
- TrustedHostMiddleware limits host header — good.
- OTP cooldown per phone — verify in `otp` service tests.
- PWA service worker scope — standard.
- `global-error` Sentry boundary — confirm exists on Vercel prod.

---

## Security launch checklist

- [ ] `DEBUG=false` on OCI
- [ ] `LENCO_ENVIRONMENT=production` + verify signatures
- [ ] `JWT_SECRET` ≥ 32 random bytes
- [ ] `ADMIN_API_KEY` / `INGEST_API_KEY` rotated from dev values
- [ ] `REDIS_URL` set
- [ ] Supabase RLS enabled on all user tables (run `schema_guard_rls`)
- [ ] VAPID private key only on OCI, never in Vercel
- [ ] Run `production_readiness_audit.py` with DB checks green

---

*See `PRODUCTION_GAP_ANALYSIS.md` for full platform context.*
