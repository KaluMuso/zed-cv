# Interview Prep — End-to-End Audit

| Field | Value |
|-------|--------|
| **Date** | 2026-06-03 |
| **Scope** | `/interview-prep/*`, `/api/v1/interview-prep/*`, `/api/v1/interview/*`, matches modal, tier gates, AI calls |
| **P0 fixes** | Shipped in [PR #250](https://github.com/KaluMuso/ZedCV/pull/250) (`cursor/interview-prep-audit-p0-9e6a`) |
| **This doc** | Doc-only follow-up; no new product code unless a new P0 is found |

---

## Executive summary

| Area | Status |
|------|--------|
| Mock interview (`/interview-prep/mock`) | **Works** — Super Standard + `require_tier_access(interview_prep)` |
| Aptitude tests (`/interview-prep/aptitude`) | **Works** if `aptitude_questions` bank has ≥20 rows per pack; pause label fixed in #250 |
| History (`/interview-prep/history`) | **Works** — good empty states; API errors fall back to empty lists |
| Job-scoped prep notes (`POST /interview-prep/generate`) | **Works** — matches CTA wired in #250 via `MatchPremiumActions` |
| Hub (`/interview-prep`) | **Works** — `InterviewPrepGate` + hub error/retry UI (#250) |
| Stub hub modules (quizzes, dress code, skill build-ups) | **Placeholder** — honest “Coming in v2” on cards |
| **New P0 gaps (post-#250 audit)** | **None** |

---

## PR #250 alignment (shipped)

These items were broken before #250; they are fixed on `master` as of commit `5d1e0da`.

| #250 change | Files | Behavior |
|-------------|-------|----------|
| **Matches → prep modal reachable** | `MatchPremiumActions.tsx`, `MatchCard.tsx`, `MatchesPageClient.tsx` | `onInterviewPrepClick` → `setPrepFor(match)` → `InterviewPrepModal` calls `POST /interview-prep/generate` |
| **Match card tier UX** | `MatchPremiumActions.tsx` | Professional+: tailor + cover letter; third column is **Interview prep** (Super Standard) or `UpgradeButton` (`unlock_prep`) |
| **Hub tier gate** | `interview-prep/page.tsx`, `InterviewPrepGate.tsx` | Hub wrapped in same gate as mock/aptitude/history (`TierGate` feature `unlock_prep`) |
| **Hub load errors** | `interview-prep/page.tsx` | Non-403 failures show “Could not load…” + **Try again** (no blank `null` render) |
| **Aptitude pause label** | `interview-prep/aptitude/page.tsx` | Ghost button: **Save & pause** (was misleading “Submit and exit” while calling `pauseSession`) |

### MatchPremiumActions matrix (post-#250)

| User tier | Tailor CV / Cover letter | Interview prep column |
|-----------|--------------------------|------------------------|
| Below Professional | Single `UpgradeButton` (`tailor_cv`) | Hidden (no `onInterviewPrepClick` on card) |
| Professional | Buttons shown | `UpgradeButton` (`unlock_prep` → Super Standard) |
| Super Standard | Buttons shown | **Interview prep** button → modal |
| Loading | Skeleton pulse | — |

`data-testid="match-interview-prep"` on the Super Standard button.

### InterviewPrepGate (all sub-routes + hub)

- Auth redirect: `/auth?next=<nextPath>` when logged out.
- Tier fallback: upgrade copy + `/pricing#super_standard` + “Back” to `/interview-prep`.
- Feature key: `unlock_prep` → `FEATURE_TIER_MAP.unlock_prep` = `super_standard`.

Used on: `/interview-prep`, `/mock`, `/aptitude`, `/history`.

---

## Routes & API map

| User route | Backend | Tier gate |
|------------|---------|-----------|
| `/interview-prep` | `GET /api/v1/interview-prep` | `_require_super_standard` in `interview_prep.py` |
| `/interview-prep` (unused stub) | `POST /api/v1/interview-prep` | Same — placeholder text only; **no UI calls this** |
| Matches → prep modal | `POST /api/v1/interview-prep/generate` | `_require_super_standard` (+ superadmin bypass) |
| `/interview-prep/mock` | `POST /api/v1/interview/mock/start`, `.../answer` | `require_tier_access(FEATURE_INTERVIEW_PREP)` |
| `/interview-prep/aptitude` | `GET .../interview/aptitude/pack/{pack}`, `POST .../score` | Same |
| `/interview-prep/history` | `GET /api/v1/interview/history` | Same |

OpenAPI: `docs/openapi.yaml` paths under `/interview-prep` and `/interview/*` (mock, aptitude, history).

**Implementation note:** Overview + `/generate` use ad-hoc `_require_super_standard`; mock/aptitude/history use centralized `require_tier_access`. Both restrict to **super_standard** only — behavior aligned, code duplicated (backlog #1).

---

## What works

1. **Mock interview** — Role picker (match titles or custom), 7 STAR questions, per-answer feedback in chat bubbles, final summary in `interview_sessions`, link to history.
2. **Aptitude** — Packs `numerical` | `verbal` | `abstract`; 20 questions; pack timer; `localStorage` resume; submit → score + percentile row in `aptitude_scores`.
3. **History** — Lists mock sessions + aptitude runs; empty states with links to mock/aptitude.
4. **Job-scoped generate** — Zambia-focused markdown brief; `ai_cache` keyed `interview_prep:{cv_id}:{job_id}`; rate limit 5/min on generate.
5. **Modal UX** — `rehype-sanitize` on markdown; 403 → pricing CTA; copy-to-clipboard; loading/error states.
6. **Backend tests** — `test_interview_prep_tier_gate.py` pins non–Super Standard → 403 on `/generate`; `test_tier_gating.py` covers `FEATURE_INTERVIEW_PREP`.
7. **Discovery** — `InterviewPrepNav`, mobile “More” sheet entry, purple accent when tier-locked (funnel).

---

## Shipped fixes (PR #250) — was broken

| Issue | Severity | Resolution |
|-------|----------|------------|
| `setPrepFor` never called — modal unreachable from matches | **P0** | Wired through `MatchPremiumActions` / `MatchCard` / `MatchesPageClient` |
| Hub without `InterviewPrepGate` — low tiers got toast + redirect | **P0** | Hub uses `InterviewPrepGate` like sub-routes |
| Hub returned `null` on non-403 load errors | **P0** | Inline error + **Try again** |
| Aptitude “Submit and exit” called `pauseSession` | **P0** | Label **Save & pause** |

---

## Still broken / incomplete (not P0)

| Issue | Severity | Notes |
|-------|----------|-------|
| History rows not clickable | P2 | No mock transcript detail page |
| Aptitude bank empty in env | Ops | `GET .../aptitude/pack/{pack}` → 503; admin seed required |
| `POST /interview-prep` stub | P3 | Backend returns `[Bwana Interview — placeholder]`; no frontend caller |
| Job detail page | P3 | Prep only from matches modal, not `/jobs/[id]` |
| Duplicate tier gate helpers | P3 | `_require_super_standard` vs `require_tier_access` |

---

## Copy & naming audit

| Location | Current copy | Issue | Recommendation |
|----------|----------------|-------|----------------|
| `interview_prep.py` stub `POST` | `[Bwana Interview — placeholder]` | Bracket placeholder tone | Remove brackets before GA |
| Aptitude results UI | `Percentile vs Zambian benchmark (placeholder)` | Honest but weak | Replace when cohort stats exist |
| Hub subhead | `More modules roll out in v2` | OK for beta | Update when v2 ships |
| Hub / overview API | Product name **Bwana Interview** | Consistent | Keep |
| Match button | **Interview prep** | Clear | Keep |
| `InterviewPrepGate` | “mock interviews, aptitude practice, and tailored prep briefs” | Accurate | Keep |
| Pricing / legacy docs | “Interview Call” | Drift vs product name | Align marketing to “Bwana Interview” / “Interview prep” |
| `bwana_faq.py` pricing intent | “quizzes, dress code, likely questions” on Super Standard | Implies live modules | Clarify mock + aptitude live; rest v2 |
| Mock chat | `STAR X/10 — {feedback}` inline | Readable but dense | Optional: separate feedback card (UX backlog) |
| Test docstring `test_interview_prep_tier_gate.py` | “Interview Call button” | Stale name | Rename in test comment when touching file |

---

## Tier gating review

| Layer | Mechanism | Effective tier |
|-------|-----------|----------------|
| `POST /interview-prep/generate` | `_require_super_standard` | `super_standard` |
| `GET /interview-prep` | `_require_super_standard` | `super_standard` |
| `/interview/*` (mock, aptitude, history) | `require_tier_access(FEATURE_INTERVIEW_PREP)` | `super_standard` (`TIER_FEATURE_GATES`) |
| Frontend sub-routes + hub | `InterviewPrepGate` → `TierGate` `unlock_prep` | `super_standard` |
| Match card prep | `tierAtLeast(tier, unlock_prep)` | Button vs `UpgradeButton` |
| Nav / mobile tab | Visible to all authenticated | Intentional funnel |
| Superadmin | Bypass on `/generate` only (`is_superadmin`) | Ops |

**Professional tier:** Tailor CV + cover letter (`professional`); interview prep correctly requires **Super Standard** (K500/mo). #250 surfaces upgrade CTA on match cards for Professional users.

---

## AI & cost

| Feature | Service | Cache | Rate limit |
|---------|---------|-------|------------|
| `/interview-prep/generate` | OpenRouter (`settings.llm_model`) | `ai_cache` `cache_type=interview_prep` | 5/min |
| Mock start/answer/summary | `bwana_interview.py` | Session rows in DB | 10–20/min per route |
| Stub `POST /interview-prep` | No LLM | — | 10/min |

Generate prompt: Zambia context, role/company, markdown sections. Degrades via `degraded_llm_result` when circuit open.

---

## Error states

| Scenario | Handling |
|----------|----------|
| No CV | 422 from `/generate` — modal shows API message |
| Wrong tier | 403 — modal tier lock + pricing link |
| Aptitude bank &lt; 20 questions | 503 + admin seed hint — toast on frontend |
| LLM / provider down | 503 — toast |
| History API fail | Silent → empty lists (acceptable) |
| Hub overview fail | Error panel + retry (#250) |
| Logged out | `InterviewPrepGate` → `/auth?next=...` |

---

## Test coverage

| Area | Tests | Gap |
|------|-------|-----|
| `/generate` tier gate | `test_interview_prep_tier_gate.py` | — |
| `FEATURE_INTERVIEW_PREP` | `test_tier_gating.py` | — |
| `TierGate` / `unlock_prep` | `TierGate.test.tsx` | — |
| `MatchCard` | `MatchCard.test.tsx` | Mocks `MatchPremiumActions` — **does not assert** `onInterviewPrepClick` / prep button |
| Hub gate / aptitude label | — | No dedicated Vitest (manual smoke) |
| E2E mock flow | — | Backlog |

No new P0 found: backend gate is tested; frontend wiring is straightforward props — highest risk was unwired callback (fixed in #250).

---

## Enhancement backlog (ranked)

1. **Unify tier gate** — Use `require_tier_access` on all `/interview-prep/*` routes; remove `_require_super_standard`.
2. **WhatsApp prep delivery** — Digest snippet + deep link (WAHA stack; Super Standard differentiator).
3. **Mock session detail** — Clickable history → full transcript review.
4. **Real aptitude percentiles** — Replace placeholder benchmark; cohort stats in DB.
5. **PDF export of prep kit** — Mentioned in `ZED_CV_BIRDS_EYE_VIEW.md`; not built.
6. **Ship v2 hub modules** — Quizzes, dress code, skill build-ups (stub API + “Coming in v2” cards).
7. **Naming consistency** — Bwana Interview / Interview prep / Interview Call across pricing, FAQ, tests.
8. **Remove or wire stub `POST /interview-prep`** — Dead API surface today.
9. **Professional hub preview** — Teaser vs hard gate (marketing decision).
10. **Vitest for `MatchPremiumActions`** — Prep button + upgrade CTA by tier.
11. **Admin aptitude bank health** — Row counts per pack on admin dashboard.
12. **Prep from job detail** — Parity with matches modal.
13. **E2E smoke** — Playwright: hub → mock start (mocked API).

---

## Smoke checklist (post-deploy)

- [ ] **Super Standard:** hub loads; mock + aptitude + history work; matches **Interview prep** opens modal and generates notes.
- [ ] **Professional:** tailor + cover work; match card shows **upgrade** for prep (not full prep button).
- [ ] **Free / Starter:** `/interview-prep` shows `InterviewPrepGate` upgrade UI (not blank screen).
- [ ] **Aptitude:** pause button reads **Save & pause**; submit requires 20 answers.
- [ ] **API:** `POST /interview-prep/generate` returns 403 for starter/professional JWTs.

---

## Key files (reference)

| Layer | Path |
|-------|------|
| Hub | `apps/frontend/src/app/interview-prep/page.tsx` |
| Gate | `apps/frontend/src/app/interview-prep/_components/InterviewPrepGate.tsx` |
| Matches CTA | `apps/frontend/src/components/matches/MatchPremiumActions.tsx` |
| Modal | `apps/frontend/src/app/matches/_components/InterviewPrepModal.tsx` |
| Generate API | `apps/backend/app/api/v1/interview_prep.py` |
| Mock/aptitude API | `apps/backend/app/api/v1/bwana_interview_routes.py` |
| LLM generate | `apps/backend/app/services/interview_prep.py` |
| Migrations | `infra/supabase/migrations/057_interview_prep.sql`, `005_super_standard_tier_and_interview_prep.sql` |
| Tier map (FE) | `apps/frontend/src/lib/tier-features.ts` |
| Tier map (BE) | `apps/backend/app/core/tier_gating.py` |
