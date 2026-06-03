# Scope lock — June 2026 (Phase 0 + product decisions)

**Status:** Locked for the June 2026 merge train  
**Date:** 2026-06-03  
**Audience:** Maintainers, Cloud Agents, and anyone opening parallel PRs against `master`

This document freezes scope after **Phase 0** discovery and explicit product decisions. Treat it as the contract when a PR might conflict with another train (notifications, referrals, tier config, admin review, CV export).

---

## Related docs and PR trains

| Doc | Location | Notes |
| --- | --- | --- |
| **Notifications migration train** | [NOTIFICATIONS_MIGRATIONS.md](NOTIFICATIONS_MIGRATIONS.md) | Supersedes GitHub **#248** / **#249**; apply order `099`→`103`. On `master` once `cursor/notifications-migration-train-9e6a` merges. |
| **General migration order** | [migrations.md](migrations.md) | Canonical Supabase numbering, renames, prod apply rules. |
| **MERGE_TRAIN** | *(not in repo yet)* | No `docs/MERGE_TRAIN.md` on `master` as of 2026-06-03. Use this file + [NOTIFICATIONS_MIGRATIONS.md](NOTIFICATIONS_MIGRATIONS.md) for train-specific ordering until a dedicated merge-train index lands. |
| **Admin review queue** | [admin_job_review_cleanup.md](admin_job_review_cleanup.md) | Visibility rules, bulk-dismiss safety, ops counts. |
| **Tier config audit** | [tier-config-audit.md](tier-config-audit.md) | `tier_config` vs `TIER_PRICES`, Bwana/FAQ sync, smoke checklist. |
| **CV export (Phase 0)** | [ui-ux-styling-brief-from-pdfs.md](ui-ux-styling-brief-from-pdfs.md) § Third round | Print/PDF vs scratch WeasyPrint paths. |

---

## Phase 0 baseline (already shipped or in active PRs)

Phase 0 means **minimum viable plumbing** without opening new product surfaces. Do not re-litigate these unless this scope lock is explicitly revised.

| Area | Phase 0 state | Locked follow-up |
| --- | --- | --- |
| **In-app notifications** | Migration `100_in_app_notifications.sql` + backend `in_app_notifications.py`; navbar inbox UI on **#248**/**#249** branches | Ship via [notifications migration train](NOTIFICATIONS_MIGRATIONS.md) — **not** separate conflicting `099`/`100` filenames. |
| **Referral attribution** | `067_user_referrals.sql`, signup `referral_ref`, profile counts | Qualify/reward trigger and copy — see **Referrals** below. |
| **Tailored CV export** | Browser print / Save as PDF (`printTailoredCv`, `print.css`) | **No Word (.docx) download in v1** — see **CV export**. |
| **Admin job review** | Track 4e queue, bulk auto-dismiss for **hidden** backlog only | **Human approve** before publish; no auto-publish from bulk tools — see **Review queue**. |
| **Pricing source of truth** | `public.tier_config` drives `/tiers`, webhooks, match limits | `TIER_PRICES` / `TIER_LIMITS` in `subscription.py` are **fallback + CI pins only** — see **Tier config**. |

---

## Locked product decisions

### 1. Referrals — trigger **B** (first paid subscription)

| Decision | Detail |
| --- | --- |
| **Qualify trigger** | Referrer reward fires when the **referred user completes their first paid subscription** (Starter, Professional, or Super Standard), not on CV upload. |
| **Interim v1 behaviour** | Until the **payment-trigger PR** ships, keep the existing **CV-upload qualify path** (`qualify_referral_on_cv_upload` in `app/services/referral.py`) so referrers are not blocked — but treat it as **technical debt**, not the long-term rule. |
| **v1 reward amount** | **+5 matches** per qualified referral (`REFERRAL_QUALIFY_BONUS_MATCHES = 5` → `users.referral_match_bonus`, with free-tier welcome stacking as today). |
| **Profile / API copy** | `referral_qualified_count` and UI strings must describe **paid conversion** once the payment trigger lands; until then, document “+5 matches (interim: first CV upload)” in release notes only — do not market CV upload as the permanent rule. |
| **Anti-abuse** | Referred account must be a real paid conversion (webhook-confirmed tier ≠ `free`); self-referral and duplicate events remain blocked. |

**Out of scope for v1:** tier-month grants (“1 free month of Starter”), WhatsApp share command, referral dashboard beyond profile card.

**Implementation note:** Wire qualify/reward from `activate_subscription_after_payment` / Lenco+DPO webhook success paths after the interim PR; remove or gate `qualify_referral_on_cv_upload` from `/cv/upload` when payment trigger is live.

---

### 2. Notifications — channel **B** (in-app inbox)

| Decision | Detail |
| --- | --- |
| **Primary surface** | **In-app inbox** (`notifications` table, `GET /api/v1/notifications`, navbar dropdown). GitHub **#248** (user inbox) and **#249** (admin broadcast) are superseded by the unified migration train. |
| **v1 `type` values** | `web_push`, `tier_expiry`, `invoice`, `admin_broadcast` (migration `100`). |
| **Not the inbox** | `user_notifications` (migration `050`) stays **digest dedup only** — do not merge into the inbox model. |
| **Web Push** | Still delivered via push APIs; successful/high-signal pushes also write an inbox row where applicable (`web_push` / `admin_broadcast`). |

Do not add a second inbox table or rename RPC columns without updating [NOTIFICATIONS_MIGRATIONS.md](NOTIFICATIONS_MIGRATIONS.md) and `docs/openapi.yaml`.

---

### 3. CV export — **PDF only** in v1

| Path | v1 scope |
| --- | --- |
| **Tailored CV builder + profile generator preview** | Browser **print / Save as PDF** only (`printTailoredCv()`, `print.css`). **No `.docx` download.** |
| **Scratch / manual CV wizard** | Server **PDF** via WeasyPrint (`POST /cv/build-from-scratch`, `cv_pdf_renderer.py`) — unchanged. |
| **CV upload parsing** | Users may still **upload** `.docx` CVs for parsing; this lock applies to **export/download**, not ingest. |

Deferred: Word export, branded DOCX templates, `cursor/cv-print-layout-docx-*` feature work — post–June train unless scope lock is revised.

---

### 4. Admin review queue — human approve; bulk-safe for hidden backlog only

| Decision | Detail |
| --- | --- |
| **Publish path** | Jobs that should appear on `/jobs` and `/matches` require **human approval** (fix apply path, deadline, or explicit admin publish) — not automatic promotion from bulk scripts. |
| **Bulk tools** | `bulk-auto-dismiss-hidden`, `bulk-dismiss-expired`, `bulk-dismiss-junk`, `bulk-dismiss-safe` may **only** clear `is_review_required` / set `admin_reviewed_at` on rows already hidden or objectively stale — see [admin_job_review_cleanup.md](admin_job_review_cleanup.md). |
| **Forbidden** | Bulk endpoints must **not** set `is_active = true`, `admin_published = true`, or change `quality_score` without human review. |
| **CLI** | `batch_dismiss_hidden_review_queue.py` — hidden backlog only; never auto-dismiss active `no_deadline` rows. |

---

### 5. Tier config **>** `TIER_PRICES`; FAQ and Bwana stay in sync

| Decision | Detail |
| --- | --- |
| **Source of truth** | Live prices and match limits come from **`public.tier_config`** (`app/services/tier_config.py`). |
| **Constants** | `TIER_PRICES` / `TIER_LIMITS` in `app/schemas/subscription.py` are **fallback** when DB is empty and **CI pins** (`tests/test_tier_limits.py`). Do not edit them for marketing changes. |
| **Consumers that must read DB** | `/api/v1/tiers`, `/pricing`, DPO/Lenco webhooks, `get_effective_match_limit()`, WhatsApp `plan` copy (`build_plan_info_by_tier`), **Bwana FAQ** (`match_faq_from_db`), **Bwana system prompt** (`load_tier_pricing_snapshot`). |
| **Admin change process** | Follow smoke checklist in [tier-config-audit.md](tier-config-audit.md) §4 after any `PATCH /admin/tiers/*`. |

Homepage / `UpgradeButton` hardcoded kwacha remain a **known gap** (tier-config-audit §2); do not add new hardcoded tier prices in June PRs — wire to `/tiers` or document as deferred.

---

## PR train map (June 2026)

Use branch names as the source of truth for what is in flight. **Do not** re-open superseded PRs without rebasing onto the train branch.

| Train | Branch / PR hint | Scope lock section |
| --- | --- | --- |
| Notifications | `cursor/notifications-migration-train-9e6a` → [NOTIFICATIONS_MIGRATIONS.md](NOTIFICATIONS_MIGRATIONS.md) | §2 Notifications |
| Referral payment trigger | TBD (`cursor/referral-paid-qualify-*`) | §1 Referrals |
| Tier / Bwana sync | `cursor/tier-config-faq-sync-9e6a`, #255 on `master` | §5 Tier config |
| Admin review ops | `cursor/admin-review-queue-*`, [admin_job_review_cleanup.md](admin_job_review_cleanup.md) | §4 Review queue |
| Scope lock (this doc) | `cursor/scope-lock-doc-9e6a` | — |

---

## Explicitly out of scope (June 2026)

- Word (.docx) **export** for tailored CV / generator preview  
- Referral rewards tied permanently to CV upload (interim only until payment PR)  
- Auto-publishing jobs from bulk dismiss or scraper ingest  
- New notification channels (SMS, email digests as inbox replacement) without scope-lock revision  
- Changing `TIER_PRICES` in code instead of `tier_config` for live pricing  
- Embedding model, vector dim, or matching weight changes ([AGENTS.md](../AGENTS.md) §2 invariants)

---

## Change control

1. Any change to a **Locked product decision** above requires an edit to this file + maintainer ack in the PR description.  
2. New Supabase migrations for notifications must update [NOTIFICATIONS_MIGRATIONS.md](NOTIFICATIONS_MIGRATIONS.md) in the same PR.  
3. New API fields for referrals or notifications require `docs/openapi.yaml` in the same PR.  
4. When `docs/MERGE_TRAIN.md` is added, link it from this file’s **Related docs** table and keep ordering consistent with [migrations.md](migrations.md).
