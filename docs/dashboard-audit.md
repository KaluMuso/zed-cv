# Dashboard audit — `/dashboard`

**Date:** 2026-06-03  
**Scope:** Logged-in home — stats, recent matches, CTAs, tier messaging, mobile layout  
**Method:** Code review of `apps/frontend/src/app/dashboard/*` and `components/dashboard/*`, API contract (`GET /matches`, `GET /subscription`), comparison with `/matches` quota handling (`resolveMatchQuotaDisplay`).

## Summary

| Area | Result | Notes |
|------|--------|-------|
| Stats grid | **PASS** (fixed) | Pool count was capped at API default (10); now fetches limit 50 |
| Quota / tier usage | **PASS** (fixed) | Plan card + insights used raw `subscription.matches_used`; unlimited/super tier showed 0 |
| Recent matches | **PASS** (fixed) | Top 3 derived from same widened fetch as stats |
| CTAs | **PASS** | “Your next step”, quick actions, insights links route correctly |
| Tier messaging | **PASS** (fixed) | Upgrade banner always said “Upgrade to starter”; plan card now uses resolved quota copy |
| Mobile layout | **PASS** | Responsive grids and stacked plan/upgrade cards; no blocking issues found |

---

## Route and data flow

- **Page:** `apps/frontend/src/app/dashboard/page.tsx` → `DashboardPageClient`
- **UI:** `UserDashboard` (+ `PlanUsageCard`, `DashboardInsights`, `DashboardWidgets`)
- **Auth:** Unauthenticated users redirect to `/auth?next=/dashboard`
- **Parallel fetch:** profile, matches (limit 50), saved jobs, subscription, preferences

---

## Findings (fixed in this PR)

### 1. Match pool count capped at 10 — **fixed**

**Symptom:** “Total matches” / header “You have N active matches” showed at most 10 for users with more delivered matches.

**Cause:** `matchesApi.get(token)` without `limit` uses backend default `limit=10` (`matches.py`).

**Fix:** `DASHBOARD_MATCHES_FETCH_LIMIT = 50` and `buildDashboardMatchStats()` in `lib/dashboard-stats.ts` (same cap as `/matches` list).

### 2. Quota counters ignored match-list payload — **fixed**

**Symptom:** Super Standard (and some list responses) showed `0` delivered in Plan usage and Insights “Quota used” while matches existed.

**Cause:** Dashboard read only `subscription.matches_used`. Matches page already uses `resolveMatchQuotaDisplay(matchList, subscription)` (see PR #239 pattern).

**Fix:** Pass resolved `matchQuota` into `PlanUsageCard`, `DashboardInsights`, and stat-card “% of quota” detail via `formatQuotaSummary` / `usagePct`.

### 3. Upgrade CTA always targeted Starter — **fixed**

**Symptom:** Paid users on Starter/Professional still saw “Upgrade to starter”.

**Cause:** `UserDashboard` hardcoded `upgradeTier="starter"` for live data.

**Fix:** `getNextUpgradeTier()` in `lib/tier-display.ts`; banner hidden on `super_standard`; labels use `TIER_NAV_LABELS`.

---

## Per-area detail

### Stats grid — PASS (fixed)

| Stat | Source | Binding |
|------|--------|---------|
| Total matches | `buildDashboardMatchStats().poolCount` | Delivered rows (max 50) |
| In pipeline | `applicationsCount` | Saved-job applications or saved jobs fallback |
| Saved jobs | `savedJobs.list().jobs.length` | OK |
| Avg. match score | Mean of fetched match scores | OK; empty → “—” |
| Quota detail | `matchQuota.usagePct` | Only when not unlimited |

### Recent matches — PASS (fixed)

- Top 3 by score from widened match fetch.
- `CondensedJobCard` links to `/jobs/{id}`.
- Empty state links to `/matches` refresh.

### CTAs — PASS

| CTA | Target |
|-----|--------|
| Your next step | `/matches`, `/profile?tab=cv-skills` |
| Quick actions | Profile CV, matches, applications, jobs |
| Insights | `/matches`, `/applications`, `/profile?tab=preferences` |
| Plan upgrade | `/pricing` |
| Super Standard billing | `/settings/billing` |

### Tier messaging — PASS (fixed)

- **PlanUsageCard:** tier label + `formatQuotaSummary` from resolved quota.
- **UpgradeBanner:** current tier display name + next tier in ladder.
- **Insights:** quota pill uses resolved used/limit, unlimited hint when applicable.

### Mobile — PASS

| Pattern | Assessment |
|---------|------------|
| Page padding `px-4 sm:px-6` | Adequate gutters |
| Stats `grid-cols-2 lg:grid-cols-4` | Readable 2-up on phone |
| Main column `lg:grid-cols-[1.4fr_1fr]` | Stacks on small screens |
| Plan / upgrade `flex-col sm:flex-row` | CTA not clipped |
| Condensed cards | Truncate title/company; score badge shrinks |

**Minor (not changed):** Insights “Match performance” band labels are decorative only (no live counts) — acceptable for v1.

---

## Mock vs live mode

`UserDashboard` still supports `MOCK_DASHBOARD` when `liveData` is omitted (Storybook/dev). Production path always passes `liveData` from `DashboardPageClient`.

---

## Tests added

- `lib/__tests__/dashboard-stats.test.ts` — pool count + unlimited quota derivation
- `lib/__tests__/tier-display.test.ts` — upgrade ladder

---

## Smoke checklist (manual)

1. Sign in → `/dashboard` loads without skeleton hang.
2. User with >10 matches: “Total matches” equals full pool (up to 50), not 10.
3. Super Standard with deliveries: plan usage shows non-zero delivered count.
4. Starter user: upgrade banner says “Upgrade to Professional” (not Starter).
5. Narrow viewport (375px): stats 2-column, no horizontal scroll on plan card.
