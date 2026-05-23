# Lenco production cutover — ZedApply

Move Lenco payments from sandbox to production for [zedapply.com](https://zedapply.com).
This runbook is **Lenco-specific**. For email, Sentry, backups, and soft launch, see
[`docs/production_cutover.md`](./production_cutover.md).

**Scope of this doc:** Phases 1–4 are manual cutover steps Kaluba runs once production
credentials arrive. Phases 5–6 are pre-launch follow-ups (code + legal publish) tracked
in the same PR series — **not part of the env swap itself**.

Run the readiness audit before and after deploy:

```bash
cd apps/backend && python scripts/production_readiness_audit.py
```

Expect green on `LENCO_API_URL (production)` and `LENCO_API_KEY set` after Phase 2.

---

## Pre-flight verification (repo state — 2026-05-23)

Use this table to confirm the codebase is ready before touching production credentials.

| Item | Status | Notes |
|------|--------|-------|
| Lenco webhook route | Ready | `POST /api/v1/webhooks/lenco` in `apps/backend/app/api/v1/webhooks.py` |
| Payment verify route | Ready | `POST /api/v1/subscription/verify-payment` in `apps/backend/app/api/v1/subscription.py` |
| Frontend widget | Ready | `apps/frontend/src/app/pricing/page.tsx` reads `NEXT_PUBLIC_LENCO_*` |
| Sandbox defaults (dev) | Expected | Backend default `lenco_api_url` → `sandbox.lenco.co`; frontend widget → `pay.sandbox.lenco.co` |
| Webhook signature | Ready | HMAC uses `sha256(LENCO_API_KEY)` per `apps/backend/app/services/lenco_webhook.py` |
| Audit script | Ready | `scripts/production_readiness_audit.py` checks `LENCO_API_URL` + `LENCO_API_KEY` |
| Rate limiting (Phase 5) | Partial | `slowapi` wired globally; see Phase 5 for gaps vs launch target |
| Refund page (Phase 6) | Pending code | Source markdown in `docs/refund_policy.md`; `/legal/refunds` route not wired yet |

**OCI env file location:** Kaluba specified `/home/ubuntu/zedcv/apps/backend/.env`.
The live stack runs from `~/n8n-docker/` (see `DEPLOY.md`). Before Phase 2, confirm which
file the container reads:

```bash
cd ~/n8n-docker
docker compose exec zedcv-backend env | grep LENCO
```

Update whichever `.env` (or compose `env_file`) actually feeds `zedcv-backend`.

---

## PHASE 1 — Pre-cutover checklist (Kaluba, manual)

Complete before swapping any env vars.

- [ ] Email Theresa Yombwe (Lenco) at [support@lenco.co](mailto:support@lenco.co) with subject  
      **Production credentials request — ZedApply (zedapply.com)**
- [ ] Wait for Lenco to issue **production API key** + **public key** (`pub-...`)
- [ ] Verify settlement account is configured and has a bank account linked
- [ ] Confirm production widget URL is `https://pay.lenco.co/js/v1/inline.js`
- [ ] Set webhook URL in the Lenco dashboard to  
      `https://api.zedapply.com/api/v1/webhooks/lenco`

**While waiting:** keep sandbox keys in place; smoke tests against sandbox remain valid.

---

## PHASE 2 — Env var swap (~5 min)

### Vercel — project `zed-cv`

Dashboard → Settings → Environment Variables → **Production** (and Preview if desired):

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_LENCO_PUBLIC_KEY` | `<production pub-...>` (replace sandbox key) |
| `NEXT_PUBLIC_LENCO_WIDGET_URL` | `https://pay.lenco.co/js/v1/inline.js` |

Do **not** redeploy yet — batch with Phase 3 so frontend and backend flip together.

### OCI — backend `.env`

File: `/home/ubuntu/zedcv/apps/backend/.env` (confirm path via pre-flight above)

| Variable | Value |
|----------|-------|
| `LENCO_API_KEY` | `<production secret>` |
| `LENCO_API_URL` | `https://api.lenco.co/access/v2/` |
| `LENCO_PUBLIC_KEY` | `<production pub-...>` |

> Trailing slash on `LENCO_API_URL` is optional; the client normalises the base URL.

**Rollback:** restore sandbox values from your password manager / prior `.env` backup:

- `LENCO_API_URL=https://sandbox.lenco.co/access/v2`
- Sandbox `LENCO_API_KEY` + `pub-...`
- Vercel: `NEXT_PUBLIC_LENCO_WIDGET_URL=https://pay.sandbox.lenco.co/js/v1/inline.js`

---

## PHASE 3 — Deploy (~10 min)

### Vercel (frontend)

1. Deployments → **Redeploy** latest production build
2. **Uncheck** “Use existing Build Cache” (forces fresh `NEXT_PUBLIC_*` inline)

### OCI (backend)

```bash
cd /home/ubuntu/zedcv && git pull origin master
cd ~/n8n-docker && docker compose up -d --force-recreate zedcv-backend
```

If `requirements.txt` or the Dockerfile changed since last deploy, rebuild first:

```bash
cd ~/n8n-docker && docker compose build zedcv-backend
docker compose up -d --force-recreate zedcv-backend
```

### Verify env inside container

```bash
cd ~/n8n-docker
docker compose exec zedcv-backend env | grep LENCO
```

Expected:

- `LENCO_API_URL` contains `api.lenco.co`
- `LENCO_API_KEY` is non-empty (do not paste values into tickets/logs)
- `LENCO_PUBLIC_KEY` matches production `pub-...` if set in `.env`

### Verify audit (from OCI host or locally with prod `.env`)

```bash
cd /home/ubuntu/zedcv/apps/backend && python scripts/production_readiness_audit.py
```

---

## PHASE 4 — Smoke test (~15 min)

Use a **private/incognito** browser session. You will spend real money — refund in the last step.

- [ ] Open [https://zedapply.com/pricing](https://zedapply.com/pricing) (incognito)
- [ ] Click **Upgrade** on **Starter** (K125)
- [ ] Lenco widget openspace; title shows **Pay for ZedApply / K125**
- [ ] Enter your own MTN number; approve with real PIN
- [ ] Lenco merchant dashboard shows the successful collection
- [ ] Webhook fired on backend:

  ```bash
  cd ~/n8n-docker
  docker compose logs zedcv-backend --since 5m | grep -i lenco
  ```

  Look for `lenco_webhook` processing without signature errors.

- [ ] Subscription tier updated in Supabase:

  ```sql
  SELECT subscription_tier, subscription_started_at
  FROM users
  WHERE phone = '+260761359005';
  ```

  Expect `subscription_tier = 'starter'` and a recent `subscription_started_at`.

- [ ] **Refund K125** via Lenco dashboard (cleanup — do not leave test revenue)

**Failure cheatsheet**

| Symptom | Likely cause |
|---------|----------------|
| Widget does not open | Wrong `NEXT_PUBLIC_LENCO_PUBLIC_KEY` or stale Vercel build cache |
| Payment succeeds but tier unchanged | Webhook URL wrong, signature mismatch (`LENCO_API_KEY`), or verify-payment not called |
| 502 on verify-payment | `LENCO_API_URL` still sandbox while widget used production key |
| CORS error in browser | Usually masked 500 — `curl -i` the API route and read backend logs |

---

## PHASE 5 — Server-side rate limiting (CRITICAL before public launch)

**Status:** `slowapi` is already installed (`requirements.txt`) and registered in
`apps/backend/main.py`. Shared limiter: `apps/backend/app/core/rate_limit.py`.

### Already rate-limited (as of 2026-05-23)

| Route | Limit | File |
|-------|-------|------|
| `POST /auth/otp/request` | 3/minute | `apps/backend/app/api/v1/auth.py` |
| `POST /auth/otp/verify` | 10/minute | `apps/backend/app/api/v1/auth.py` (signup completes here) |
| `POST /subscription/verify-payment` | 10/minute | `apps/backend/app/api/v1/subscription.py` |
| `POST /interview-prep` (stub) | 10/minute | `apps/backend/app/api/v1/interview_prep.py` |
| `POST /interview-prep/generate` | 5/minute | `apps/backend/app/api/v1/interview_prep.py` |

There is no separate `/signup` route — new users are created on OTP verify.
There is no `/interview/mock/start` route — use `/interview-prep/generate` for LLM cost.

### Follow-up PR (before marketing launch)

1. Tighten `POST /subscription/verify-payment` to **5/minute** (currently 10/minute).
2. Add `apps/backend/tests/test_subscription_rate_limit.py` asserting 429 behaviour.
3. Set **`REDIS_URL`** on OCI (Upstash free tier) so limits survive
   `docker compose up -d --force-recreate`. Without Redis, limits reset on every
   container restart. Documented in `apps/backend/.env.example`; not injected by
   compose today — add to the backend env file manually.

Example target decorator (follow-up code change):

```python
from app.core.rate_limit import limiter

@router.post("/verify-payment")
@limiter.limit("5/minute")
async def verify_payment(request: Request, ...):
    ...
```

---

## PHASE 6 — Refund policy publish

**Source markdown:** [`docs/refund_policy.md`](./refund_policy.md)

**Publish target:** public page at `/legal/refunds`, editable from Admin → **Legal** tab.

**Blocker (follow-up PR):** the legal API slug whitelist is currently
`privacy | terms | cookies` only (`apps/backend/app/api/v1/legal.py`,
`apps/frontend/src/lib/api.ts`, `LegalTab.tsx`). Adding `refunds` requires:

1. Extend `LegalSlug` on backend + frontend
2. Add `apps/frontend/src/app/legal/refunds/page.tsx` (+ `_content.ts` fallback)
3. Add Refunds entry to `LegalTab.tsx` slug list
4. Admin → Legal → paste `refund_policy.md` body → Save
5. Align §5 in Terms (`apps/frontend/src/app/legal/terms/_content.ts`) or link to `/legal/refunds`

Until that ships, the refund rules in Terms §5 still reference the older 14-day
first-subscription guarantee — reconcile copy when publishing.

---

## Related docs

- [`docs/production_cutover.md`](./production_cutover.md) — full prod checklist (email, Sentry, DR)
- [`docs/refund_policy.md`](./refund_policy.md) — refund policy source for `/legal/refunds`
- [`DEPLOY.md`](../DEPLOY.md) — OCI deploy paths (`~/n8n-docker` vs `~/zedcv`)
- [`AGENTS.md`](../AGENTS.md) §3 — CORS-as-500, WAHA, matching failure modes
