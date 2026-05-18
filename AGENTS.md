# AGENTS.md — Operating Guide for AI Coding Assistants

This document is a contract between Zed CV's maintainer and any AI coding
assistant (Claude, Cursor, Aider, Copilot, etc.) that touches this
codebase. It exists because we've collected enough recurring failure
modes that "be careful" is no longer a sufficient instruction.

Read this **before** reading `CLAUDE.md`, `AI_CONTEXT.md`, or
`ZED_CV_BIRDS_EYE_VIEW.md`. Those documents describe what the project
*is*. This one describes what you, the agent, are allowed and required
to do.

If you have not been asked to act as a coding agent in this repo,
stop reading.

---

## 1. What Zed CV is, in one paragraph

Zed CV is an AI job-matching SaaS for Zambia. Users upload a CV; we
parse it, embed it with `gemini-embedding-001` (768 dim, cosine), match
it against jobs scraped via n8n + WAHA, and deliver match digests over
WhatsApp. Backend is FastAPI (Python 3.11), frontend is Next.js 14
(App Router), database is Supabase (Postgres + pgvector + RLS),
WhatsApp delivery is WAHA, payments are DPO Pay (Visa/MasterCard) +
Lenco (Zambian mobile money). The whole stack runs under a $30/month
budget — free tiers everywhere, one OCI VM for the Docker compose,
Vercel hobby for the frontend. Currency is ZMW stored as ngwee.

---

## 2. Invariants — Do Not Change Without Explicit Approval

These are choices that look like normal config but are load-bearing.
Changing one will silently break a downstream system. Ask before any
change to any of these:

| Invariant | Value | Why it matters |
| --- | --- | --- |
| Embedding model | `gemini-embedding-001` | Changing this without re-embedding both jobs AND CVs puts them in different coordinate spaces; matching silently returns 0. See `memory: project_zedcv_matching_fixed_2026_05_12.md`. |
| Embedding dim | 768 | pgvector column type is fixed to `vector(768)` in migration 007. Bigger needs a migration + HNSW index rebuild. |
| Phone format | `+260XXXXXXXXX` | E.164 with country code. WAHA expects this; OTP cooldown is keyed on it; users table has a UNIQUE constraint on this column. |
| Currency unit | Ngwee (integer) | All amounts in DB are integer ngwee (1 ZMW = 100 ngwee). The `// 100` in payment confirmations relies on this. Don't introduce float kwacha anywhere. |
| Matching weights | 60% vector / 30% skill / 10% bonus | Embedded in the `match_jobs_for_user` RPC. See migration 009 for the function definition. Changing weights without updating the RPC silently uses old weights. |
| RPC return shape | `match_jobs_for_user` returns `(job_id, vector_score, score, matched_skills)` | Touched on 2026-05-11. Frontend reads these field names directly. Renaming any column breaks `/matches`. |
| OpenAPI is source of truth | `docs/openapi.yaml` | Backend Pydantic schemas and frontend Zod schemas both derive from it. Add an endpoint without updating it and the contract drifts; the frontend will type-check against a stale spec. |
| Migration files are immutable | `infra/supabase/migrations/NNN_*.sql` | Never edit an existing migration. Always create a new one. Prod has applied the originals — editing them desyncs prod from the file. |
| Free-tier heartbeat | n8n pings Supabase every 6h | Removing this lets Supabase pause the project after 7 days of inactivity. Don't disable the n8n workflow even if it looks pointless. |

---

## 3. Known Failure Modes — Recognize These Symptoms

When something breaks, check this table before debugging from scratch.
These have all bitten us at least once and the surface symptom is often
misleading.

### 3.1 "CORS error on sign-in" — almost always not CORS

**Surface symptom:** browser console reports
`No 'Access-Control-Allow-Origin' header is present`.

**Likely cause:** an unhandled exception in a FastAPI route. Uvicorn
returns a bare `text/plain` 500 which **bypasses** the CORS middleware
entirely, so no ACAO header is attached. The browser interprets that
as a CORS failure.

**First step:** `curl -i -X POST` the endpoint. If you see
`HTTP/1.1 500 Internal Server Error` with `content-type: text/plain`,
it's an exception. Do not edit CORS config. Find the traceback in
`docker compose logs zedcv-backend`.

### 3.2 Matching returns 0 results despite jobs and CVs existing

**Likely cause:** jobs and CVs were embedded with different models.
Cosine similarity across coordinate spaces is near-zero across the
board.

**Diagnose:**
```sql
SELECT vector_dim, COUNT(*) FROM jobs WHERE embedding IS NOT NULL GROUP BY 1;
SELECT vector_dim, COUNT(*) FROM cvs WHERE embedding IS NOT NULL GROUP BY 1;
```
If dims match but matching is still empty, check `EMBEDDING_MODEL` in
the deployed env vs what generated the existing embeddings.

**Fix:** `POST /api/v1/admin/re-embed?target=all` rebuilds both sides
against the current `EMBEDDING_MODEL`.

### 3.3 WAHA returns 422 on `/api/sendText`

**Surface symptom:** OTP delivery returns 503 with body
"WhatsApp delivery is temporarily unavailable" (the `auth.py`
try/except added 2026-05-12 catches this cleanly — before that fix,
it was a CORS-masked 500).

**Likely cause:** WAHA session not in `WORKING` state. The container
is up and `/api/sessions` returns 200, but the WhatsApp pairing
either isn't loaded yet or got revoked.

**Diagnose:** `GET /api/sessions` from inside the docker network. If
it returns `[]` or any status other than `WORKING`, that's the cause.
`check_waha_health()` in `app/services/whatsapp.py` validates this
correctly. `/api/v1/health` surfaces it in the `waha` field.

**Fix (in order of cheapness):**
1. `POST /api/v1/admin/waha/bootstrap-session` — re-runs the idempotent
   session bootstrap. This is the documented manual recovery path.
2. `docker compose restart zedcv-backend` — the FastAPI startup hook
   `bootstrap_waha_session` in `main.py` runs `ensure_session_started`
   automatically on boot. Use this if the admin endpoint is unreachable.
3. If neither works, the session credentials on disk are corrupt or
   the phone revoked Linked Devices access. Scan a fresh QR via the
   WAHA dashboard at `https://waha.vergeo.company`.

**Prevention (already in place as of 2026-05-12):**
- WAHA service has bind mount `/home/ubuntu/n8n-docker/waha_data/sessions`
  → `/app/.sessions`. Don't remove it.
- WAHA image is digest-pinned (`devlikeapro/waha@sha256:b579...`) so a
  surprise `docker pull` can't change the image and invalidate the
  session file format.
- Backend's startup hook calls `ensure_session_started("default")` so
  every backend restart self-heals the session. Don't remove the hook
  from `main.py`.

### 3.4 `docker compose up -d --force-recreate` doesn't pick up code changes

**Likely cause:** The compose file uses `image:` (not `build:`) or the
image was already built. Force-recreate only re-creates the container
from the existing image.

**Fix:** `docker compose build zedcv-backend && docker compose up -d --force-recreate zedcv-backend`.

### 3.5 `.env` change not picked up after restart

**Likely cause:** `docker compose restart` does not re-read `.env`.
Only `docker compose up` does.

**Fix:** `docker compose up -d --force-recreate <service>`.

### 3.6 Git index corruption on the Windows Cowork mount

**Surface symptom:** `error: bad index file sha1 signature` or similar
on a routine `git status`.

**Likely cause:** An IDE (Cursor, VSCode) held an exclusive handle on
`.git/index` during a Cowork/Claude write.

**Fix:** Close all IDEs touching the repo, then
`rm .git/index && git reset` to rebuild from HEAD.

### 3.7 Cowork file Write desyncs from Linux mount

**Surface symptom:** `Read` shows the updated file; bash sees the old
content.

**Fix:** force-sync via bash heredoc:
```bash
cat > /sessions/.../mnt/ZedCV/path/to/file << 'PY_EOF'
<new content>
PY_EOF
```

---

## 4. Pre-commit checklist

Before opening a PR or pushing, walk through this list. It's short
because each item has caught a real bug.

- [ ] If you added an endpoint, update `docs/openapi.yaml` in the same change.
- [ ] If you added a Pydantic model, run `pytest apps/backend/tests/` locally — schema validation tests catch refusal/echo regressions in LLM output.
- [ ] If you changed a SQL migration: did you create a NEW file? Never edit an applied migration.
- [ ] If you changed `requirements.txt`: did you `docker compose build zedcv-backend` (not just up)?
- [ ] If you changed `.env`: did you `up -d --force-recreate`, not just `restart`?
- [ ] If you touched the embedding model or vector dim: have you planned a re-embed? An untriggered model change means 0 matches in prod.
- [ ] If you wrote prose to be shipped to users (WAHA messages, email): is it consistent with `TIER_DISPLAY_NAMES` and `PLAN_INFO_BY_TIER` in `webhooks.py`?

---

## 5. Cost & quota guardrails

- $30/month total budget. Free tiers everywhere; if a free tier is
  about to be exceeded, surface that as a P1 in your output, not as a
  silent paid upgrade.
- Gemini token quota is the most-likely-to-burn. Cache LLM and
  embedding calls via the `ai_cache` table (`app/services/cv_parser.py`
  and `app/services/embeddings.py` already wire this).
- Anthropic prompt caching is enabled on the system prompt for Claude
  API calls — preserve the prompt structure (system block first, then
  user) so the cache hits.
- `/cv/upload` graceful-degrades to `cv_upload_queue` when Gemini
  refuses; the drain endpoint is `POST /admin/cv-queue/drain`. Don't
  return 503 from `/cv/upload` directly.

---

## 6. Where to look for more

- `CLAUDE.md` — short project rules (always loaded into Claude's context)
- `AI_CONTEXT.md` — full architecture, request flows, schema
- `docs/ZED_CV_BIRDS_EYE_VIEW.md` — exec/handoff summary
- `docs/openapi.yaml` — API contract; this is canon for both sides
- `docs/CODE_REVIEW_PROMPT.md` — what a code review on this repo checks for
- `DEPLOY.md` — deploy steps for backend (OCI) and frontend (Vercel)
- `infra/supabase/migrations/` — every schema change, in order
- `infra/n8n/` — n8n workflow JSON exports (scraper, heartbeat)
- `~/n8n-docker/` on the OCI server — the docker-compose for backend + WAHA + n8n in prod

---

## 7. When to ask before doing

Default to acting on small reversible changes (typo fixes, one-file
refactors, missing test cases). Ask before:

- Any migration — naming, scope, and idempotency need confirmation.
- Any change to an Invariant in section 2.
- Anything that touches money flow (DPO/Lenco webhook logic,
  `TIER_PRICES`, `TIER_LIMITS`, subscription period length).
- Dependency upgrades that cross a major version.
- Changes that require a deploy + smoke-test cycle (frame the plan
  first so the human can decide whether to batch it with other work).
- Anything that adds an external API or credential surface.

When you ask, present a plan with the proposed change, the affected
files, the rollback approach, and the smoke test that proves it
worked. Don't ask "should I do X?" — ask "I propose X because Y; the
risk is Z; here's how I'd verify; ok to proceed?"

---

## Cursor Cloud specific instructions

### Services overview

| Service | Command | Port | Notes |
|---------|---------|------|-------|
| Backend (FastAPI) | `cd apps/backend && uvicorn main:app --reload --port 8000` | 8000 | Needs `.env` with at minimum `SUPABASE_URL`, `SUPABASE_KEY`, `GEMINI_API_KEY`, `JWT_SECRET` |
| Frontend (Next.js) | `cd apps/frontend && npm run dev` | 3000 | Needs `.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` |

### Running tests

- **Backend**: `cd apps/backend && python3 -m pytest tests/ -v` — tests mock all external deps (Supabase, Gemini, WAHA) via `conftest.py`, no real credentials needed.
- **Frontend**: `cd apps/frontend && npm test` — uses Vitest + MSW, no network access.
- **Frontend lint**: `cd apps/frontend && npm run lint`

### Gotchas

- `pytest-asyncio` is required for `test_skill_resolver.py` async tests. The update script installs it.
- `libmagic1` system package is required by `python-magic` (CV upload MIME validation). Pre-installed in the VM.
- The backend uses `pydantic-settings` which reads `.env` from `apps/backend/.env`. If that file is missing, the server won't start (required fields: `supabase_url`, `supabase_key`, `gemini_api_key`, `jwt_secret`).
- `/home/ubuntu/.local/bin` must be on `PATH` for `uvicorn` and `pytest` (pip installs there as non-root).
- Without real Supabase/Gemini credentials, the health endpoint reports `"status": "unhealthy"` but the server runs fine — routes that hit Supabase will 500 as expected.
- The frontend uses Next.js 14 App Router. `npm run build` verifies the full compilation chain.
