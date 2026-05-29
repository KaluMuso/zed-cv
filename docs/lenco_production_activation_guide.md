# Lenco production activation — operator guide (ZedApply)

You are **Live** on Lenco Pay. Use this guide after merging
[`feat/lenco-prod-hardening`](https://github.com/KaluMuso/zed-cv/pull/160).

**Never paste API keys into tickets, chat, or git.** Store them in a password
manager and OCI/Vercel env only.

---

## What each tier unlocks in the app

| Tier | Price | Matches/mo | Web app features |
|------|-------|------------|------------------|
| **Free** | K0 | 3 (7 welcome bonus first 2 months) | Matches, CV upload, WhatsApp alerts, basic analysis |
| **Starter** | K125 | 50 | + AI tailored CVs, priority matching, score breakdowns |
| **Professional** | K250 | 125 | + Cover letters (`/cover-letter`), career insights |
| **Super Standard** | K500 | Unlimited | + Interview prep (`/interview-prep`) |

Usage is enforced server-side (`tier_gating.py`). Users see quota on
**Dashboard**, **Matches**, and **Settings → Billing**.

---

## Step 1 — Lenco dashboard (you, ~10 min)

From **Lenco Pay → APIs → ZedApply**:

### API Keys tab

1. Copy **API (secret) key** → `LENCO_API_KEY` (shown once — save immediately).
2. Copy **Public key** (`pub-...`) → `LENCO_PUBLIC_KEY` (backend) and
   `NEXT_PUBLIC_LENCO_PUBLIC_KEY` (Vercel).
3. Confirm **Base URL** is `https://api.lenco.co/access/v2`.

### Webhook tab

1. **Webhook URL:** `https://api.zedapply.com/api/v1/webhooks/lenco`
2. **Signature key:** copy the value shown → `LENCO_WEBHOOK_SECRET`  
   (This is Lenco’s `sha256(API key)` — you can also compute it; both must match.)
3. Click **Save changes**.

### Settlement

Confirm your settlement account / bank is linked under Lenco Pay → Accounts.

---

## Step 2 — Backend (OCI, ~5 min)

Edit the `.env` file your `zedcv-backend` container reads (usually via
`~/n8n-docker` compose):

```env
LENCO_ENVIRONMENT=production
LENCO_VERIFY_SIGNATURES=true
LENCO_API_KEY=<production secret>
LENCO_PUBLIC_KEY=pub-...
LENCO_API_URL=https://api.lenco.co/access/v2
LENCO_WEBHOOK_SECRET=<signature key from Webhook tab>
```

Deploy:

```bash
cd ~/n8n-docker
docker compose up -d --force-recreate zedcv-backend
docker compose logs zedcv-backend --tail 30
```

If misconfigured, the container **exits immediately** with a clear assertion
(`WEBHOOK_SECRET`, `VERIFY_SIGNATURES`, etc.).

Verify inside container:

```bash
docker compose exec zedcv-backend env | grep LENCO
curl -s https://api.zedapply.com/api/v1/health | jq .
```

---

## Step 3 — Frontend (Vercel, ~5 min)

Project **zed-cv** → Settings → Environment Variables → **Production**:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_LENCO_PUBLIC_KEY` | `pub-...` (production) |
| `NEXT_PUBLIC_LENCO_WIDGET_URL` | `https://pay.lenco.co/js/v1/inline.js` |

Redeploy production with **Use existing Build Cache unchecked**.

---

## Step 4 — n8n (verify, ~5 min)

No new payment workflow is required — webhooks hit FastAPI directly.

**Required (already in repo):**

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `ZedApply - Subscription Expiry Downgrade` | Daily 03:00 UTC | `downgrade_expired_subscriptions` RPC |
| Supabase heartbeat | Every 6h | Keeps free-tier DB alive |

**In n8n UI:**

1. Import/update from `infra/n8n/subscription_expiry_daily.json` if missing.
2. Set credentials: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.
3. Activate the workflow; run once manually and confirm HTTP 200.

**Optional follow-ups (not blocking go-live):**

- Renewal reminder email 3 days before `subscription_expires_at`
- Slack/WhatsApp alert if Lenco webhook 401 rate spikes (Sentry)

---

## Step 5 — Smoke test (real money, ~15 min)

See [`docs/lenco_production_smoke_test.md`](./lenco_production_smoke_test.md).

1. Incognito → [zedapply.com/pricing](https://zedapply.com/pricing)
2. Upgrade **Starter** (K125) with your MTN/Airtel number
3. Confirm:
   - Lenco dashboard shows collection
   - Backend logs: no `lenco_webhook_invalid_signature`
   - Supabase: `subscription_tier = starter`
   - **Settings → Billing:** invoice row → **View** → download / email
   - Dashboard shows plan + match usage
4. **Refund** test payment in Lenco dashboard

---

## Billing & monitoring (now in app)

| Feature | Where |
|---------|--------|
| Plan + usage | Dashboard, Matches quota bar, Settings → Billing |
| Invoices table + modal | Settings → Billing → View / Download / Email copy |
| Cancel at period end | Settings → Billing → Cancel at period end |
| Upgrade | Pricing page → Lenco widget |
| Downgrade | Cancel at period end, then choose lower tier on pricing after expiry |
| Admin revenue | Admin → Stats (`/admin/stats`) |
| LLM cost | Admin → LLM cost panel |
| Product analytics | `analytics_events` + `/analytics/events` |

Invoice email sends automatically on successful Lenco/DPO webhook; users can
resend from Billing.

---

## Rollback to sandbox

```env
LENCO_ENVIRONMENT=sandbox
LENCO_VERIFY_SIGNATURES=false
LENCO_WEBHOOK_SECRET=
LENCO_API_URL=https://sandbox.lenco.co/access/v2
```

Vercel: restore sandbox `pub-...` and `https://pay.sandbox.lenco.co/js/v1/inline.js`.

---

## Tests to run before/after deploy

```bash
# Backend
cd apps/backend
python3 -m pytest tests/test_lenco_production_hardening.py tests/test_lenco_webhook.py tests/test_invoice_billing.py -v

# Frontend
cd apps/frontend
npm test -- --run
npm run lint
```

---

## Related docs

- [`docs/lenco_production_smoke_test.md`](./lenco_production_smoke_test.md)
- [`docs/lenco_production_cutover.md`](./lenco_production_cutover.md)
- [`DEPLOY.md`](../DEPLOY.md)
