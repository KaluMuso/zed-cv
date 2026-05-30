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
| Job scraper ingest | **Was hardcoded in live** `Send to Zed CV` node | Replace body with `api_key: $env.INGEST_API_KEY` per `job_scraper.json`; rotate ingest key if exposed in logs/git |

Bwana live workflow already uses `$env.OPENROUTER_API_KEY` and `$env.WAHA_API_KEY` (no literals in nodes). Job Scraper **must** be patched on n8n — live still had ingest key in JSON body at export time.

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
```

Gemini scraper nodes use n8n credential type **Google PaLM/Gemini API** (`googlePalmApi`), not env vars.

## Import any workflow JSON

1. n8n UI → **Workflows** → **Import from File**
2. Map credentials (Gemini on scraper nodes)
3. Confirm env vars
4. Activate

Or use n8n MCP `create_workflow_from_code` / `update_workflow` after `validate_workflow`.
