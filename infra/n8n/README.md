# n8n workflow exports (ZedApply / Zed CV)

Sanitized JSON snapshots of production workflows on `https://automation.vergeo.company`. **Never commit API keys** — use n8n instance env vars and credentials.

## Live inventory (2026-05-30)

| Workflow | n8n ID | Active | Repo file |
| --- | --- | --- | --- |
| Supabase Heartbeat | `qA4Zi46MAWx3gTTL` | Yes | `heartbeat_workflow.json` |
| Daily Digest (Email + WhatsApp) | `j6U2CDRZi0FI5G32` | Yes | `daily_digest_dual_channel.json` |
| Notification Digest (Every 24h) | `MW5KETbBdrAOk04y` | **No** | `notification_digest_every_24h.json` |
| Bwana Chat Pipeline | `TPDJ5S1HaRKZTdb1` | Yes | `bwana_chat_pipeline.json` |
| Job Scraper | `rsgZLi6UAcC3lXvu` | Yes | `job_scraper.json` |
| Sentry → WhatsApp Alert | _(import from repo)_ | **No** | `sentry_whatsapp_alert.json` |

## Sentry → WhatsApp alerts (Wave A.1)

Forwards Sentry issue-alert webhooks to the operator via WAHA. Full setup and **test fire** steps: `docs/SENTRY_ALERTS.md`.

**Import / activate**

1. n8n → **Workflows** → **Import from File** → `sentry_whatsapp_alert.json`
2. Env: `WAHA_API_URL`, `WAHA_API_KEY`, `ADMIN_ALERT_PHONE` (+260 E.164)
3. **Activate** and copy the **production** webhook URL (`…/webhook/sentry-alert`)
4. Sentry → **Alerts** → create rule → action **Webhooks** → paste URL
5. Smoke: `curl -X POST …/webhook/sentry-alert` with sample JSON (see docs) or trigger a test error

## Uptime monitoring

UptimeRobot free-tier setup for `GET /api/v1/health`: `UPTIME_MONITORING.md` in this directory.

Expected JSON includes `"status": "healthy"`, `"supabase": true`, `"waha": true`, plus config flags `redis_configured`, `vapid_configured`, `resend_configured`, `sentry_configured`.

## Digest cron: which to keep?

**Keep active:** `ZedApply - Daily Digest (Email + WhatsApp)` (`j6U2CDRZi0FI5G32`)

- Schedule: `0 7 * * *` (07:00 server time — align TZ with CAT in n8n settings).
- Calls the canonical backend paths in `app/services/daily_digest.py`:
  - `POST /api/v1/admin/trigger-daily-digest-email` → `run_email_daily_digest`
  - `POST /api/v1/admin/trigger-daily-digest-whatsapp` → `run_whatsapp_daily_digest`
- Auth: `INGEST_API_KEY` header (see `admin_ingest.py`).

**Keep disabled:** `ZedApply — Notification Digest (Every 24h)` (`MW5KETbBdrAOk04y`)

- Calls `POST /api/v1/matches/send-notifications`, which uses `_send_due_digest` in `matches.py` (tier `last_notification_at` cadence, different message shape than the 07:00 daily digest).
- Running both risks duplicate WhatsApp/email for users with new credited matches.

Match cron (`bqBV6XNPu3z3Ikx5`) may still call `_send_due_digest` after auto-match; that is intentional and separate from the 07:00 batch.

## Supabase heartbeat

Required so Supabase free tier does not pause after 7 days idle (`AGENTS.md` invariant).

**Import / activate**

1. n8n → **Workflows** → **Import from File** → `heartbeat_workflow.json`
2. Set env: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_SERVICE_KEY`), `FASTAPI_URL`
3. **Activate** workflow (toggle on)
4. Smoke: run once manually; expect HTTP 200 from `POST …/rest/v1/rpc/heartbeat` and `GET …/api/v1/health`

Prod instance already has workflow `qA4Zi46MAWx3gTTL` active as of 2026-05-30.

**Duplicate:** `Zed CV - Supabase Heartbeat` (`Gun5al1RkCKPSlfW`) is also active and runs the same 6h schedule. Keep one (prefer `qA4Zi46MAWx3gTTL` + service role key) and **deactivate** the other to avoid redundant RPC calls.

## Bwana chat: backend vs n8n

**Recommended (OCI):** leave `BWANA_N8N_WEBHOOK_URL` empty in `apps/backend/.env` so FAQ, escalation, and LLM run **in-process** (`app/services/bwana_chat.py`). Escalation WAHA uses `bwana_platform_config.escalation_whatsapp_phone` (admin UI `/admin/bwana`). See `docs/BWANA_ADMIN.md`.

The n8n workflow `TPDJ5S1HaRKZTdb1` remains optional for legacy routing; escalation there still uses env `ADMIN_ALERT_PHONE`.

## Bwana chat: FAQ matching weights

Production RPC `match_jobs_for_user` (migration 060) uses **50% semantic / 20% skills / 15% experience / 10% location / 5% recency** (hard floor 35).

Repo export `bwana_chat_pipeline.json` uses these weights in:

- FAQ branch (`how does matching work` / `score`)
- OpenRouter system prompt

**Apply to live n8n**

1. Open workflow `TPDJ5S1HaRKZTdb1`
2. **FAQ and Escalation Router** → replace the `match`/`score` FAQ line with the string from the repo export
3. **OpenRouter Bwana LLM** → update system message `content` to match repo (50/20/15/10/5)
4. Save and publish

### Secret rotation checklist (human)

| Secret | Where | Action |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | n8n env + OpenRouter dashboard | Rotate key; update n8n env; revoke old key |
| `WAHA_API_KEY` | n8n env + WAHA container | Rotate; update n8n; restart WAHA if needed |
| `INGEST_API_KEY` | n8n env + `apps/backend/.env` on OCI | Generate new key; update both; `docker compose up -d --force-recreate zedcv-backend` |
| Job scraper ingest | **Was hardcoded in live** `Send to ZedApply` node | Replace body with `api_key: $env.INGEST_API_KEY` per `job_scraper.json`; rotate ingest key if exposed in logs/git |

Bwana live workflow already uses `$env.OPENROUTER_API_KEY` and `$env.WAHA_API_KEY` (no literals in nodes). Job Scraper **must** be patched on n8n — live still had ingest key in JSON body at export time.

### Job scraper 403 `PERMISSION_DENIED` (Google AI)

If **AI Parse \*** nodes return `Your project has been denied access`, the live workflow is still calling **Google AI Studio** (`generativelanguage.googleapis.com`) with a blocked project. Re-import repo `job_scraper.json`: all four **AI Parse** nodes now use **OpenRouter** (`OPENROUTER_API_KEY`), same as the backend.

### Send to ZedApply: 422 `api_key` Field required

**Symptom:** Normalize returns 50 jobs with valid `source_url`, but **Send to ZedApply** fails with HTTP 422 and `"loc":["body","api_key"],"msg":"Field required"`.

**Cause:** The Send node still uses `api_key: $json.ingestKey`, but **Normalize and Deduplicate** does not pass `ingestKey` on the item.

**Fix:** Paste latest `infra/n8n/snippets/normalize_and_deduplicate.js` into the **Normalize and Deduplicate** Code node (it reads `$env` in Code and outputs `fastapiUrl` + `ingestKey`). Then set **Send to ZedApply**:

1. **URL:** `={{ ($json.fastapiUrl || 'http://zedcv-backend:8000') + '/api/v1/jobs/ingest' }}`
2. **Body:** `={{ JSON.stringify({ jobs: $json.jobs, api_key: $json.ingestKey }) }}`

Parentheses around the base URL are **required** — without them, `$json.fastapiUrl || 'http://…' + '/api/v1/…'` short-circuits to bare `https://api.zedapply.com` (no path) and the HTTP node fails with “incorrect host”.

### `$env` red / `[access to env vars denied]` in HTTP Request nodes

**Symptom:** `$env.FASTAPI_URL` or `$env.INGEST_API_KEY` is red in **Send to ZedApply** with `[access to env vars denied]`.

**Cause:** Production n8n sets `N8N_BLOCK_ENV_ACCESS_IN_EXPRESSIONS=true` (or equivalent). **HTTP Request** parameter expressions cannot read `$env`; **Code** nodes still can.

**Fix (preferred on blocked instances):** **Normalize and Deduplicate** (Code node) copies env into the item:

```javascript
fastapiUrl: $env.FASTAPI_URL || 'http://zedcv-backend:8000',
ingestKey: $env.INGEST_API_KEY,
```

Downstream HTTP nodes use `$json.fastapiUrl` and `$json.ingestKey` (see repo `job_scraper.json`). **Deep Enrich After Ingest** uses `$('Normalize and Deduplicate').item.json.*` because it runs after Send.

**Alternative:** Set `N8N_BLOCK_ENV_ACCESS_IN_EXPRESSIONS=false` in the n8n container env and recreate the container — then `$env.*` works directly in HTTP nodes (trade-off: secrets visible in expression editor).

**Settings → Variables:** `FASTAPI_URL` and `INGEST_API_KEY` must still be set (same values as OCI `apps/backend/.env`). If n8n uses process env instead of Variables, set them in docker-compose for the n8n service.

After patch: **Save** → **Publish** → manual test. Expect HTTP 200 `{ "ingested": N, ... }`.

### Ingest HTTP 200 but every job `embedding_failed`

**Symptom:** **Send to ZedApply** returns 200 with `"ingested": 0` and `"errors": [{ "reason": "embedding_failed: …" }]`.

**Cause:** The backend still calls **direct Google Gemini** `embedContent` for each job. Your Google AI Studio project is **PERMISSION_DENIED** (same ban that broke the old scraper Gemini nodes). n8n OpenRouter works for LLM parsing, but **embeddings run inside `zedcv-backend`**, not in n8n.

**Fix on OCI (`~/n8n-docker`):**

1. Ensure `apps/backend/.env` (the file the backend container reads) includes:
   ```
   OPENROUTER_API_KEY=sk-or-...   # same key n8n uses for AI Parse
   EMBEDDING_VIA_OPENROUTER=true   # skip Gemini entirely (recommended)
   ```
2. Deploy backend code with OpenRouter embedding support (PR #224 branch or `master` after merge):
   ```bash
   # Repo clone on OCI is ~/zedcv (no hyphen) — NOT ~/zed-cv
   cd ~/zedcv && git pull origin master
   # Or, before merge: git pull origin cursor/fix-n8n-ingest-api-key-72f6

   cd ~/n8n-docker
   docker compose build --no-cache zedcv-backend
   docker compose up -d --force-recreate zedcv-backend
   ```
   **If `~/zedcv` does not exist:** clone once with
   `git clone https://github.com/KaluMuso/zed-cv.git ~/zedcv`, then ensure
   `docker-compose.yml` `build.context` points at `~/zedcv/apps/backend` (not a
   tiny vendored copy under `~/n8n-docker`). A ~10 KB build context means the
   image is stale — fix the context path before rebuilding.

3. Smoke — env vars alone are not enough; confirm the **code** is deployed:
   ```bash
   docker exec zedcv-backend grep -c _embed_via_openrouter /app/app/services/embedding.py
   # Must print >= 1. If 0, the container is still on pre-OpenRouter code.

   docker exec zedcv-backend printenv OPENROUTER_API_KEY EMBEDDING_VIA_OPENROUTER | head -2
   curl -s https://api.zedapply.com/api/v1/health | jq '{openrouter_configured, embedding_via_openrouter}'
   ```
   Expect `openrouter_configured: true`, `embedding_via_openrouter: true`, and
   `_embed_via_openrouter` present in the image.
4. Re-run the scraper. Expect `"ingested": N` with N > 0 (duplicates OK on re-run).

Without `EMBEDDING_VIA_OPENROUTER=true`, the backend auto-falls back to OpenRouter only **after** Gemini returns 403 **and** `OPENROUTER_API_KEY` is set. Setting the flag avoids the failed Gemini call on every job.

### Combine All Sources: jobs with `source_url: null`

OpenRouter can return valid `choices[0].message.content` while every job still has `source_url` / `apply_url` null and `posted_at` like `9h ago` or `Posted 19 hours ago`. **Prep \*** nodes extract `href` links into `extractedLinks` before HTML strip; **Normalize and Deduplicate** reads those links from each Prep node (by branch index) and fuzzy-matches titles to URLs when the LLM omitted `source_url`. It keeps per-job aggregator URLs (e.g. `gozambiajobs.com/jobs/123-slug`) and drops homepages only. It also converts relative `posted_at` to ISO `YYYY-MM-DD`.

**Source of truth:** `infra/n8n/snippets/normalize_and_deduplicate.js` — paste the full file into the n8n **Normalize and Deduplicate** Code node, or re-import `job_scraper.json` (the export embeds the same code).

### Post-ingest deep-enrich + review queue

After scraper ingest, jobs often land in the admin **review queue** (`is_review_required=true`) when apply path or closing date is missing. Two mechanisms clear that backlog:

1. **Backend (automatic):** `POST /api/v1/jobs/ingest` schedules `schedule_post_ingest_deep_enrich` (fire-and-forget, limit capped 10–80 from ingest count).
2. **n8n (explicit):** **Deep Enrich After Ingest** node POSTs `/api/v1/jobs/deep-enrich-tick?limit=80&include_review_queue=true` after **Send to ZedApply** (wired in repo `job_scraper.json`).

The 6h cron export `deep_enrich_cron_6h.json` uses the same `include_review_queue=true` query param. Deep-enrich fetches `source_url`, runs LLM extraction, splits multi-role listings, and re-runs review-state so rows can auto-activate when contacts and deadlines are found.

Re-import `job_scraper.json` after any change to Prep, Normalize, or Deep Enrich nodes.

## Job Scraper — patch live workflow (`rsgZLi6UAcC3lXvu`)

Repo export `job_scraper.json` is the source of truth. Live n8n must match it before the next scrape run.

1. Sign in to `https://automation.vergeo.company`.
2. **Workflows** → open **ZedApply Job Scraper** (ID `rsgZLi6UAcC3lXvu`).
3. **Settings → Variables**: `OPENROUTER_API_KEY` (required), optional `OPENROUTER_MODEL=google/gemini-2.5-flash`.
4. Re-import `infra/n8n/job_scraper.json` or update all four **AI Parse \*** nodes to POST `https://openrouter.ai/api/v1/chat/completions` with Bearer auth (remove **Google AI** credential).
3. Open the **Send to ZedApply** HTTP Request node.
4. Set **Method** `POST` and URL:
   `={{ ($json.fastapiUrl || 'http://zedcv-backend:8000') + '/api/v1/jobs/ingest' }}`
5. **Body** → JSON (expression mode):
   `={{ JSON.stringify({ jobs: $json.jobs, api_key: $json.ingestKey }) }}`
   Use `$json.*` not `$env.*` when `N8N_BLOCK_ENV_ACCESS_IN_EXPRESSIONS` is enabled (see troubleshooting above).
6. **Settings** → **Variables** (instance): confirm `INGEST_API_KEY` and `FASTAPI_URL` are set (same values as OCI `apps/backend/.env` ingest secret and public API base).
7. **Save** → **Publish** (activate if the toggle was off).
8. **Execute workflow** (manual test) → open the execution → **Send to ZedApply** should return HTTP 200 with `{ "ingested": … }` (zeros are OK on an empty scrape).
9. If the old ingest key ever appeared in git, n8n execution logs, or Slack: **rotate** `INGEST_API_KEY` on OCI and n8n, then `docker compose up -d --force-recreate zedcv-backend` (not `restart`).

Optional: re-import `job_scraper.json` via **Import from File** on a draft copy, diff nodes, then merge credential mappings — do not overwrite live credentials blindly.

### Duplicate Supabase heartbeat (`Gun5al1RkCKPSlfW`)

Two heartbeats were active on 2026-05-30. Keep **`qA4Zi46MAWx3gTTL`** (repo: `heartbeat_workflow.json`) and **deactivate** the duplicate:

1. **Workflows** → **Zed CV - Supabase Heartbeat** (ID `Gun5al1RkCKPSlfW`).
2. Toggle **Inactive** (unpublish).
3. Confirm **Supabase Heartbeat** (`qA4Zi46MAWx3gTTL`) stays **Active** with the 6h schedule.

No API access from this repo — ops performs the toggle in the n8n UI.

## Required n8n environment variables

```
FASTAPI_URL=https://api.zedapply.com   # or internal docker URL
INGEST_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
WAHA_API_URL=...
WAHA_API_KEY=...
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=google/gemini-2.0-flash-001
ADMIN_ALERT_PHONE=+260...
SENTRY_ALERT_WEBHOOK_PATH=sentry-alert
```

`SENTRY_ALERT_WEBHOOK_PATH` is informational — the path is fixed in `sentry_whatsapp_alert.json`. Sentry alert rules should target the n8n production webhook URL for that path.

Gemini scraper nodes use n8n credential type **Google PaLM/Gemini API** (`googlePalmApi`), not env vars.

## Import any workflow JSON

1. n8n UI → **Workflows** → **Import from File**
2. Map credentials (Gemini on scraper nodes)
3. Confirm env vars
4. Activate

Or use n8n MCP `create_workflow_from_code` / `update_workflow` after `validate_workflow`.
