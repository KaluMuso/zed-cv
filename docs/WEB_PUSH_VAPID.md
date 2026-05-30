# Web Push (VAPID) — Ops Runbook

Browser push for **85%+ match** alerts (migration `079_web_push_subscriptions`). Backend uses `pywebpush`; frontend subscribes via the service worker (`apps/frontend/worker/index.ts`).

**Prerequisites:** Migration `079` applied on Supabase; backend image built after `pywebpush` was pinned in `requirements.txt` (#171).

---

## 1. Generate keys (once per environment)

Run locally (needs `cryptography` from backend venv):

```bash
cd apps/backend && python3 scripts/generate_vapid_keys.py
```

Output:

| Script label | Env var | Where |
|--------------|---------|--------|
| `VAPID_PRIVATE_KEY` (PEM block) | `VAPID_PRIVATE_KEY` | **OCI only** — `apps/backend/.env` on the VM |
| `VAPID_PUBLIC_KEY` (base64url) | `VAPID_PUBLIC_KEY` | OCI backend `.env` |
| Same public string | `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | **Vercel** — all environments that serve the app |

**Never** commit keys, paste the private key in chat/PRs, or put `VAPID_PRIVATE_KEY` on Vercel.

`VAPID_CLAIMS_EMAIL` is the `mailto:` contact for VAPID JWT claims (default in code: `convergeozambia@gmail.com`). Set explicitly on OCI if you use a different operator address.

### Private key in `.env`

Paste the **full PEM** from the script (including `-----BEGIN PRIVATE KEY-----` / `-----END PRIVATE KEY-----`). In `apps/backend/.env`, a quoted multiline value is fine; after edits use **`docker compose up -d --force-recreate zedcv-backend`** (not `restart` — see `AGENTS.md` §3.5).

Public key must be **identical** on OCI (`VAPID_PUBLIC_KEY`) and Vercel (`NEXT_PUBLIC_VAPID_PUBLIC_KEY`).

---

## 2. Env placement checklist

### OCI (`~/n8n-docker` or repo `apps/backend/.env` mounted into backend)

| Variable | Required | Notes |
|----------|----------|--------|
| `VAPID_PRIVATE_KEY` | Yes | PEM; signing only on server |
| `VAPID_PUBLIC_KEY` | Yes | base64url from script |
| `VAPID_CLAIMS_EMAIL` | Yes | e.g. `convergeozambia@gmail.com` |

After setting vars:

```bash
cd ~/n8n-docker   # or your compose directory
docker compose build zedcv-backend
docker compose up -d --force-recreate zedcv-backend
```

### Vercel (project: frontend, root `apps/frontend`)

| Variable | Required | Notes |
|----------|----------|--------|
| `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | Yes | Same value as `VAPID_PUBLIC_KEY` on OCI |

Redeploy **without build cache** after changing `NEXT_PUBLIC_*` vars.

---

## 3. Verify configuration (no browser)

```bash
curl -s https://api.zedapply.com/api/v1/health | jq '.vapid_configured'
# expected: true
```

If `false`, keys are missing in the running container env (recreate container, confirm `.env` path).

---

## 4. Smoke test (manual — Chrome desktop)

1. **Pro (or any) user** with ≥1 credited match: sign in at https://www.zedapply.com
2. Open **`/matches`** — accept the “Enable alerts” prompt (or enable notifications in site settings if already granted).
3. Confirm subscription stored: row in `web_push_subscriptions` for that `user_id` (Supabase table).
4. **Admin** session: copy Bearer JWT from browser (or sign in as admin).
5. Send test push:

```bash
curl -sS -X POST 'https://api.zedapply.com/api/v1/admin/push/test' \
  -H 'Authorization: Bearer <ADMIN_OR_TARGET_USER_JWT>' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"<uuid-of-user-who-subscribed>"}'
```

Optional body `user_id` targets a specific user; omit to send to the admin’s own subscriptions.

**Expected response:** `{"delivered":1,"message":"Test push sent to 1 device(s)"}` (or higher if multiple devices).

**Expected UX:** Chrome shows “ZedApply test notification”; tap opens **`/matches`** (test payload). High-match cron pushes use **`/matches/{match_id}`** (`build_high_match_payload` in `web_push.py`).

### High-match click path (cron / real alert)

Payload `data.url` / `url` is `/matches/<match_id>`. Service worker `notificationclick` navigates to `origin + path` (`worker/index.ts`).

---

## 5. Failure — where to look

| Symptom | Check |
|---------|--------|
| `vapid_configured: false` | OCI `.env`; force-recreate backend |
| Subscribe UI: “Push is not configured” | Vercel `NEXT_PUBLIC_VAPID_PUBLIC_KEY`; redeploy frontend |
| `delivered: 0` — no subscriptions | User did not complete enable on `/matches` |
| `delivered: 0` — VAPID not configured | Backend env |
| Push send errors | `docker compose logs zedcv-backend` (grep `web push`) |
| 404/410 on endpoint | Stale subscription; row auto-deleted in `send_payload_to_user` |

Admin route: `POST /api/v1/admin/push/test` — requires **admin JWT** (`require_admin`), not ingest key alone.

---

## 6. Related code

| Piece | Path |
|-------|------|
| Keygen | `apps/backend/scripts/generate_vapid_keys.py` |
| Send / payload | `apps/backend/app/services/web_push.py` |
| Admin test | `apps/backend/app/api/v1/admin.py` (`/push/test`) |
| Subscribe API | `apps/backend/app/api/v1/push.py` |
| Frontend UX | `apps/frontend/src/lib/pushNotifications.ts`, `PushPermissionPrompt.tsx` |
| SW click handler | `apps/frontend/worker/index.ts` |
| Schema | `infra/supabase/migrations/079_web_push_subscriptions.sql` |

OpenAPI: `/admin/push/test`, `/push/subscribe`, health field `vapid_configured`.
