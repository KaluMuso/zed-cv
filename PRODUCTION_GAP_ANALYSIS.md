# Zed CV / ZedApply — Production Gap Analysis

**Audit date:** 2026-05-28  
**Scope:** Full-stack (FastAPI + Next.js 14 + Supabase + WAHA + n8n)  
**Method:** Static code review, CI/workflow inspection, migration inventory, test execution, comparison to attached task matrices (`ai_studio_code_*.csv`).

---

## Executive Summary

| Metric | Assessment |
|--------|------------|
| **Production readiness score** | **58 / 100** |
| **Deployable to real paying users (today)** | **No** — constrained pilot only |
| **Safe for real users (PII + payments)** | **Conditional** — after webhook hardening verification, secret rotation, staging migration dry-run |
| **Estimated readiness** | **1–2 weeks** of focused ops + security work for a **soft launch**; **4–6 weeks** for enterprise-grade SaaS |

### Major strengths (verified)

- **Contract-first API** with `docs/openapi.yaml`, drift guards (`schema_guard`, `openapi_ts_guard`, `compose_env_guard`), and broad backend test suite (**867 passing** locally after installing `pywebpush`).
- **Security primitives in place:** OTP hashed (HMAC-SHA256), SlowAPI rate limits, `TrustedHostMiddleware`, security headers (backend + Next.js CSP), Lenco webhook HMAC-SHA512 with production startup assert, WAHA webhook shared secret, admin `require_admin` on routers, RLS migration track (`040`, extended in later migrations).
- **AI guardrails:** Pydantic validation on CV parse output (`CVParseResult`), `ai_cache` used across embeddings/parsing/Bwana, LLM usage logging (`065_llm_usage_log`), circuit/retry helpers, CV upload queue on Gemini refusal.
- **Product surface largely built:** matching RPC v2, Apply modal, Bwana chat API, interview prep routes, employer portal backend, legal docs seeded, JSON-LD JobPosting, sitemap, account deletion, Vitest (**220 tests**), global `ErrorBoundary`.
- **Infra patterns:** Docker prod compose with nginx + healthchecks, n8n cron workflows, migration audit (`059_audit_idempotent`), HNSW indexes (`066`).

### Major weaknesses (verified)

- **No staging environment** in repo/CI — migrations and payments tested direct-to-prod risk.
- **No automated backup/restore automation** in codebase (only `docs/disaster_recovery.md`).
- **Single-node OCI + WAHA unofficial API** — WhatsApp OTP/delivery is a single point of failure; prod compose uses `devlikeapro/waha:latest` (not digest-pinned unlike AGENTS.md prod guidance).
- **Migration numbering collision:** two files share prefix `063_*` — deployment ordering ambiguity.
- **DPO webhook** relies on company-token comparison; HMAC path is **opt-in** (`dpo_pay_webhook_secret` empty by default).
- **OTP verify** uses DB equality on hash (no `secrets.compare_digest` on mismatch path) — enumeration/timing residual risk.
- **Frontend API base URL** still falls back to `http://localhost:8000` in `api.ts` and several server routes if env is missing at build time.
- **CI gaps:** no deploy workflow, drift guards need live Supabase secrets, 2 backend test failures observed in cloud VM, `pywebpush` not in default CI install path for all test modules.

### Launch blockers (do not skip)

1. Prove **Lenco + DPO webhooks** end-to-end on staging with signature verification enabled (`LENCO_VERIFY_SIGNATURES=true`).
2. **Rotate** any credentials ever committed; verify Supabase service role not exposed via anon key misuse.
3. **Staging migration dry-run** — resolve `063` duplicate prefix; run `059_audit_idempotent` checks.
4. **WAHA session health** monitoring + runbook tested (OTP is login).
5. **Legal/consent** flows visible in UI (footer links exist; confirm production content matches seeded docs).
6. Fix **CI red** if drift guards or tests fail on `master`.

---

## Gap vs attached task matrices

Many CSV rows marked **Missing** are now **implemented or partial**. Re-baseline your tracker:

| CSV claim | Verified state (2026-05-28) |
|-----------|------------------------------|
| deep-enrich 405 | **Resolved** — `POST /api/v1/jobs/deep-enrich-tick` + tests |
| Lenco webhook missing | **Implemented** — `webhooks.py` + `lenco_webhook.py` + tests |
| Webhook HMAC missing | **Partial** — Lenco full; DPO token + optional HMAC |
| OTP brute force | **Partial** — rate limit + `attempts` increment; not timing-safe compare |
| RLS on aux tables | **Partial** — `040` + later tables; verify live with `schema_guard_rls()` |
| Bwana static mock | **Resolved** — `POST /api/v1/bwana/chat` + FAQ/LLM/escalation |
| Resend OTP broken | **Resolved** — `AuthPageClient` calls `auth.requestOTP` on resend |
| Apply Now dead | **Resolved** — `ApplyModal` on matches + job detail |
| Vitest missing | **Resolved** — 45 files, coverage gate in CI |
| Legal placeholders | **Resolved** — `063_seed_legal_docs.sql` + frontend routes |
| ai_cache bypass | **Partial** — wired in cv_parser, embeddings, job_extractor, bwana |
| HNSW missing | **Resolved** — migration `066` |
| Account deletion | **Resolved** — `DELETE /profile` + cascade |
| JSON-LD / sitemap | **Resolved** — `job-posting-jsonld.ts`, `sitemap.ts` |
| Staging env | **Still missing** |
| Automated backups | **Still missing** in repo |
| Meta WhatsApp API | **Still missing** (WAHA remains) |
| Employer portal | **Partial** — backend `employers.py` + migration `076`; B2B UI maturity unknown |

---

## Architecture & code quality

| Area | Status | Notes |
|------|--------|-------|
| Monorepo layout | Good | `apps/backend`, `apps/frontend`, `packages/*`, `infra/*`, `docs/` |
| Separation of concerns | Good | Routes thin; services for AI, matching, payments |
| Modularity | Good | Deep-link parsers split; admin sub-routers |
| File size discipline | Mixed | Some routes/services approach 300+ lines — watch `admin.py`, `jobs.py` |
| Typing (TS) | Good | No `any` abuse in `api.ts`; OpenAPI guard with small allowlist |
| Dead code / duplication | Low–medium | Legacy deep-link parser file coexists with package |
| Async handling | Good | BackgroundTasks for match-after-upload, welcome email |
| Error handling | Good | RFC 7807-style `ProblemHTTPException`, Sentry hooks |
| Circular deps | Not flagged | — |

**Fragile areas:** payment webhooks, WAHA session, embedding model changes, migration ordering.

**Over-engineered:** multiple CI guards (good for quality, ops cost).

**Under-engineered:** job queue/workers for match batch at scale; Redis optional for rate limits only.

---

## Production infrastructure

| Capability | Status |
|------------|--------|
| Docker / compose prod | Partial — `infra/production/docker-compose.prod.yml`; WAHA unpinned `latest` |
| Kubernetes | Missing |
| CI (test + build) | Ready — `.github/workflows/ci.yml`, `frontend_tests.yml` |
| CI (deploy) | Missing |
| Staging | Missing |
| Secrets in code | Policy good; **rotation unverifiable** from repo |
| Backups | Documented only |
| Rollback | Manual (docker recreate / Vercel promote) |
| Monitoring | Partial — Sentry, `/health`, `llm_usage_log`; no UptimeRobot in repo |
| Logging | Partial — structured request IDs; no centralized log stack in repo |
| Rate limiting | Ready — SlowAPI + optional Redis |
| CDN | Vercel edge (frontend) |
| Job workers | Partial — n8n + FastAPI BackgroundTasks, not dedicated queue |
| Horizontal scaling | Poor — in-memory rate limits without Redis; single WAHA |
| DB indexing | Good — HNSW `066`, job indexes |
| Migration safety | Partial — audit migration; **063 duplicate prefix risk** |
| SSR/CSR | Next 14 App Router, `standalone` output |
| Build optimization | Partial — `optimizePackageImports`, PWA |

---

## Security snapshot

See `SECURITY_AUDIT.md` for prioritized findings.

---

## Performance & scale (realistic)

| Load | Likely behavior |
|------|-----------------|
| **100 users** | Fine on free tiers if WAHA stable |
| **1,000 users** | Gemini/WAHA cost and rate limits become painful; match RPC + sync decrements stress Supabase |
| **10,000+ users** | **Will break** without batch match workers, Redis rate limits, WAHA replacement, Supabase plan upgrade |

---

## AI system readiness

| Item | Status |
|------|--------|
| Prompt structure / caching | Partial — system-first patterns; `ai_cache` |
| Cost optimization | Partial — cache + `llm_usage_log`; no budget alerts in repo |
| Validation | Good for CV parse; job extractor uses Pydantic |
| Prompt injection | Partial — user CV text in prompts; no dedicated sanitizer |
| Fallback providers | Partial — OpenRouter primary; degraded paths in retry lib |
| Abuse prevention | Partial — rate limits; no per-user AI quotas in all routes |
| Observability | Partial — Sentry + DB log table |

---

## UI/UX & product

- **Polished design system** and responsive layouts present.
- **Apply flow** in-app modal — good for mobile.
- **Admin guard** client-side only for UX; backend enforces roles (defense in depth OK if all admin routes use `require_admin`).
- **PWA** configured; production Lighthouse not gated in CI.
- **Employer portal** — backend exists; treat B2B as beta until UX/billing proven.

---

## Reliability

- Graceful CV upload queue on Gemini failure — **yes**
- WAHA degradation — **503 on OTP** (documented in AGENTS.md)
- Transactional consistency — **mostly** via Supabase; no distributed transactions for payment + tier
- Race conditions — possible on concurrent webhook delivery (idempotency keys should be verified per webhook handler)

---

## Recommended priority order

1. Staging + migration proof  
2. Payments webhooks smoke + idempotency  
3. Secret rotation + RLS live audit  
4. WAHA reliability / email OTP fallback  
5. Remove localhost fallback; fail build on missing API URL  
6. Ops: backups, uptime alerts, deploy automation  
7. Scale: Redis rate limits, match batch workers  

---

*This document should be updated after each production cutover.*
