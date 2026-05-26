# UI/UX Styling Brief — PDF Review & Implementation Plan

**Date:** 2026-05-26  
**Status:** Phases 1–4 implemented on branch `cursor/ui-ux-phased-implementation-0e40`  
**Source:** Styling_UI-UX PDFs (sections 3–5) + review notes PDF

---

## Implementation status (2026-05-26)

| Phase | Scope | Status |
|-------|--------|--------|
| **1** | Job detail: match panel copy, description CSS, scraper stripping, Tailored CV CTA | Done |
| **2** | Tailored CV: green tab strip, cover letter step, job context query, generator redirect | Done |
| **3** | Jobs sidebar presets, MatchCard skills + Learn more | Done |
| **4** | Dashboard light theme + live API data; Profile welcome gradient + green tabs | Done |

### Key files changed

- `JobDetailMatchPanel.tsx`, `JobDescription.tsx`, `jobDetailHtml.ts`, `JobDetailBody.tsx`
- `features/tailored-cv-builder/*` (CoverLetterStep, BuilderHeader, types)
- `JobsSidebar.tsx`, `JobsPageClient.tsx`
- `MatchCard.tsx`, `UserDashboard.tsx`, `DashboardPageClient.tsx`, `DashboardWidgets.tsx`
- `ProfilePageClient.tsx`, `GeneratorTab.tsx`
- `components/ui/SectionEyebrow.tsx`, `globals.css`

### Follow-up round (2026-05-26) — completed

- Full **Experience**, **Education**, **Skills**, **Extras (style)**, and **Review** builder steps with live preview sync
- Preview accordions for WORK EXPERIENCE / EDUCATION / SKILLS sections
- **JobsSidebarMobile** horizontal chips on viewports &lt; lg
- Auth layout tokens (`.auth-grid`, `.auth-form-panel`), responsive headings, `.field` on email input

### Third round (2026-05-26) — completed

- **PDF export:** `print.css` + `printTailoredCv()` on live preview and Review step (browser Save as PDF)
- **Profile hydration:** `mapProfileToDraft()` + `useHydrateBuilderFromProfile()` from `GET /profile` → `cv_sections`
- **Referral card:** `ProfileReferralCard` on profile sidebar (invite link with `ref` query param)

---

## Executive summary

The PDFs are **visual acceptance criteria** comparing current vs target ZedApply styling. See sections below for the original gap analysis and file map.

PNG references: `docs/ui-ux-pdf-extract/` (when present on branch with docs commit).

---

## What the PDFs cover (summary)

### §3 Job Details
Serif title, meta pills, Apply/Save/Cover letter/Tailored CV, share row, skills, rich description (no scraper footers), sticky **Why you're a good match** panel with score ring and skill lists.

### §4 Tailored CV + Cover Letter
Split-pane builder, green underline stepper, live ATS preview, cover letter in the same flow.

### §5 Other pages
Home, Matches, Profile, Auth, Dashboard — cream/green brand; dashboard mock in PDFs 12–15 is light (implemented); PDF 16 dark variant was superseded by light dashboard in §5 extended notes.

---

## Cross-cutting patterns

Use `docs/design_system.md` tokens (`--bg`, `--green-700`, `.btn-primary`, `.tag-green`, `font-display`). Avoid a third primary green.

---

## Testing

```bash
cd apps/frontend && npm test -- --run
```

Job detail snapshots: `src/app/jobs/[id]/__tests__/layout.responsive.test.tsx`  
Scraper strip unit tests: `src/components/jobs/__tests__/jobDetailHtml.test.ts`
