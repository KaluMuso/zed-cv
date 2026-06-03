# n8n digest deduplication (prod)

**Audit date:** 2026-06-03 · **Instance:** `https://automation.vergeo.company`

**Who runs this:** A human operator in the n8n UI. This runbook is **documentation + checklist only** — do **not** use n8n MCP `publish_workflow` or bulk API toggles without explicit maintainer approval.

**Goal:** One WhatsApp (and email) digest path per user per day. Legacy n8n workflows duplicate the canonical 07:00 batch and can send a second message the same day.

---

## Background — three digest code paths

| Path | Trigger | Backend entry | Dedup mechanism | Message shape |
|------|---------|---------------|-----------------|---------------|
| **Canonical daily batch** | n8n `j6U2CDRZi0FI5G32` @ 07:00 | `POST /admin/trigger-daily-digest-*` → `daily_digest.py` | `user_notifications` channel `whatsapp_daily_digest` / `email_digest`; skips jobs already sent on that channel | `format_daily_digest_message` — “Good morning …”, top 3, interview reminders |
| **Legacy notification cron** | n8n `MW5KETbBdrAOk04y` every ~24h | `POST /matches/send-notifications` → `_send_due_digest` | `users.last_notification_at` (24h cadence) | `send_match_digest` — tier/auto-match digest template |
| **Post auto-match (intentional)** | n8n `bqBV6XNPu3z3Ikx5` every 12h → `POST /matches/cron-tick` | `_send_due_digest` **only when** new matches were credited in that tick | Same as legacy (`last_notification_at`) | Same as legacy |

**Keep:** `j6U2CDRZi0FI5G32` (07:00) + `bqBV6XNPu3z3Ikx5` (12h match cron).

**Deactivate:** `MW5KETbBdrAOk04y` (legacy duplicate) and `XAmpEqMqahFa6uOI` (orphan — see below).

### Why match cron + 07:00 batch both call “digest” code

- **`daily_digest.py`** (`run_whatsapp_daily_digest`): scheduled morning batch for users with `alert_frequency = daily`. Re-runs matching, picks up to 3 jobs not yet recorded in `user_notifications` for channel `whatsapp_daily_digest`. Does **not** update `last_notification_at`.
- **`_send_due_digest`** (`matches.py`): event-driven after **auto-match credits new jobs** (12h cron) or when the legacy `send-notifications` workflow runs. Uses matches with `credited_at` in the last 24h. Updates `last_notification_at` on send.

These are **intentionally separate**: a user may get a post-match WhatsApp when new jobs land mid-day, and the 07:00 batch the next morning — but **not** two messages from overlapping n8n schedulers the same day. Deactivating `MW5KETbBdrAOk04y` removes the extra scheduler that re-fired `_send_due_digest` for all auto-match users on a fixed 24h clock.

### Orphan workflow `XAmpEqMqahFa6uOI`

**Name:** `Zed CV - Daily Match Digest` · **Repo:** `infra/n8n/daily_digest_workflow.json`

- Schedule: `0 7 * * *` (same wall time as canonical digest — collision risk).
- Nodes: `deactivate_expired_jobs` RPC + `Get Active Users` only — **no digest send**, incomplete fork.
- Uses `$env.SUPABASE_SERVICE_ROLE_KEY` in HTTP nodes; on instances with `N8N_BLOCK_ENV_ACCESS_IN_EXPRESSIONS=true`, env reads fail in HTTP Request nodes (see [infra/n8n/README.md](../infra/n8n/README.md)).
- Job expiry is already handled by pg_cron (`067_job_expiration_cron.sql`) and admin tools — **do not extend** this workflow; deactivate it.

---

## Prerequisites

| Check | How |
|-------|-----|
| n8n admin access | Sign in at `https://automation.vergeo.company` |
| Canonical digest active | Workflow **ZedApply - Daily Digest (Email + WhatsApp)** `j6U2CDRZi0FI5G32` → **Active** |
| Match cron active | Workflow **Zed CV - Match Cron Every 12h** `bqBV6XNPu3z3Ikx5` → **Active** |
| Backend healthy | `GET https://api.zedapply.com/api/v1/health` → JSON 200 |
| Ingest key set in n8n | `FASTAPI_URL`, `INGEST_API_KEY` (Settings → Variables or container env) |

---

## Procedure

### 1. Confirm current live state (before changes)

In n8n → **Workflows**, verify the **Active** toggle for each ID:

| Workflow | ID | Expected before | Target after |
|----------|-----|-----------------|--------------|
| ZedApply - Daily Digest (Email + WhatsApp) | `j6U2CDRZi0FI5G32` | Active | **Active** |
| Zed CV - Match Cron Every 12h | `bqBV6XNPu3z3Ikx5` | Active | **Active** |
| ZedApply — Notification Digest (Every 24h) | `MW5KETbBdrAOk04y` | Active (audit) | **Inactive** |
| Zed CV - Daily Match Digest | `XAmpEqMqahFa6uOI` | Active or inactive | **Inactive** |

Optional: note last execution times on the two workflows you will deactivate (screenshot or copy execution ID) for rollback verification.

### 2. Deactivate legacy Notification Digest (`MW5KETbBdrAOk04y`)

1. n8n → **Workflows**.
2. Open **ZedApply — Notification Digest (Every 24h)** (ID `MW5KETbBdrAOk04y`).
3. Toggle **Inactive** (top-right). If n8n shows **Publish**, publish the inactive state so the schedule stops (human UI only — no MCP publish from agents).
4. Confirm the workflow list shows **Inactive** for this ID.
5. Open **Executions** — no new scheduled runs should appear after the next former trigger window (~24h from old schedule).

**What this stops:** `POST /api/v1/matches/send-notifications` on a fixed n8n timer (repo: `notification_digest_every_24h.json`).

### 3. Deactivate orphan Daily Match Digest (`XAmpEqMqahFa6uOI`)

1. n8n → **Workflows**.
2. Open **Zed CV - Daily Match Digest** (ID `XAmpEqMqahFa6uOI`).
3. Toggle **Inactive** → **Publish** if prompted.
4. **Do not** add digest HTTP nodes or merge into this workflow — use `j6U2CDRZi0FI5G32` only.

### 4. Confirm keepers still active

| Workflow | ID | Schedule | HTTP target |
|----------|-----|----------|-------------|
| Daily Digest (Email + WhatsApp) | `j6U2CDRZi0FI5G32` | `0 7 * * *` | `POST …/admin/trigger-daily-digest-email`, `POST …/admin/trigger-daily-digest-whatsapp` |
| Match Cron Every 12h | `bqBV6XNPu3z3Ikx5` | every 12h | `POST …/matches/cron-tick` |

Quick manual smoke on keepers (optional, uses ingest key):

```bash
export API_URL="${API_URL:-https://api.zedapply.com/api/v1}"
export INGEST_API_KEY="<from OCI apps/backend/.env>"

curl -sS -X POST "$API_URL/matches/cron-tick?limit=1" \
  -H "INGEST_API_KEY: $INGEST_API_KEY" | jq .

curl -sS -X POST "$API_URL/admin/trigger-daily-digest-whatsapp" \
  -H "INGEST_API_KEY: $INGEST_API_KEY" | jq .
```

Expect HTTP 200 JSON (counts may be zero if no eligible users).

---

## Smoke test — no double WhatsApp same day

Pick **one test user** (operator phone or dedicated QA account) with:

- `alert_frequency = daily`
- WhatsApp digest enabled (`wants_whatsapp_digest` — typically Starter+ with verified WhatsApp)
- At least one match eligible for digest (or use a user who routinely receives 07:00 digests)

### A. After deactivating legacy workflows

1. **Baseline:** In Supabase (or admin tooling), record for the test user:
   - `users.last_notification_at`
   - Rows in `user_notifications` where `channel = 'whatsapp_daily_digest'` for today (UTC date)
2. **Wait** for the next **07:00** server-time run of `j6U2CDRZi0FI5G32`, **or** trigger once manually:
   ```bash
   curl -sS -X POST "$API_URL/admin/trigger-daily-digest-whatsapp" \
     -H "INGEST_API_KEY: $INGEST_API_KEY" | jq .
   ```
3. Confirm **exactly one** WhatsApp digest message on the test phone (message opens with “Good morning …” from `format_daily_digest_message`).
4. **Same calendar day (UTC):** confirm no second digest with the auto-match template (`send_match_digest` shape) unless the user received **new credited matches** from a 12h cron tick (expected mid-day path only when `new_matches_total > 0` in cron response).
5. **Executions tab:** `MW5KETbBdrAOk04y` and `XAmpEqMqahFa6uOI` show **no** new successful runs on the smoke day.

### B. Negative check (duplicate symptom)

If the test user gets **two** WhatsApp digests the same day with similar job lists:

1. Re-check n8n — `MW5KETbBdrAOk04y` may still be **Active**.
2. Search executions for `POST send-notifications` or `/matches/send-notifications`.
3. Compare message copy — duplicate schedulers usually mix “Good morning …” (07:00) with the shorter auto-match digest format.

---

## Rollback

Re-enable a deactivated workflow only if the canonical digest or match cron is broken and you need the legacy path temporarily.

| Workflow | ID | Rollback steps |
|----------|-----|----------------|
| Notification Digest (Every 24h) | `MW5KETbBdrAOk04y` | n8n → open workflow → toggle **Active** → **Publish** → monitor executions |
| Daily Match Digest (orphan) | `XAmpEqMqahFa6uOI` | Same toggle (not recommended — orphan does not send digests) |

**After rollback:** expect duplicate digest risk to return if **both** `MW5KETbBdrAOk04y` and `j6U2CDRZi0FI5G32` are active. Prefer fixing the canonical workflow instead of leaving both on.

Document rollback in your ops log with date, operator, and reason.

---

## Related

| Doc | Purpose |
|-----|---------|
| [infra/n8n/README.md](../infra/n8n/README.md) | Workflow inventory (`live` vs `recommendedActive`), env vars |
| [RUNBOOK_INDEX.md](RUNBOOK_INDEX.md) | Ops index |
| [ADMIN_API_KEYS.md](ADMIN_API_KEYS.md) | `INGEST_API_KEY` for admin trigger routes |
| [AGENTS.md](../AGENTS.md) | Supabase heartbeat invariant (unrelated — do not disable `qA4Zi46MAWx3gTTL`) |

Repo exports: `daily_digest_dual_channel.json`, `notification_digest_every_24h.json`, `match_cron_every_12h.json`, `daily_digest_workflow.json`.
