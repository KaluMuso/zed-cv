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
RESEND_FROM_EMAIL="Zed CV <info@vergeo.company>"
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

### Updating the App

> **Production reality note (2026-05-17):**
> The runbook above assumes the compose stack lives in `~/zedcv/infra/production/`. The current OCI box actually runs the stack from `~/n8n-docker/` (the n8n compose stack was extended to include `zedcv-backend` rather than spinning up a second project). Source still lives in `~/zedcv/`. Until the layouts re-converge, use the actual paths below.

**Actual prod redeploy commands (as run today):**

```bash
ssh ubuntu@YOUR_SERVER_IP

# 1. Pull source
cd ~/zedcv && git pull origin master

# 2. Rebuild + restart only the backend service. ~/n8n-docker/docker-compose.yml
#    references ../zedcv as the build context, so step 1's pull is what
#    actually changes the container contents — step 2 rebuilds the image.
cd ~/n8n-docker
docker compose build zedcv-backend
docker compose up -d --force-recreate zedcv-backend
```

**Greenfield runbook (the repo's documented path — kept for reference):**

```bash
cd ~/zedcv/infra/production
docker compose -f docker-compose.prod.yml up -d --build
```

If you're standing up a new prod box, prefer the greenfield path so you stay in lockstep with the checked-in compose files. If you're maintaining the current OCI box, use the actual-prod commands above.

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

**If `docker compose up` fails with `key cannot contain a space` on `.env` line N**, quote
values that contain spaces (common culprit: `RESEND_FROM_EMAIL`):

```bash
# Wrong — docker compose env_file parser rejects unquoted spaces
RESEND_FROM_EMAIL=Zed CV <info@vergeo.company>

# Correct
RESEND_FROM_EMAIL="Zed CV <info@vergeo.company>"
```

**If `git pull` aborts on local Dockerfile/requirements.txt changes**, either stash or
discard before rebuilding (the image is built from `~/zedcv/apps/backend` on disk):

```bash
cd ~/zedcv
git diff apps/backend/Dockerfile apps/backend/requirements.txt
git checkout -- apps/backend/Dockerfile apps/backend/requirements.txt   # discard local edits
git pull origin master
grep trigger-renewal-reminders apps/backend/app/api/v1/admin_ingest.py  # must match
```

Wave 1 renewal cron sanity check:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  https://api.zedapply.com/api/v1/admin/trigger-renewal-reminders
# 401 = route exists (good). 404 = still on pre-#174 image — pull + rebuild again.
```

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
