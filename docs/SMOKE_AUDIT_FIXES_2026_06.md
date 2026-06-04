# Smoke audit — post #259 + digest dedup

**Date:** 2026-06-04  
**Target:** Production API [https://api.zedapply.com/api/v1](https://api.zedapply.com/api/v1) · Supabase `chnesgmcuxyhwhzomdov` · n8n `https://automation.vergeo.company`  
**Repo ref:** `master` @ `298d4ee` (includes `01b860f` — PR **#259**)  
**Agent:** Cursor Cloud — no `ADMIN_API_KEY`, no user/admin JWT, no Resend/WAHA dashboard access in env.

**Legend:** **PASS** | **FAIL** | **BLOCKED** (needs admin/super session or operator UI) | **CODE** (pytest / static verification on `master`)

---

## Preconditions

| Check | Result | Evidence |
| --- | --- | --- |
| PR **#259** merged to `master` | **PASS** | `01b860f` — tailor-cv `job_skills` embed, promo tier resolution, `admin_stats` capacity keys, admin job XOR |
| Backend **#259** deployed on OCI | **BLOCKED** | `/health` returns `version: 0.1.0` only (no git SHA). Cannot confirm image age from API. Maintainer: `docker compose build zedcv-backend && docker compose up -d --force-recreate zedcv-backend` after merge. |
| n8n **digest dedup** applied ([RUNBOOK_N8N_DIGEST_DEDUP.md](./RUNBOOK_N8N_DIGEST_DEDUP.md)) | **FAIL** | Live n8n (2026-06-04): `MW5KETbBdrAOk04y` (*Notification Digest Every 24h*) **active**; `XAmpEqMqahFa6uOI` (*Daily Match Digest* orphan) **active**. Target: both **inactive**. Keepers `j6U2CDRZi0FI5G32` + `bqBV6XNPu3z3Ikx5` **active** (expected). |
| API health | **PASS** (degraded) | `GET /health` → `status: degraded`, `supabase: true`, `waha: false`, `last_gemini_call_status: quota_exhausted` |
| Migrations ≥ `099` on prod DB | **PASS** | Latest ledger: `106_notifications_train_schema_guard` (`20260604060001`) |

---

## Checklist (5 items)

| # | Scenario | Result | Notes / evidence |
| --- | --- | --- | --- |
| 1 | **Matches → Tailor CV** → 200; builder loads skills (not 500) | **CODE** + **BLOCKED** (live) | **Root cause fixed in #259:** `matches.py` selects `jobs(..., job_skills(skills(name)))` not `jobs.skills`. **Tests:** `test_match_tailor_cv_query.py`, `test_match_tailor_cv_tier_gate.py` — **PASS** (25 tests in admin/tailor bundle). **Prod DB:** all `matches.status = new` (100 rows); no `active` match to hit from UI without crediting flow. **Live:** needs Professional+ (or Super) user JWT → `POST /matches/{id}/tailor-cv` → open builder with `generationId`; confirm skills section populated. **Risk if backend not recreated:** old image still 500s on `jobs.skills`. |
| 2 | **Admin → Post job** (dialog) → **201** with **only** `apply_url` **or** `apply_email` | **CODE** + **BLOCKED** (live) | **Schema:** `AdminJobCreate` XOR — at least one apply path, not both (`app/schemas/jobs.py`). **Tests:** `test_admin_jobs.py` — 201 with `apply_email` only (`_valid_payload`); 422 if neither or both — **PASS**. **Frontend (#259):** omit `admin_published` on create; XOR on URL/email. **Live:** superadmin JWT → `/admin` Post job dialog → 201 with single apply field. |
| 3 | **Promo** (if active): payment webhook → **Professional**, not Starter | **FAIL** (prod historical) + **CODE** (fix) | **Promo window:** user `1fedcbc6…` has `promotion_applied_until` **2026-07-29** (active). **Completed payment** `4ba211e9…` **6250** ngwee (K62.50 = 50% of Professional list) on **2026-06-03 19:36 UTC** → subscription tier **`starter`** (**wrong**). Payment predates merge commit `01b860f` (**21:10** +0200). `webhook_data.intended_tier` **null** on that row. **Tests:** `test_promotion_pricing.py::test_resolve_tier_promo_professional_not_starter` — **PASS** (12500 + promo → `professional`). **Required for PASS:** staging **Lenco webhook replay** (or new sandbox charge) **after** backend recreate with #259; expect `subscriptions.tier = professional`. |
| 4 | **`GET /admin/capacity`** → non-zero `jobs` / `users` when DB has data | **BLOCKED** (live) + **PASS** (data) | **Unauthed:** `GET /admin/capacity` → **403** (expected). **SQL `admin_stats()`:** `jobs_total` **1151**, `users_total` **2**, `jobs_active` **430** — non-zero. **#259 fix:** reads `jobs_total` / `users_total` from RPC (not stale `total_*` keys). **Live:** superadmin JWT or `X-ADMIN-API-KEY` → expect `jobs.used ≥ 1151`, `users.used ≥ 2` (not 0). |
| 5 | **One user, one digest per 24h** (Resend + WAHA after 07:00 cron) | **FAIL** (precondition) + **BLOCKED** (logs) | **Dedup ledger:** `user_notifications` **empty** (no `whatsapp_daily_digest` / `email_digest` rows yet). **Duplicate schedulers still on** (see preconditions) — **cannot PASS** until `MW5KETbBdrAOk04y` and `XAmpEqMqahFa6uOI` deactivated per runbook. **Users:** `+260971715270` `last_notification_at` **2026-05-23**; `+260979370372` **null**. **Manual after dedup + next 07:00 UTC:** Resend dashboard + WAHA logs — exactly one “Good morning …” digest per eligible user per UTC day; no second legacy `send-notifications` run same day. |

---

## Automated verification (`master` workspace)

| Suite | Result |
| --- | --- |
| `pytest` `test_match_tailor_cv_query`, `test_match_tailor_cv_tier_gate`, `test_admin_jobs` | **25 passed** |
| `pytest` `test_promotion_pricing.py` | **8 passed** |

---

## Read-only probes (2026-06-04)

```bash
# Health
curl -sS https://api.zedapply.com/api/v1/health | python3 -m json.tool

# Capacity without auth (expect 403)
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://api.zedapply.com/api/v1/admin/capacity
```

**n8n workflow state (MCP):**

| Workflow | ID | Expected | Observed |
| --- | --- | --- | --- |
| Daily Digest (Email + WhatsApp) | `j6U2CDRZi0FI5G32` | Active | **Active** |
| Match Cron Every 12h | `bqBV6XNPu3z3Ikx5` | Active | **Active** |
| Notification Digest (Every 24h) | `MW5KETbBdrAOk04y` | **Inactive** | **Active** |
| Daily Match Digest (orphan) | `XAmpEqMqahFa6uOI` | **Inactive** | **Active** |

---

## Maintainer actions (to clear FAIL / BLOCKED)

1. **OCI:** `docker compose build zedcv-backend && docker compose up -d --force-recreate zedcv-backend` so **#259** is live (tailor-cv, capacity, promo webhooks).
2. **n8n:** Deactivate `MW5KETbBdrAOk04y` and `XAmpEqMqahFa6uOI`; publish inactive state ([RUNBOOK_N8N_DIGEST_DEDUP.md](./RUNBOOK_N8N_DIGEST_DEDUP.md)).
3. **Re-smoke with admin JWT:** rows 1, 2, 4 — browser or `curl` with `Authorization: Bearer …` (superadmin).
4. **Promo:** Lenco sandbox webhook replay for K62.50 (12500 promo checkout) → confirm **`professional`** tier; optionally repair user `1fedcbc6…` subscription if they paid for Professional.
5. **Digest:** After next **07:00** cron, verify Resend + WAHA — one digest per user per UTC day.

---

## Sign-off

| Role | Name | Date | Notes |
| --- | --- | --- | --- |
| Agent (automated) | Cursor Cloud | 2026-06-04 | Doc-only; live UI/API smokes **BLOCKED** without admin JWT. **FAIL:** n8n dedup not applied; historical promo tier wrong. |
| Maintainer | | | Complete BLOCKED rows after backend recreate + n8n dedup. |
