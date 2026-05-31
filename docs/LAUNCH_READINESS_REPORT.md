# ZedApply — Launch Readiness Report

**Date:** 2026-05-31  
**Branch:** `cursor/premium-saas-polish-5cc5`  
**Scope:** Premium SaaS polish pass (post UX modernization). No API or business-logic changes.

---

## Executive summary

| Dimension | Score (1–10) | Notes |
| --- | ---: | --- |
| Visual consistency | 8.5 | Unified `cn-ui` helpers; `/jobs` and `/matches` migrated to `btnClass` / `surfaceCardClass` / `tagClass` |
| Design system migration | 8.5 | Legacy `.btn`/`.card`/`.tag` retained as aliases; secondary pages only |
| Dashboard experience | 8.5 | Live insights, funnel bars, quota trends, theme-safe widgets |
| Admin tables | 8.5 | Jobs, Matches, Billing (payments + subs), Subscriptions tab: sort, export, pagination, empty states |
| Conversion / trust | 8.0 | `TrustSection` on home + pricing; signup security line; `/security` page (prior pass) |
| Accessibility | 7.5 | `aria-sort` on match sort; labeled apply/status modals; Kanban drag handles; focus-visible on cn-ui buttons |
| Mobile | 8.0 | 320px padding on jobs/matches; Kanban snap scroll + 44px drag handles; match actions flex row |
| **Overall launch readiness** | **8.2 / 10** | **Soft launch ready**; replace TrustSection placeholders before paid ads |

---

## Completed improvements (this pass)

### Priority 1 — Design system migration (partial)

- Added `apps/frontend/src/lib/cn-ui.ts`: `btnClass()`, `tagClass()`, `surfaceCardClass`.
- Migrated high-traffic surfaces: homepage hero CTAs, pricing FAQ cards, dashboard CTAs, admin uses shadcn `Button`/`Card`.
- `globals.css`: legacy `.btn`/`.card`/`.tag` documented as compatibility layer; focus-visible on `.btn`.

### Priority 2 — Visual consistency

- Dashboard widgets (`ProfileCompletenessRing`, `RecentActivityTimeline`, `UpgradeBanner`) moved from hardcoded zinc palette to CSS variables.
- Skill chips on condensed match cards use `tagClass("green")`.
- Homepage pricing teaser cards use `surfaceCardClass`.

### Priority 3 — Dashboard premium experience

- `DashboardInsights`: trend pills (match pool, avg/best score, quota), application funnel bars, match performance guidance.
- `DashboardPageClient` builds funnel from saved-job application statuses.

### Priority 4 — Enterprise admin tables

| Tab | Sort | Filter | Pagination | Export | Empty state |
| --- | --- | --- | --- | --- | --- |
| Jobs | ✓ (client, per page) | ✓ server | ✓ | ✓ CSV | ✓ |
| Matches | ✓ | ✓ min score | ✓ | ✓ | ✓ |
| Billing — subs | ✓ | ✓ tier | ✓ | ✓ | ✓ |
| Billing — payments | ✓ | ✓ status/provider | ✓ | ✓ | ✓ |
| Subscriptions | ✓ | — | — (50 rows) | ✓ | ✓ |
| Users | ✓ (prior pass) | ✓ tier | ✓ | ✓ | ✓ |

Shared: `AdminTableTools.tsx`, `useClientTable.ts`.

### Priority 5 — Conversion optimization

- `TrustSection`: trust pillars, placeholder logos/testimonials, employer CTA.
- Integrated on **homepage** (before FAQ) and **pricing** (before FAQ).
- **Auth signup**: shield + link to `/security`.

### Priority 6 — Accessibility (partial)

- Sortable column headers expose `aria-sort`.
- Button focus rings (`focus-visible:ring-primary-500/30`).
- Auth security copy is readable at 320px.
- **Not run in CI:** axe-core sweeps at 320/768/1280/1920 — recommend one manual pass before marketing launch.

### Priority 7 — Mobile (inherits prior pass)

- Bottom tab bar, interview prep dropdown, theme-safe jobs sticky filter (UX modernization).
- Admin tables: horizontal scroll; touch targets ≥44px on primary actions.

---

## Remaining issues (non-blocking)

| Issue | Severity | Effort |
| --- | --- | --- |
| `jobs/[id]` detail page still uses legacy `.btn` / `.tag` | Low (visual only) | Small — mirror `btnClass` migration |
| Match performance bands in dashboard are illustrative (not live counts) | Low | Requires read-only API aggregate (out of scope) |
| Placeholder testimonials/logos in `TrustSection` | Low | Content/marketing |
| axe / keyboard audit not automated | Medium | Add `@axe-core/playwright` or Lighthouse CI |
| Admin Jobs: sort is client-side on current API page only | Low | Expected until server sort |
| Bulk actions on admin tables | Low | Not required for launch |

---

## Risk assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Legacy CSS drift on secondary pages | Medium | Low | Migrate incrementally via `btnClass` / `surfaceCardClass` |
| Placeholder trust content perceived as fake | Medium | Medium | Replace with real logos/quotes before paid ads |
| Payment/Lenco env misconfig in prod | Low | High | Existing billing health panel + smoke test |
| WCAG contrast on copper gradient banners | Low | Medium | Spot-check dark mode on dashboard upgrade banner |

---

## Pre-launch checklist

- [ ] Replace `TrustSection` placeholders with verified assets
- [ ] Run axe DevTools on `/`, `/pricing`, `/auth`, `/dashboard`, `/matches`, `/jobs` at 320px and 1280px
- [ ] Keyboard-only pass: nav, Cmd+K, modals, match sort buttons, Kanban drag handles
- [ ] Manual: `/jobs` and `/matches` at 320px — filter bar scroll, match action row, dark mode upgrade banner contrast
- [ ] Confirm Vercel env: `NEXT_PUBLIC_API_URL`, Lenco public key
- [ ] Smoke: OTP → CV upload → matches → pricing upgrade (staging)
- [ ] Merge after CI green (frontend tests + lint)

---

## Verification commands

```bash
cd apps/frontend && npm run lint
cd apps/frontend && npm test
```

---

## Related work

- UX modernization: PR #188 (`cursor/ux-modernization-production-5cc5`)
- Desktop UI audit: structured report (audit-only, no code)
