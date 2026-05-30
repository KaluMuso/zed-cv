# Zed CV — Deployment Runbook

Complete step-by-step guide to deploy Zed CV from scratch. Budget: ~$30/month.

---

## Architecture Overview

```
Users ──→ zedcv.com (Vercel, free) ──→ api.zedcv.com (Oracle Cloud, free)
                                            ├── FastAPI backend (Docker)
                                            ├── WAHA WhatsApp API (Docker)
                                            └── n8n job scraper (Docker)
                                        ↕
                                   Supabase (free tier)
                                   + pgvector 768-dim embeddings
```

**AI Stack:** Gemini text-embedding-004 (free) + Gemini Flash 2.0 via OpenRouter (~$0.10/M tokens)
**Payments:** DPO Pay (mobile money) + Lenco (ready when configured)

---

## Phase 1: Gather Credentials

You need 5 sets of credentials before deploying. Collect them all first.

### 1.1 Supabase Keys

Your project already exists at `chnesgmcuxyhwhzomdov.supabase.co`.

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project → **Settings** → **API**
3. Copy:
   - **URL** (already set: `https://chnesgmcuxyhwhzomdov.supabase.co`)
   - **service_role key** → `SUPABASE_KEY` (keep this secret!)

### 1.2 Gemini API Key (Embeddings — FREE)

Used for generating CV/job embeddings via text-embedding-004. Free tier: 1,500 requests/min.

1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Create a new key → `GEMINI_API_KEY`

### 1.3 OpenRouter API Key (LLM)

Used for CV parsing and cover letter generation via Gemini Flash 2.0.

1. Go to [openrouter.ai/keys](https://openrouter.ai/keys)
2. Create a new key → `OPENROUTER_API_KEY`
3. Add $5-10 credits (Gemini Flash is ~$0.10/M tokens — very cheap)

### 1.4 DPO Pay Merchant Account

Used for MTN/Airtel mobile money payments in ZMW.

1. Go to [directpay.com](https://www.directpay.com/) → Apply for Merchant Account
2. Select **Zambia** as your country
3. After approval, from your merchant dashboard:
   - **Company Token** → `DPO_PAY_COMPANY_TOKEN`
   - **Service Type** → `DPO_PAY_SERVICE_TYPE`
4. Set your webhook URL to: `https://api.zedcv.com/api/v1/webhooks/dpo`

> **Note:** DPO Pay approval takes 2-5 business days. The app works without it — payments just won't process until configured.

### 1.5 Generate JWT Secret + WAHA Key (Windows)

Open **PowerShell** on your Windows machine and run:

```powershell
# JWT Secret (64 hex chars)
python -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))"

# WAHA API Key (32 hex chars)
python -c "import secrets; print('WAHA_API_KEY=' + secrets.token_hex(16))"
```

If Python isn't installed, use this alternative:

```powershell
# PowerShell-native method
$jwt = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
$waha = -join ((1..32) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
Write-Host "JWT_SECRET=$jwt"
Write-Host "WAHA_API_KEY=$waha"
```

### 1.6 Resend (Email OTP + Digests)

Transactional email (OTP, match digests, contact form) goes through [Resend](https://resend.com).

1. Create an API key → `RESEND_API_KEY`
2. In Resend → **Domains**, add **vergeo.company** and publish the DNS records (SPF, DKIM, DMARC) at your DNS host
3. Wait until the dashboard shows **verified** (do not use `zedcv.com` until it is verified there too)
4. Set on the backend (OCI `apps/backend/.env` and Vercel if applicable):

```bash
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=Zed CV <info@vergeo.company>
```

**Verify:** `curl -s -H "X-Admin-Key: $ADMIN_API_KEY" https://api.zedcv.com/api/v1/admin/email-health | jq .domain_verified` → `true`

See `AGENTS.md` §3.8 if email OTP returns 503.

---

## Phase 2: Push to GitHub

### 2.1 Create the Repository

1. Go to [github.com/new](https://github.com/new)
2. Name: `zed-cv`, Private, no README (we have one)
3. From your Windows machine (in the project folder):

```powershell
cd "Zed CV\zed-cv"
git init
git add -A
git commit -m "Initial commit: Zed CV platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/zed-cv.git
git push -u origin main
```

---

## Phase 3: Deploy Backend (Oracle Cloud Free Tier)

### 3.1 Create Oracle Cloud Instance

1. Sign up at [cloud.oracle.com](https://cloud.oracle.com/) (Always Free tier)
2. Create a **Compute Instance**:
   - Shape: **VM.Standard.A1.Flex** (ARM) — 4 OCPU, 24 GB RAM (free!)
   - Image: **Ubuntu 22.04**
   - Add your SSH key
3. Note the **Public IP address**

### 3.2 Configure Security Lists

In Oracle Cloud Console → Networking → Virtual Cloud Networks → Your VCN → Security Lists:

Add **Ingress Rules**:

| Port | Protocol | Source    | Purpose       |
|------|----------|-----------|---------------|
| 80   | TCP      | 0.0.0.0/0 | HTTP (redirect) |
| 443  | TCP      | 0.0.0.0/0 | HTTPS (API)   |
| 5678 | TCP      | Your IP   | n8n admin     |

### 3.3 Set Up the Server

```bash
ssh ubuntu@YOUR_SERVER_IP

git clone https://github.com/YOUR_USERNAME/zed-cv.git ~/zedcv
cd ~/zedcv
chmod +x infra/production/oracle-cloud-setup.sh
./infra/production/oracle-cloud-setup.sh

# Log out and back in (for Docker group)
exit
ssh ubuntu@YOUR_SERVER_IP
```

### 3.4 Configure Environment

```bash
cd ~/zedcv
cp apps/backend/.env.production.example apps/backend/.env
nano apps/backend/.env
```

Fill in ALL credentials from Phase 1. **Important:** set `SUPERADMIN_PHONE` to your +260 number for unrestricted access.

### 3.5 Point Your Domain

Create DNS A records:
- `api.zedcv.com` → `YOUR_SERVER_IP`

Wait 5-10 minutes, then verify: `dig api.zedcv.com`

### 3.6 Set Up SSL

```bash
cd ~/zedcv/infra/production
chmod +x setup-ssl.sh
./setup-ssl.sh api.zedcv.com your@email.com
```

### 3.7 Launch Everything

```bash
cd ~/zedcv/infra/production

# Create the compose-level .env (separate from apps/backend/.env — docker
# compose only reads .env in the same directory as the compose file).
cp .env.example .env
nano .env   # fill in real values:
            #   WAHA_API_KEY=<key from Phase 1>
            #   N8N_USER=admin
            #   N8N_PASSWORD=<strong password>
            #   SUPABASE_URL=https://chnesgmcuxyhwhzomdov.supabase.co
            #   SUPABASE_KEY=<service role key>

docker compose -f docker-compose.prod.yml up -d --build
```

### 3.8 Verify

```bash
curl https://api.zedcv.com/api/v1/health
```

Expected: `{"status": "healthy", "version": "0.1.0", "supabase": true, "waha": true}`

### 3.9 Connect WhatsApp

1. Open WAHA admin: `http://YOUR_SERVER_IP:3001`
2. Start a new session → Scan the QR code with your WhatsApp Business number
3. Test: Send "hi" to your WhatsApp number → should get the welcome message

---

## Phase 4: Deploy Frontend (Vercel)

### 4.1 Import Project

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your `zed-cv` GitHub repo
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `apps/frontend`

### 4.2 Set Environment Variables

In Vercel Dashboard → Your Project → **Settings** → **Environment Variables**:

| Variable                        | Value                                               |
|---------------------------------|-----------------------------------------------------|
| `NEXT_PUBLIC_API_URL`           | `https://api.zedcv.com/api/v1`                     |
| `NEXT_PUBLIC_SUPABASE_URL`      | `https://chnesgmcuxyhwhzomdov.supabase.co`         |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Your Supabase anon key                              |

### 4.3 Deploy

Click **Deploy**. Your site will be live at `https://zedcv.vercel.app`.

---

## Phase 5: Post-Deploy Checklist

- [ ] `https://api.zedcv.com/api/v1/health` returns healthy
- [ ] `https://zedcv.vercel.app` loads the homepage
- [ ] Register via WhatsApp OTP (your superadmin phone)
- [ ] Confirm you got superadmin role (unlimited matches, cover letters)
- [ ] Upload a test CV (PDF, under 5MB)
- [ ] View job listings
- [ ] Trigger matching (should bypass quota for you)
- [ ] Generate a cover letter (should bypass Bwino tier check for you)
- [ ] (After DPO Pay approval) Test payment flow

---

## Superadmin Access

Your phone number (set via `SUPERADMIN_PHONE` env var) gets:
- **Unlimited matches** — no monthly quota
- **All features unlocked** — cover letters, etc. regardless of tier
- **Bwino tier auto-assigned** on first registration

To add more admins later, update the `role` column in the `users` table:
```sql
UPDATE users SET role = 'superadmin' WHERE phone = '+260XXXXXXXXX';
```

---

## Maintenance

### OCI production redeploy runbook (`ubuntu@OCI`)

Use this after every merge to `master` that touches the backend (including **pywebpush** / Web Push, **WeasyPrint** PDF libs in the Dockerfile, **Lenco** webhook fixes, or any `apps/backend/.env` change).

**Layout on the live box:**

| Path | Role |
|------|------|
| `~/zedcv/` | Git clone — source for `docker compose build` |
| `~/n8n-docker/` | Compose project — `zedcv-backend`, WAHA, n8n |
| `~/zedcv/apps/backend/.env` | Backend secrets (mounted via compose `env_file`) |

**Critical:** `docker compose restart` does **not** reload `.env` or pick up new code. You must **`build`** then **`up -d --force-recreate`**.

#### 1. Copy-paste deploy sequence

```bash
# From your laptop (or any machine with SSH access)
ssh ubuntu@YOUR_OCI_PUBLIC_IP

# 0. (Optional) If you edited secrets on the host — edit BEFORE recreate:
#    nano ~/zedcv/apps/backend/.env
#    Required for a full-green deploy: DEBUG=false, REDIS_URL, RESEND_API_KEY,
#    RESEND_FROM_EMAIL, VAPID_* (if push enabled), Lenco prod keys (#172+).

# 1. Pull latest backend source
cd ~/zedcv && git pull origin master

# 2. Rebuild image + recreate container (re-reads .env)
cd ~/n8n-docker
docker compose build zedcv-backend
docker compose up -d --force-recreate zedcv-backend

# 3. Production readiness audit — FULL (needs Supabase + WAHA from container .env)
docker exec zedcv-backend python scripts/production_readiness_audit.py
# Expect exit code 0 (no red checks). Re-run after fixing .env / WAHA / migrations.

# 4. Public health check
curl -s https://api.zedapply.com/api/v1/health | jq .

# 5. Confirm integration flags match .env (see table below)
#    redis_configured  ← non-empty REDIS_URL in container
#    vapid_configured  ← VAPID_PRIVATE_KEY + VAPID_PUBLIC_KEY + VAPID_CLAIMS_EMAIL
#    resend_configured ← non-empty RESEND_API_KEY
```

**If the image still looks stale** (missing scripts, old code paths):

```bash
cd ~/n8n-docker
docker compose build --no-cache zedcv-backend
docker compose up -d --force-recreate zedcv-backend
```

#### 2. Expected healthy `/health` JSON

When Supabase and WAHA are both up:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "supabase": true,
  "waha": true,
  "redis_configured": true,
  "vapid_configured": true,
  "resend_configured": true
}
```

| Field | `true` when | Notes |
|-------|-------------|--------|
| `status` | `healthy` | `supabase` **and** `waha` both true |
| `status` | `degraded` | Supabase OK, WAHA down — OTP/digests fail until WAHA fixed |
| `status` | `unhealthy` | Supabase heartbeat RPC failed |
| `redis_configured` | `REDIS_URL` set in container env | Shared rate limits across workers / recreates |
| `vapid_configured` | All three VAPID vars set | Matches `vapid_configured()` in `web_push.py` |
| `resend_configured` | `RESEND_API_KEY` non-empty | Email OTP/digests; also verify domain via `/admin/email-health` |

`version` comes from `APP_VERSION` / settings — value may differ from the example.

#### 3. `production_readiness_audit.py` — expected results

Run **inside** the container (not host `python3` — host Python lacks `pydantic`, `pywebpush`, etc.).

**Green (required for go-live):**

| Check | Meaning |
|-------|---------|
| `DEBUG=false` | Production mode |
| `LENCO_API_URL (production)` | Host contains `api.lenco.co` |
| `LENCO_API_KEY set` | Key present (post–#172 cutover) |
| `SENTRY_DSN set` | Error tracking wired |
| `REDIS_URL set` | Recommended — shared rate limits |
| `Migrations on disk` | SQL files visible (yellow OK in slim image if DB probes pass) |
| `DB schema sentinels` | Migrations through latest applied on Supabase |
| `tier_config rows` | All four consumer tiers present |
| `Active jobs have apply path` | No active jobs missing `apply_url` / `apply_email` |
| `RLS on 10 audited tables` | `schema_guard_rls` RPC passes |
| `WAHA session WORKING` | At least one session in `WORKING` state |

**Yellow (acceptable short-term, fix before marketing push):**

| Check | Meaning |
|-------|---------|
| `LENCO_API_URL` still `sandbox.lenco.co` | Sandbox payments only |
| `LENCO_API_KEY set` empty | Lenco disabled until key added |
| `SENTRY_DSN set` empty | No Sentry (local/dev only) |
| `REDIS_URL set` empty | In-memory rate limits — reset on recreate |
| `Migrations on disk` yellow | Container has no `infra/supabase/migrations` — rely on DB probes |
| `Supabase checks` skipped | Only when `--skip-db` — **do not use for prod deploy** |

**Red (block deploy / fix before taking payments):**

| Check | Action |
|-------|--------|
| `DEBUG=true` | Set `DEBUG=false` in `.env`, force-recreate |
| `DB schema sentinels` missing columns | Apply pending migrations in Supabase |
| `tier_config rows` missing tiers | Seed/fix `tier_config` |
| `Active jobs have apply path` | Run backfills or deactivate bad jobs |
| `RLS on 10 audited tables` | Apply migration 043+ / fix RLS |
| `WAHA session WORKING` | See WAHA recovery below |

Exit code: **0** if no red; **1** if any red.

#### 4. Ops scripts — always via `docker exec`

Do **not** run `python3 scripts/...` on the Ubuntu host unless you have a venv with `requirements.txt` installed. On OCI, host Python often fails with missing `pydantic` / deps.

```bash
# Audit (full)
docker exec zedcv-backend python scripts/production_readiness_audit.py

# Backfills — dry-run first, then --apply where supported
# Apply URL v2: default is dry-run (no flag). Full runbook: docs/APPLY_URL_BACKFILL_V2_RUNBOOK.md
docker exec -it zedcv-backend python scripts/backfill_apply_urls_v2.py
# docker exec -it zedcv-backend python scripts/backfill_apply_urls_v2.py --apply
docker exec zedcv-backend python scripts/backfill_job_quality.py --dry-run
docker exec zedcv-backend python scripts/backfill_job_enrichment.py --dry-run
```

#### 5. WAHA recovery when `"waha": false`

1. Check WAHA container: `cd ~/n8n-docker && docker compose logs waha --tail 50`
2. Bootstrap session (admin key from `~/zedcv/apps/backend/.env` → `ADMIN_API_KEY`):

```bash
curl -sS -X POST "https://api.zedapply.com/api/v1/admin/waha/bootstrap-session?session=default&timeout=45" \
  -H "X-ADMIN-API-KEY: $ADMIN_API_KEY" | jq .
```

3. Re-check health: `curl -s https://api.zedapply.com/api/v1/health | jq .waha`
4. If still false: scan QR at WAHA dashboard (`https://waha.vergeo.company`) or restart backend (startup hook re-runs bootstrap):

```bash
cd ~/n8n-docker && docker compose restart zedcv-backend
```

See `AGENTS.md` §3.3 for full WAHA failure-mode notes. Session files: `/home/ubuntu/n8n-docker/waha_data/sessions`.

#### 6. Rollback

```bash
ssh ubuntu@YOUR_OCI_PUBLIC_IP

# Record current SHA before deploy (for rollback target)
cd ~/zedcv && git rev-parse HEAD

# Roll back source to previous known-good commit
cd ~/zedcv && git fetch origin master && git checkout <previous-sha>

# Rebuild + recreate on the old code
cd ~/n8n-docker
docker compose build zedcv-backend
docker compose up -d --force-recreate zedcv-backend

# Verify
docker exec zedcv-backend python scripts/production_readiness_audit.py
curl -s https://api.zedapply.com/api/v1/health | jq .
```

- **`.env` rollback:** restore `apps/backend/.env` from backup, then `force-recreate` only (no git change).
- **Supabase:** do **not** revert applied migrations — forward-fix with a new migration.
- **Vercel frontend:** promote previous deployment in the Vercel dashboard if the release included frontend changes.

---

### Updating the App (short reference)

> **Production reality:** stack runs from `~/n8n-docker/`; source in `~/zedcv/`. Full steps: [OCI production redeploy runbook](#oci-production-redeploy-runbook-ubuntuoci) above.

```bash
cd ~/zedcv && git pull origin master
cd ~/n8n-docker && docker compose build zedcv-backend && docker compose up -d --force-recreate zedcv-backend
docker exec zedcv-backend python scripts/production_readiness_audit.py
curl -s https://api.zedapply.com/api/v1/health | jq .
```

**Greenfield runbook** (new VM, not the current OCI box):

```bash
cd ~/zedcv/infra/production
docker compose -f docker-compose.prod.yml up -d --build
```

### Viewing Logs

```bash
# On the current OCI box:
cd ~/n8n-docker && docker compose logs zedcv-backend --tail 100 -f

# On a greenfield deploy:
cd ~/zedcv/infra/production && docker compose -f docker-compose.prod.yml logs backend --tail 100 -f
```

### Sanity-check after a backend update

```bash
# Verify the running container is on the expected commit (image was rebuilt)
docker compose exec zedcv-backend grep -c resolve_skill_ids /app/app/api/v1/cv.py
# Should print >= 1 once Phase 2 Initiative #1 (semantic skill resolver) is in master.

# Track 4a (scraper LLM enrichment) — both must pass after PR #47+ is deployed:
docker compose exec zedcv-backend grep -c enrich_job /app/app/api/v1/jobs.py
# >= 1
docker compose exec zedcv-backend test -f /app/scripts/backfill_job_enrichment.py && echo ok
# prints "ok"

# Verify health endpoint
curl -fsS https://api.zedcv.com/api/v1/health
```

**If `grep enrich_job` prints 0 or the backfill script is missing**, the container is still on an old image. On the OCI box you must pull source *and* rebuild — `docker compose restart` is not enough:

```bash
cd ~/zedcv && git pull origin master
cd ~/n8n-docker
docker compose build --no-cache zedcv-backend
docker compose up -d --force-recreate zedcv-backend
```

Then re-run the sanity checks above before running the backfill dry-run.

---

## Cost Breakdown

| Service         | Monthly Cost | Notes                           |
|-----------------|-------------:|----------------------------------|
| Oracle Cloud    |          $0  | Always Free ARM instance         |
| Vercel          |          $0  | Free tier (100GB bandwidth)      |
| Supabase        |          $0  | Free tier (500MB DB, 1GB storage)|
| Gemini Embed    |          $0  | Free tier (1,500 req/min)        |
| OpenRouter      |        ~$2   | Gemini Flash 2.0 for LLM        |
| Domain          |       ~$12/yr| .com domain                      |
| DPO Pay         |    per-txn   | ~2.5% per payment                |
| **Total**       |    **~$3/mo**| Well under $30 budget            |
