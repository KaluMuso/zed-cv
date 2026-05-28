# Zed CV / ZedApply — Security Audit

**Audit date:** 2026-05-28  
**Auditor perspective:** Practical pre-launch review (not a formal penetration test).

---

## Summary

| Severity | Count (actionable) |
|----------|-------------------|
| Critical | 2 |
| High | 6 |
| Medium | 8 |
| Low | 5 |

---

## Critical

### SEC-C01 — Production payment webhook forgery surface (DPO)

**Finding:** DPO webhooks authenticate primarily via `verify_company_token` (shared token in payload/header). HMAC verification exists in `dpo_webhook.py` but is **disabled unless** `DPO_PAY_WEBHOOK_SECRET` is set.

**Risk:** Forged success callbacks could upgrade tiers if token leaks or validation is misconfigured.

**Recommendation:** Set HMAC secret in production; reject requests without valid signature. Add integration tests for rejected/forged payloads.

**Files:** `apps/backend/app/services/dpo_webhook.py`, `apps/backend/app/api/v1/webhooks.py`

---

### SEC-C02 — Credential exposure history (unverified remediation)

**Finding:** Attached task matrices and `CODE_REVIEW_PROMPT.md` reference historical Git leaks (Supabase service key, Gemini, etc.). Cannot verify rotation from codebase alone.

**Risk:** Full database exfiltration, unlimited AI spend.

**Recommendation:** Rotate all keys; audit git history with `gitleaks`; use separate Supabase keys for CI vs prod; never commit `.env`.

---

## High

### SEC-H01 — OTP verification not timing-safe on failure path

**Finding:** `verify_otp` queries `otp_codes` with `.eq("code", body_code_hash)`. Wrong guesses increment `attempts` but do not use `hmac.compare_digest` against a constant-time comparison of candidate codes.

**Risk:** Theoretical timing side-channels; practical risk lowered by rate limits (`10/minute`) and hashed storage.

**Recommendation:** Fetch latest OTP row by phone only; compare hash with `hmac.compare_digest`.

**Files:** `apps/backend/app/api/v1/auth.py`

---

### SEC-H02 — Admin authorization model inconsistency

**Finding:** `admin.py` module doc says "All endpoints require role = superadmin" but router uses `require_admin` (admin **or** superadmin). Frontend `AdminGuard` allows both roles.

**Risk:** Over-broad admin access if `admin` role assigned casually.

**Recommendation:** Document intended RBAC; restrict destructive ops to `superadmin`; audit `admin` role assignments in DB.

---

### SEC-H03 — Service role bypasses RLS

**Finding:** Backend uses Supabase **service role** key — bypasses RLS by design.

**Risk:** Any backend bug (IDOR, missing `user_id` filter) exposes all rows.

**Recommendation:** Per-route authorization tests; never trust client-supplied `user_id`; schema guard in CI.

---

### SEC-H04 — WAHA unofficial API + session on shared VM

**Finding:** WhatsApp via WAHA (web session). Prod compose uses `waha:latest`.

**Risk:** Account ban, session loss → OTP outage; supply-chain risk on unpinned image.

**Recommendation:** Digest-pin WAHA image (per AGENTS.md); isolate WAHA host; email OTP fallback always on.

---

### SEC-H05 — No WAF / edge rate limit at nginx (in-repo)

**Finding:** Application rate limits exist; nginx config in `infra/production/nginx.conf` has rate zone but edge DDoS protection not documented.

**Risk:** volumetric attacks on `/auth/otp/request`, `/cv/upload`.

**Recommendation:** Cloudflare or OCI WAF; ensure `REDIS_URL` for shared rate limit state across replicas.

---

### SEC-H06 — CSRF on cookie-less JWT API

**Finding:** API uses Bearer tokens in `Authorization` header (typical for SPA) — CSRF risk lower than cookie sessions.

**Risk:** If any endpoint uses cookie auth without `SameSite`, CSRF possible.

**Recommendation:** Confirm no sensitive cookie-based session without CSRF token.

---

## Medium

### SEC-M01 — CORS allows credentials + multiple origins

**Finding:** `CORSMiddleware` with `allow_credentials=True` and regex for Vercel previews.

**Risk:** Misconfigured origin regex could allow token theft via malicious preview deploy (low if regex is strict).

**Recommendation:** Tighten preview regex; separate staging API origin list.

---

### SEC-M02 — File upload attack surface

**Finding:** CV upload uses MIME validation (`python-magic`) and size limits.

**Risk:** Malicious PDF/DOCX; parser bombs.

**Recommendation:** Max pages/size caps; virus scan optional; sandbox parsing.

**Files:** `apps/backend/app/api/v1/cv.py`

---

### SEC-M03 — Prompt injection via CV/job text

**Finding:** User-controlled text sent to LLMs for parsing/matching explanations.

**Risk:** Instruction injection affecting output quality or data exfil in model callbacks.

**Recommendation:** System prompt hardening; output schema validation (partially done); strip HTML.

---

### SEC-M04 — OpenAPI /docs in production

**Finding:** `docs_url` disabled when `DEBUG=false` — **good**.

**Risk:** If `DEBUG` mis-set true in prod, API surface exposed.

**Recommendation:** Deploy check in `production_readiness_audit.py`.

---

### SEC-M05 — n8n credentials in workflows

**Finding:** n8n workflows in `infra/n8n/` may reference env vars; hardcoded secrets called out in task CSV.

**Risk:** Leaked workflow exports in git.

**Recommendation:** Audit JSON exports; use n8n credential store only.

---

### SEC-M06 — PII in Sentry

**Finding:** `before_send` redaction for ZM phones/emails — **good** (tests in `test_sentry_redaction.py`).

**Risk:** Regression if hook bypassed on new SDK paths.

**Recommendation:** Keep tests; sample prod events after launch.

---

### SEC-M07 — Account deletion vs retention

**Finding:** `DELETE /profile` hard-deletes user row (CASCADE). Legal docs mention 30/90-day backup retention.

**Risk:** ZDPA erasure vs tax record retention — payments may need anonymization not delete.

**Recommendation:** Soft-delete + anonymize `payments` per `018_data_subject_rights.sql` intent.

---

### SEC-M08 — Employer portal candidate PII

**Finding:** Employer contact requests with consent gating (`076_employer_portal.sql`).

**Risk:** Bulk CV search abuse if quotas bypassed.

**Recommendation:** Audit `assert_contact_quota` on all contact paths.

---

## Low

### SEC-L01 — JWT algorithm / expiry

**Finding:** HS256 with configurable expiry — standard.

**Recommendation:** Short access token TTL; refresh rotation; consider asymmetric keys at scale.

---

### SEC-L02 — `Permissions-Policy` disables camera/mic

**Good** for attack surface reduction.

---

### SEC-L03 — CSP allows `unsafe-inline` / `unsafe-eval`

**Finding:** Required for Next.js / Lenco widget — common tradeoff.

**Recommendation:** Nonce-based CSP when feasible.

---

### SEC-L04 — Dependency scanning

**Finding:** No Dependabot/Snyk config observed in snippet.

**Recommendation:** Enable GitHub Dependabot alerts.

---

### SEC-L05 — Web push VAPID keys

**Finding:** `web_push` module; ensure keys not in git.

---

## Security controls that ARE in place (verified)

| Control | Evidence |
|---------|----------|
| OTP stored hashed | `otp.py`, migration `017` |
| Rate limiting | `app/core/rate_limit.py`, route decorators |
| Lenco HMAC | `lenco_webhook.py`, production startup assert |
| WAHA webhook secret | `webhooks.py` |
| TrustedHost middleware | `main.py` |
| Security headers | `middleware.py`, `next.config.js` |
| Admin route deps | `require_admin`, ingest API key |
| RLS migrations | `040_rls_policies_track1.sql` + extensions |
| Webhook ingest auth | `require_admin_or_ingest_key` on jobs ingest |

---

## Pre-launch security checklist

- [ ] Rotate Supabase, JWT, WAHA, Gemini, OpenRouter, DPO, Lenco, Resend keys
- [ ] `LENCO_VERIFY_SIGNATURES=true` in production
- [ ] Set `DPO_PAY_WEBHOOK_SECRET` if DPO supports HMAC
- [ ] `WAHA_WEBHOOK_SECRET` non-empty in production
- [ ] `DEBUG=false` on OCI backend
- [ ] Run `schema_guard_rls()` on production DB
- [ ] Confirm no service key in frontend env
- [ ] Enable Supabase MFA on dashboard accounts
- [ ] Review Supabase RLS for tables without policies (service-only tables OK)

---

*Formal penetration testing recommended before high-volume paid marketing.*
