# Interview Prep — End-to-End Audit

**Date:** 2026-06-03  
**Scope:** `/interview-prep/*`, `/api/v1/interview-prep/*`, `/api/v1/interview/*`, matches modal, tier gates, AI calls.

---

## Executive summary

| Area | Status |
|------|--------|
| Mock interview (`/interview-prep/mock`) | **Works** (Super Standard + backend gate) |
| Aptitude tests (`/interview-prep/aptitude`) | **Works** if question bank seeded; UX label bug fixed in P0 |
| History (`/interview-prep/history`) | **Works** with good empty states |
| Job-scoped prep notes (`POST /interview-prep/generate`) | **Backend works**; **matches UI was broken** (button never wired) — fixed in P0 |
| Hub (`/interview-prep`) | **Tier UX inconsistent** — fixed in P0 with `InterviewPrepGate` |
| Stub modules (quizzes, dress code, etc.) | **Placeholder only** — honest “Coming in v2” copy |

---

## Routes & API map

| User route | Backend | Tier gate |
|------------|---------|-----------|
| `/interview-prep` | `GET/POST /api/v1/interview-prep` | Super Standard (`_require_super_standard`) |
| `/interview-prep/mock` | `POST /api/v1/interview/mock/start`, `.../answer` | `require_tier_access(interview_prep)` |
| `/interview-prep/aptitude` | `GET .../aptitude/pack/{pack}`, `POST .../score` | Same |
| `/interview-prep/history` | `GET /api/v1/interview/history` | Same |
| Matches → prep modal | `POST /api/v1/interview-prep/generate` | Super Standard |

**Note:** Overview/generate use a custom `_require_super_standard` in `interview_prep.py`; mock/aptitude/history use centralized `require_tier_access(FEATURE_INTERVIEW_PREP)`. Both restrict to `super_standard` only — behavior aligned, implementation duplicated (backlog).

---

## What works

1. **Mock interview flow** — Role picker (from matches or custom), 7 STAR questions, per-answer feedback, final summary persisted to `interview_sessions`, history list.
2. **Aptitude flow** — Three packs, 20 questions, timer, localStorage resume, score + percentile stored in `aptitude_scores`.
3. **History empty states** — Links to mock/aptitude when lists are empty; silent fallback to empty arrays on API error.
4. **Sub-route tier gate** — `InterviewPrepGate` + `TierGate` feature `unlock_prep` → Super Standard; clear upgrade copy and `/pricing#super_standard` link.
5. **Matches modal (when opened)** — Markdown render + `rehype-sanitize`, 403 → pricing CTA, 422 CV missing surfaced via API message, ai_cache for `/generate`.
6. **Backend tier tests** — `test_interview_prep_tier_gate.py` pins non–Super Standard → 403 on `/generate`.
7. **Nav discovery** — `InterviewPrepNav`, mobile tab “More” sheet, purple accent when tier-locked (premium tease).

---

## Broken / fixed in P0 (this PR)

| Issue | Severity | Fix |
|-------|----------|-----|
| `setPrepFor` never called — Interview Prep modal on matches unreachable | **P0** | Wire `onInterviewPrepClick` through `MatchCard` → `MatchPremiumActions` |
| Hub had no `InterviewPrepGate`; low tiers got toast + redirect instead of upgrade UI | **P0** | Wrap hub in `InterviewPrepGate` |
| Hub returned `null` on non-403 load errors (blank screen) | **P0** | Error empty state + retry |
| Aptitude “Submit and exit” button called `pauseSession` (misleading) | **P0** | Label → “Save & pause” |

---

## Unprofessional / confusing copy (not P0)

| Location | Copy | Recommendation |
|----------|------|----------------|
| `interview_prep.py` stub POST | `[Bwana Interview — placeholder]` | Remove bracket placeholder tone before GA |
| Aptitude results | `Percentile vs Zambian benchmark (placeholder)` | Replace when real benchmark data exists |
| Hub | `More modules roll out in v2` | OK for beta; update when v2 ships |
| Pricing/marketing | `Interview prep notes (Interview Call)` | Align naming: “Bwana Interview” vs “Interview Call” |
| `InterviewPrepGate` | “Upgrade for mock interviews…” | Accurate; keep |
| Mock feedback bubbles | `STAR X/10 — {feedback}` as chat message | Consider separate feedback card (UX backlog) |
| `bwana_faq.py` | Lists quizzes/dress code as live | Update FAQ to match mock/aptitude/live vs v2 |

---

## Tier gating review

| Layer | Behavior |
|-------|----------|
| Backend `interview_prep` routes | Super Standard only (+ superadmin bypass on generate) |
| Backend `interview/*` routes | `FEATURE_INTERVIEW_PREP` → `super_standard` |
| Frontend sub-pages | `InterviewPrepGate` / `unlock_prep` |
| Frontend hub (before P0) | API-only gate → redirect |
| Frontend matches (before P0) | No button; modal dead code |
| Nav | Visible to all authenticated users (intentional funnel) |

**Professional tier:** Can use tailor CV + cover letter; interview prep correctly requires Super Standard. P0 adds visible “Interview prep” on match cards with `UpgradeButton` when on Professional.

---

## AI calls

| Feature | Model path | Cache | Rate limit |
|---------|------------|-------|------------|
| `/interview-prep/generate` | OpenRouter via `settings.llm_model` | `ai_cache` keyed by cv+job | 5/min |
| Mock start/answer/summary | `bwana_interview` service | Per-session DB | 10–20/min |
| Stub `POST /interview-prep` | No LLM | — | 10/min |

Prompt for generate is solid (Zambia-specific, markdown sections). Degraded path uses `degraded_llm_result` when circuit open.

---

## Error states

| Scenario | Current handling |
|----------|------------------|
| No CV | 422 from `/generate` — modal shows message |
| Wrong tier | 403 — modal tier lock UI |
| Aptitude bank &lt; 20 rows | 503 with admin seed hint — toast on frontend |
| LLM down | 503 ValueError messages — toast |
| History API fail | Empty lists (no error toast) — acceptable |
| Hub load fail | **Fixed:** inline error + retry |

---

## Enhancement backlog (ranked)

1. **Unify tier gate implementation** — Use `require_tier_access` on all `/interview-prep/*` routes; drop duplicate `_require_super_standard`.
2. **WhatsApp delivery of prep brief** — Digest snippet + link (fits product WAHA stack; Super Standard differentiator).
3. **Mock interview session detail page** — History rows are not clickable; no transcript review.
4. **Real aptitude percentiles** — Replace placeholder benchmark; store cohort stats.
5. **PDF export of prep kit** — Mentioned in `ZED_CV_BIRDS_EYE_VIEW.md`; not built.
6. **Ship v2 hub modules** — Quizzes, dress code, skill build-ups (currently stub + “Coming in v2”).
7. **Consolidate naming** — “Bwana Interview” / “Interview prep” / “Interview Call” across pricing, nav, FAQ.
8. **Hub: remove dead `loadPlaceholder`** — POST stub unused in UI after v2 cards.
9. **Professional-tier hub preview** — Teaser content without full API (marketing) vs hard gate.
10. **E2E tests** — Vitest for hub gate; Playwright smoke for mock flow.
11. **Admin health for aptitude bank** — Surface row counts on admin dashboard.
12. **Interview prep from job detail page** — Only matches modal today.

---

## Smoke checklist (post-deploy)

- [ ] Super Standard user: hub loads, mock + aptitude + history work
- [ ] Professional user: match card shows upgrade for prep; tailor/cover still work
- [ ] Free user: `/interview-prep` shows upgrade gate (not blank)
- [ ] Matches: “Interview prep” opens modal and generates notes
- [ ] `POST /interview-prep/generate` returns 403 for starter/professional

---

## Files touched in P0 PR

- `apps/frontend/src/components/matches/MatchPremiumActions.tsx`
- `apps/frontend/src/components/matches/MatchCard.tsx`
- `apps/frontend/src/app/matches/MatchesPageClient.tsx`
- `apps/frontend/src/app/interview-prep/page.tsx`
- `apps/frontend/src/app/interview-prep/aptitude/page.tsx`
- `docs/interview-prep-audit.md`
