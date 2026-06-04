# n8n admin cron authentication (prod)

**Audit date:** 2026-06-03 · **Instance:** `https://automation.vergeo.company`

**Who runs this:** A human operator on OCI and/or in the n8n UI. This runbook is **documentation + checklist only** — do **not** use n8n MCP `publish_workflow` or bulk API toggles without explicit maintainer sign-off.

**Goal:** n8n workflows that call `POST /api/v1/admin/*` must authenticate with the same secret the backend expects. When `ADMIN_API_KEY` is set and **differs** from `INGEST_API_KEY`, workflows that send only `INGEST_API_KEY` return **401 Invalid admin API key**.

---

## Background — how the backend resolves the secret

`resolve_admin_api_key()` in `apps/backend/app/core/config.py`:

```python
def resolve_admin_api_key(settings: Settings) -> str:
    return settings.admin_api_key or settings.ingest_api_key
```

`require_admin_api_key()` in `app/core/admin_auth.py` accepts any of:

| Header | Alias |
|--------|--------|
| `ADMIN_API_KEY` | `X-ADMIN-API-KEY` |
| `INGEST_API_KEY` | `X-INGEST-API-KEY` |

The supplied value must **equal** `resolve_admin_api_key(settings)`:

| OCI `ADMIN_API_KEY` | Effective expected secret | n8n sends only `INGEST_API_KEY` |
|---------------------|---------------------------|----------------------------------|
| Unset / empty | `INGEST_API_KEY` | Works |
| Set, **same** as ingest | That shared value | Works |
| Set, **different** from ingest | `ADMIN_API_KEY` | **401** (ingest value ≠ expected) |

Job ingest (`POST /jobs/ingest`) still requires `INGEST_API_KEY` only — do not point scrapers at the admin secret unless you intentionally unify keys (Option A).

See also [ADMIN_API_KEYS.md](ADMIN_API_KEYS.md).

---

## Affected admin routes (n8n)

| Endpoint | Repo workflow export | Typical schedule |
|----------|----------------------|------------------|
| `POST /admin/batch-match` | `infra/n8n/nightly_match_batch_02_00.json` | 02:00 CAT (00:00 UTC) |
| `POST /admin/trigger-daily-digest-email` | `infra/n8n/daily_digest_dual_channel.json` | 07:00 |
| `POST /admin/trigger-daily-digest-whatsapp` | same | 07:00 |
| `POST /admin/check-review-queue` | `infra/n8n/review_queue_alert_hourly.json` | hourly |
| `POST /admin/trigger-renewal-reminders` | `subscription_renewal_reminder.json`, `subscription_renewal_reminder_daily.json` | daily |

**Not in scope here:** `POST /matches/cron-tick` (`match_cron_every_12h.json`) — uses ingest auth on the matches router, not `resolve_admin_api_key`.

---

## Repo export audit — auth headers (2026-06-03)

Headers below are what **repo JSON** sends before any live n8n drift. After this PR, exports use a **Load cron env** Code node and pass `$json.*` into HTTP nodes (works when `N8N_BLOCK_ENV_ACCESS_IN_EXPRESSIONS=true`).

| Export file | HTTP auth headers (repo) | `$env` in HTTP expressions? | Code env passthrough? |
|-------------|--------------------------|------------------------------|------------------------|
| `nightly_match_batch_02_00.json` | `INGEST_API_KEY`, `X-INGEST-API-KEY`, `X-ADMIN-API-KEY` | No (uses `$json`) | Yes |
| `daily_digest_dual_channel.json` | Same trio on both digest nodes | No | Yes (`ingestKey` + `adminKey`) |
| `review_queue_alert_hourly.json` | Same trio | No | Yes |
| `subscription_renewal_reminder.json` | Same trio | No | Yes |
| `subscription_renewal_reminder_daily.json` | Same trio (+ `Content-Type`) | No | Yes |

**`adminKey` in Code node:** `$env["ADMIN_API_KEY"] || $env["INGEST_API_KEY"]` so Option A (equal keys) and Option B (separate admin key) both work without editing HTTP nodes.

---

## Option A (recommended) — unify keys on OCI

Use one shared service secret for ingest + admin cron. n8n only needs `INGEST_API_KEY` in practice; repo exports still send `X-ADMIN-API-KEY` with the same value via `adminKey` fallback.

### Procedure

1. On OCI, open `~/zedcv/apps/backend/.env` (or the path your compose mount uses).
2. Set **both** to the **same** value (generate once if rotating):
   ```bash
   INGEST_API_KEY=<long-random>
   ADMIN_API_KEY=<same-as-ingest>
   ```
3. In n8n (Settings → Variables or docker env for the n8n service), set `INGEST_API_KEY` to match. Optionally set `ADMIN_API_KEY` to the same value for clarity.
4. Reload backend env (not `restart` alone):
   ```bash
   cd ~/n8n-docker   # or your compose directory
   docker compose up -d --force-recreate zedcv-backend
   ```
5. Run smoke tests below.

**When to choose A:** Default for Zed CV prod — one rotation surface, matches historical n8n exports, no live workflow edits required if keys were already equal.

---

## Option B — separate admin key

Keep `ADMIN_API_KEY` distinct from `INGEST_API_KEY` (stricter blast radius for ingest vs cron). n8n **must** send the admin secret on admin routes.

### Procedure

1. OCI `apps/backend/.env`: set distinct `ADMIN_API_KEY` and `INGEST_API_KEY`.
2. n8n env: set **both** `ADMIN_API_KEY` and `INGEST_API_KEY`.
3. Re-import or patch affected workflows from repo (after maintainer sign-off):
   - Confirm **Load cron env** (or **ENV script**) Code node exists.
   - HTTP nodes use `$json.adminKey` for `X-ADMIN-API-KEY` (repo exports post-PR).
4. `force-recreate` backend; smoke test with **admin** key header.

**Do not** paste `ADMIN_API_KEY` into the Job Scraper ingest body — scraper stays on `INGEST_API_KEY` only.

---

## `$env` blocked in HTTP Request nodes

**Symptom:** `$env.FASTAPI_URL` red in HTTP nodes with `[access to env vars denied]`.

**Cause:** `N8N_BLOCK_ENV_ACCESS_IN_EXPRESSIONS=true` on production n8n.

**Fix:** Use a **Code** node to copy env onto the item (`fastapiUrl`, `ingestKey`, `adminKey`); HTTP nodes reference `$json.*` only. Pattern documented in [infra/n8n/README.md § `$env` red](../infra/n8n/README.md). Canonical example: `daily_digest_dual_channel.json`.

Alternative (trade-off): set `N8N_BLOCK_ENV_ACCESS_IN_EXPRESSIONS=false` and recreate n8n — secrets visible in the expression editor.

---

## Smoke tests

From a host that can reach the API (OCI loopback or public URL):

```bash
API_URL="${API_URL:-https://api.zedapply.com/api/v1}"
INGEST_KEY="$(grep -E '^INGEST_API_KEY=' ~/zedcv/apps/backend/.env | cut -d= -f2-)"
ADMIN_KEY="$(grep -E '^ADMIN_API_KEY=' ~/zedcv/apps/backend/.env | cut -d= -f2-)"

# Expect 401
curl -sS -o /dev/null -w "no header: %{http_code}\n" \
  -X POST "$API_URL/admin/check-review-queue"

# Ingest-only header fails when ADMIN_API_KEY is set and differs
curl -sS -o /dev/null -w "ingest only: %{http_code}\n" \
  -X POST "$API_URL/admin/check-review-queue" \
  -H "INGEST_API_KEY: $INGEST_KEY"

# Admin header — must be 200 (body may be {"alerted":false,...})
curl -sS -X POST "$API_URL/admin/check-review-queue" \
  -H "X-ADMIN-API-KEY: ${ADMIN_KEY:-$INGEST_KEY}" | jq .

# Batch match accepts 202
curl -sS -o /dev/null -w "batch-match: %{http_code}\n" \
  -X POST "$API_URL/admin/batch-match" \
  -H "X-ADMIN-API-KEY: ${ADMIN_KEY:-$INGEST_KEY}"

# Digest triggers
curl -sS -X POST "$API_URL/admin/trigger-daily-digest-email" \
  -H "X-ADMIN-API-KEY: ${ADMIN_KEY:-$INGEST_KEY}" | jq .
```

**n8n execution check:** After OCI/n8n env fix, open the workflow → **Executions** → latest run → HTTP node should be **200/202**, not **401**.

---

## Applying repo exports to live n8n (human checklist)

1. Maintainer approves Option A or B and this runbook.
2. Complete OCI + n8n env steps for the chosen option.
3. For each workflow in the audit table: **Import from File** (draft) or hand-merge **Load cron env** + HTTP header changes from repo.
4. Map credentials if prompted; confirm `FASTAPI_URL`, `INGEST_API_KEY`, and (Option B) `ADMIN_API_KEY` in n8n Variables.
5. **Save** → manual **Execute workflow** → verify HTTP 200/202.
6. **Publish** / activate only after smoke passes.

Agents: **do not** publish to production n8n without maintainer sign-off.

---

## Rollback

| Change | Rollback |
|--------|----------|
| Option A key unify | Restore previous `.env` values; `force-recreate` backend; revert n8n Variables |
| Option B workflow headers | Re-import previous workflow export from git tag, or remove `X-ADMIN-API-KEY` nodes and set `ADMIN_API_KEY=` empty on backend to fall back to ingest |
| Code env passthrough | Revert to prior export; risk `$env` denied returns if HTTP nodes used `$env` directly |

---

## Related

| Doc | Purpose |
|-----|---------|
| [ADMIN_API_KEYS.md](ADMIN_API_KEYS.md) | Header names, rotation, browser vs automation |
| [infra/n8n/README.md](../infra/n8n/README.md) | Workflow inventory, `$env` troubleshooting |
| [RUNBOOK_N8N_DIGEST_DEDUP.md](RUNBOOK_N8N_DIGEST_DEDUP.md) | Digest dedup (orthogonal) |
| [RUNBOOK_INDEX.md](RUNBOOK_INDEX.md) | Ops index |
| [staging.md](staging.md) | Staging n8n duplicate workflows |
