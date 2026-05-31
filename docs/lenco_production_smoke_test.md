# Lenco production smoke test — ZedApply

One-page checklist for flipping Lenco from sandbox to production once Theresa
Yombwe (Lenco) sends production credentials. Complements
[`docs/lenco_production_cutover.md`](./lenco_production_cutover.md).

**Safety:** With this PR merged, the backend **refuses to start** in production
if signature verification is off or `LENCO_WEBHOOK_SECRET` is empty — forged
webhooks cannot upgrade accounts to `super_standard`.

---

## Prerequisites

- [ ] Production **API key** and **public key** (`pub-...`) received from Lenco
- [ ] Settlement account linked in Lenco dashboard
- [ ] Webhook URL set in Lenco dashboard:  
      `https://api.zedapply.com/api/v1/webhooks/lenco`
- [ ] Vercel production env ready (`NEXT_PUBLIC_LENCO_PUBLIC_KEY`, widget URL)

---

## Step 1 — Compute webhook secret

Lenco signs webhooks with HMAC-SHA512 over the **raw request body**. The HMAC
key is `sha256(LENCO_API_KEY)` (hex string), not the raw API key:

```bash
python3 - <<'PY'
import hashlib, os
api_key = os.environ["LENCO_API_KEY"]  # paste prod key for this one-off
print(hashlib.sha256(api_key.encode()).hexdigest())
PY
```

Store the output as `LENCO_WEBHOOK_SECRET` (same value as
`hashlib.sha256(LENCO_API_KEY.encode()).hexdigest()` in Python).

**Or:** copy the **Signature key** directly from Lenco Pay → APIs → ZedApply →
**Webhook** tab (it is the same derived value).

---

## Step 2 — Update OCI `.env` (all four Lenco values)

Confirm which file the container reads (usually `~/n8n-docker` compose `env_file`):

```bash
cd ~/n8n-docker
docker compose exec zedcv-backend env | grep LENCO
```

Set on the backend:

| Variable | Value |
|----------|-------|
| `LENCO_API_KEY` | `<production secret from Lenco>` |
| `LENCO_PUBLIC_KEY` | `<production pub-...>` |
| `LENCO_API_URL` | `https://api.lenco.co/access/v2` |
| `LENCO_WEBHOOK_SECRET` | `<sha256 hex from Step 1>` |
| `LENCO_ENVIRONMENT` | `production` |
| `LENCO_VERIFY_SIGNATURES` | `true` |

`LENCO_VERIFY_SIGNATURES=true` is the default in code; setting it explicitly
documents intent. Startup **asserts** all four credentials when
`LENCO_ENVIRONMENT=production`.

---

## Step 3 — Restart backend (fail-fast confirms safety)

```bash
cd ~/n8n-docker
docker compose up -d --force-recreate zedcv-backend
```

If misconfigured, the container exits immediately with one of:

- `Refusing to start: VERIFY_SIGNATURES must be true in production`
- `Refusing to start: WEBHOOK_SECRET must be set in production`
- `Refusing to start: LENCO_API_KEY must be set in production`
- `Refusing to start: LENCO_PUBLIC_KEY must be set in production`

Check logs:

```bash
docker compose logs zedcv-backend --tail 50
```

When healthy, `GET /api/v1/health` returns 200.

---

## Step 4 — Real K125 Starter payment smoke test

Use a private/incognito browser session. You will spend real money — refund in
Step 5.

- [ ] Redeploy Vercel frontend (uncheck build cache) with production Lenco keys
- [ ] Open [https://zedapply.com/pricing](https://zedapply.com/pricing)
- [ ] Sign in with a test account on **Free**, then choose **Starter (K125/mo)**
      (checkout shows K62.50 while the launch 50% promo is active — still maps to
      Starter tier after webhook)
- [ ] Complete MTN/Airtel mobile money with your PIN
- [ ] Confirm pricing page copy: Starter lists score breakdowns (not tailored CVs);
      Professional lists cover letters + tailored CVs
- [ ] Backend logs show Lenco webhook **without** `lenco_webhook_invalid_signature`:

  ```bash
  docker compose logs zedcv-backend --since 5m | grep -i lenco
  ```

- [ ] Sentry (if configured) shows `lenco.webhook` breadcrumbs with masked
      reference/amount (last 4 digits only)
- [ ] Supabase: user `subscription_tier` updated for the test account

---

## Step 5 — Refund test payment

- [ ] Refund the **K125** (or promo K62.50) test charge in the Lenco merchant dashboard
- [ ] Do not leave test revenue on the merchant account

---

## Rollback (sandbox)

Restore sandbox values in OCI `.env`:

```env
LENCO_ENVIRONMENT=sandbox
LENCO_VERIFY_SIGNATURES=false
LENCO_WEBHOOK_SECRET=
LENCO_API_URL=https://sandbox.lenco.co/access/v2
LENCO_API_KEY=<sandbox key>
LENCO_PUBLIC_KEY=<sandbox pub-...>
```

Then `docker compose up -d --force-recreate zedcv-backend`.

---

## Local verification (before deploy)

```bash
cd apps/backend
# Should refuse to start (import runs create_app() — expect AssertionError):
SUPABASE_URL=https://fake.supabase.co SUPABASE_KEY=fake GEMINI_API_KEY=fake JWT_SECRET=test \
  LENCO_ENVIRONMENT=production LENCO_WEBHOOK_SECRET= LENCO_API_KEY=key \
  LENCO_PUBLIC_KEY=pub python3 -c "import main"
# Expect: AssertionError: WEBHOOK_SECRET must be set in production

python3 -m pytest tests/test_lenco_production_hardening.py tests/test_lenco_webhook.py tests/test_lenco_payment_ref.py tests/test_webhooks.py -v
```

---

## Related

- [`docs/lenco_production_cutover.md`](./lenco_production_cutover.md) — full cutover runbook
- [`apps/backend/app/core/lenco_startup.py`](../apps/backend/app/core/lenco_startup.py) — startup assertions
- [`apps/backend/app/services/lenco_webhook.py`](../apps/backend/app/services/lenco_webhook.py) — HMAC verification
