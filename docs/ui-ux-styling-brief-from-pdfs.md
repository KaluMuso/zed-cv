# UI/UX Styling Brief — PDF Review & Implementation Plan

**Date:** 2026-05-26  
**Source:** `Styling_UI-UX-06-08` through `Styling_UI-UX-16-16` (7 PDFs, 11 pages)  
**Product:** ZedApply (Zed CV) web app — `apps/frontend/`  
**Related docs:** [`design_system.md`](./design_system.md), [`frontend_visual_audit.md`](./frontend_visual_audit.md)

Page renders extracted for reference live in [`docs/ui-ux-pdf-extract/`](./ui-ux-pdf-extract/).

---

## Executive summary

The PDFs are **visual acceptance criteria** (before/after mockups), not a full design system. They define three major workstreams:

1. **Job Details** — Match a cleaner, editorial layout (ZedApply reference) with rich description typography, a prominent match score card, and **no scraper/source chrome** in the user-facing description.
2. **Tailored CV + Cover Letter** — A split-pane builder with step progress, live ATS-style preview, and a **unified document output** experience (CV + generated cover letter in one flow).
3. **Other pages** — Align **Home**, **Matches**, **Profile**, **Auth**, and **Dashboard** with the same green/cream brand, card surfaces, and typography rhythm already used on marketing and job detail screens.

Much of the **Job Details** and **Tailored CV builder shell** already exists in code; the gap is polish, content normalization, cover-letter integration, and bringing secondary pages up to the same visual bar.

---

## What the PDFs show (page-by-page)

### PDF 06–08 — Job Details Page (§3)

| Page | Content |
|------|---------|
| **p1** | Side-by-side: **current** ZedApply job detail (left) vs **target** ZedApply layout (right). Target has larger serif title, company as subtitle, pill row (deadline, salary, type, location), green **Apply** CTA, outline **Save**, sparkle **Generate cover letter**, **Share** row, **Required skills** chips, and a right-hand **Match score** card (circular ring, semantic/skills/location breakdown, matched & missing skill lists). |
| **p2** | Second reference (ZedApply) emphasizing **full job description** body: section headings (`JOB PURPOSE`, `KEY RESPONSIBILITIES`, `REQUIREMENTS`, `LOCATION`, `METHOD OF APPLICATION`) with clear vertical spacing; bullet lists; readable paragraph blocks. |
| **p3** | **Note:** Include full descriptions with this styling and subtitles/spacing. **Do not** show scraping sites, “view original posting”, or similar source attribution in the rendered description. |

**Reference job in brief:** Sales Representative at Gastec Trading and Supply.

### PDF 09–11 — Tailored CV (§4) & Other pages (§5)

| Page | Content |
|------|---------|
| **p1** | **Tailored CV** screen: header “Tailored CV for [Job Title] at [Company]”, horizontal **stepper** (Basics → Experience → Education → Skills → Review), left form (“Basics” with name, email, phone, location, headline, summary + **Next**), right **live preview** pane styled like a printed CV (serif, section rules). |
| **p2** | Same layout continued (preview content / later steps implied). |
| **p3** | Instruction: **Include the Tailored CV and the Generated Cover Letter** in this experience. Section **5 Other pages** lists additional screens (see PDFs 12–16). |

### PDF 12 — Home (landing)

- Hero: “Find jobs that actually fit your CV” + subcopy + **Get started free** (green) + **See how it works** (outline).
- Right: floating **match score** card mockup (~87%, skills breakdown).
- Below: **Four steps** strip (Upload CV → Get matched → Apply smarter → Land the role) with icons on cream cards.
- **Pricing** section: four tier cards (Free, Starter highlighted, Professional, Super Standard) with K prices and feature bullets.
- **FAQ** accordion.
- Footer with Zambia flag motif, legal links.

### PDF 13 — Matches

- Title **Your matches** + subtitle + **Refresh matches** (outline) + **Preferences** (ghost).
- Filter chips: All, 80%+, 60%+, Closing soon.
- Sort: **Best match** dropdown.
- Match **cards**: company avatar, title, company, location, salary band, **circular score**, skill chips (green matched / muted missing), **View job** + **Apply** + bookmark.
- Sticky feel, cream background, green primary actions.

### PDF 14 — Profile

- **Welcome banner** (green gradient): avatar, name, tier badge, “Member since …”, **Upgrade plan** CTA.
- Tab row: CV & Skills | CV Analysis | CV Generator | Preferences.
- **CV & Skills** tab: upload zone, parsed CV summary card, skills editor with suggestions, **Save changes**.

### PDF 15 — Auth (sign-in)

- Split layout: left **Login** form (phone/email toggle, Zambian phone field, consent checkbox, **Send OTP**), right brand panel (“Your CV. Matched to real jobs.” + bullet value props).
- Cream/warm neutrals, green primary button, copper accents on links.

### PDF 16 — Dashboard

- Dark **analytics-style** dashboard (contrast to rest of app): welcome row, stat tiles (Total matches, Applied, Saved jobs, Avg. score), **Recent matches** list, **Quick actions** sidebar (Upload CV, Refresh matches, View all jobs).
- This is the **only** screen in the set that uses a dark chrome; everything else is cream/light.

---

## Cross-cutting design patterns (from all PDFs)

| Pattern | Target look | Current tokens (already in `globals.css`) |
|---------|-------------|-------------------------------------------|
| Page background | Warm cream `#FAFAF7` | `--bg`, `--background` |
| Primary CTA | Deep green, full-width on mobile | `--green-700`, `.btn-primary` |
| Secondary CTA | Outline / ghost | `.btn-outline`, `.btn-ghost` |
| Display type | Serif (Crimson) for H1/H2 | `--font-display`, `font-display` |
| UI type | Inter for labels, pills, body | `--font-body` |
| Meta pills | Rounded-full, subtle border | `MetaPill` in `JobDetailBody.tsx` |
| Skill chips | Mono tags; green tint for matched | `.tag`, `.tag-mono`, `.tag-green` |
| Match ring | Circular score + breakdown rows | `ScoreRing`, `JobDetailMatchPanel` |
| Section labels | Uppercase, tracked, muted | `SectionTitle` in `JobDetailBody.tsx` |
| Cards | White surface, soft shadow, `rounded-xl` | `.card`, `--surface`, `--shadow-md` |
| Step progress | Numbered circles + connector line | `StepProgress`, `BuilderHeader` |

**Important:** PDFs assume **ZedApply** branding throughout. The codebase already uses this palette; avoid introducing a third green (see `frontend_visual_audit.md` §1.3).

---

## Gap analysis: current app vs PDF targets

### Job Details — **mostly built, needs polish**

| Aspect | Current implementation | Gap vs PDF |
|--------|------------------------|------------|
| Route | `src/app/jobs/[id]/page.tsx` → `JobDetailClient` → `JobDetailBody` | — |
| Header, pills, CTAs | `JobDetailBody.tsx` | Align spacing/typography to mock (title size, pill order). |
| Match panel | `JobDetailMatchPanel.tsx` | Verify breakdown labels match PDF (semantic/skills/location). |
| Description | `JobDescription.tsx` + `plainTextToMarkdown` | Headings exist; may need stronger spacing and scraper-line stripping. |
| Scraper chrome | Partially stripped in `stripDescriptionHtml` | PDF explicitly forbids source sites in body — extend normalization. |
| Share / skills | Present | — |

### Tailored CV — **shell exists, content incomplete**

| Aspect | Current implementation | Gap vs PDF |
|--------|------------------------|------------|
| Route | `(app)/profile/cv-builder/page.tsx` → `TailoredCvBuilder` | Entry may be only via `/profile/cv-builder`; PDF shows job-context header (“for [Job] at [Company]”). |
| Stepper + split pane | `BuilderHeader`, `BasicsStepForm`, `LivePreviewPane`, `builder.css` | Steps 2–5 are placeholders (`StepPlaceholder.tsx`). |
| Cover letter | `CoverLetterModal` on job detail only | PDF wants **cover letter inside** tailored CV flow, not isolated modal. |
| Preview styling | `AtsLivePreview.tsx`, `.tailored-cv-paper` | Close to PDF; tune margins/fonts to match mock exactly. |

### Other pages — **mixed maturity**

| Page | Current | Gap vs PDF |
|------|---------|------------|
| Home | `HomePageClient.tsx`, `components/marketing/*` | Largely aligned; verify four-step icons and pricing highlight card. |
| Matches | `MatchesPageClient.tsx` (~995 lines) | Functionally rich; visual pass for card layout, filter chips, score ring consistency. |
| Profile | `ProfilePageClient.tsx` + tabs | Welcome banner exists; match green gradient and tab underline style from PDF. |
| Auth | `AuthPageClient.tsx`, `LoginPage`, `OtpPage` | Split layout exists; compare to PDF spacing and right-panel copy. |
| Dashboard | `dashboard/page.tsx` + `UserDashboard` | **Largest visual mismatch** — `bg-zinc-950` dark theme vs light PDF set; decide if PDF 16 is intentional dark mode or outdated. |

---

## Where to implement (file map)

### 1. Job Details (Priority: P0)

```
apps/frontend/src/
├── app/jobs/[id]/
│   ├── page.tsx              # SSR metadata, passes job to client
│   └── JobDetailClient.tsx   # Loads match + saved state
├── components/
│   ├── JobDetailBody.tsx     # Layout orchestrator — primary edit surface
│   └── jobs/
│       ├── JobDescription.tsx       # Markdown typography + heading rules
│       ├── JobDetailMatchPanel.tsx  # Score ring + breakdown
│       ├── JobDetailSimilarMatches.tsx
│       ├── jobDetailHtml.ts         # stripDescriptionHtml — extend scraper stripping
│       └── CoverLetterModal.tsx     # Keep; link from CTA row
```

**Suggested changes**

- **Content pipeline (backend + frontend):** Add a `normalizeJobDescription()` pass that removes lines matching scraper footers (`view on`, `source:`, `posted via`, known board domains). Run in `stripDescriptionHtml` and/or at scrape/ingest time in `apps/backend`.
- **Typography:** In `JobDescription.tsx`, increase `mt` between sections to match PDF (e.g. `mt-8` after major `h3`), ensure `whitespace-pre-line` on paragraphs preserves blank lines from source text.
- **Expand `MAIN_SUBTITLE_HEADINGS`** in `JobDescription.tsx` for Zambian job boards: `duties`, `responsibilities`, `experience`, `education`, `competencies`, `how to apply`, etc.
- **Hide from UI (not delete from DB):** Do not render `source_url`, scraper site names, or “original posting” blocks in `JobDetailBody` — PDF §3.3.
- **Layout tweak:** Consider moving match panel **above the fold on mobile** (PDF shows score card very prominent); today `order-1` on aside stacks match panel first on mobile — verify against product intent.

### 2. Tailored CV + Cover Letter (Priority: P0–P1)

```
apps/frontend/src/
├── app/(app)/profile/cv-builder/page.tsx
├── features/tailored-cv-builder/
│   ├── TailoredCvBuilder.tsx
│   ├── BuilderHeader.tsx          # Job context title + stepper
│   ├── BasicsStepForm.tsx
│   ├── StepPlaceholder.tsx        # Replace with real steps
│   ├── LivePreviewPane.tsx
│   ├── AtsLivePreview.tsx
│   ├── builder.css
│   ├── store.ts                   # Add jobId, coverLetter draft state
│   └── types.ts
├── app/profile/_tabs/GeneratorTab.tsx   # May link into builder
└── components/jobs/CoverLetterModal.tsx # Refactor → shared generator panel
```

**Suggested changes**

- **Job context:** Pass `jobId`, `jobTitle`, `company` via query (`/profile/cv-builder?jobId=…`) from job detail **Apply smarter** / matches card; render header per PDF §4.
- **Implement steps:** Experience, Education, Skills, Review — mirror PDF left column; wire to API if endpoints exist, else local draft + export.
- **Cover letter tab or step:** Add step **“Cover letter”** after Review or as sub-tab in Review:
  - Reuse `coverLetter.generate()` from `lib/api.ts`.
  - Show editable textarea + **Copy** / **Download .txt** alongside CV preview.
- **Unified export:** PDF shows one workflow — add **Download PDF** (CV only or CV+letter) using existing print CSS patterns under `app/profile/_tabs/generator/` if present.
- **Deep link:** From `JobDetailBody` “Generate cover letter”, route to builder with letter step pre-selected instead of only opening modal (modal remains for quick action).

### 3. Matches (Priority: P1)

```
apps/frontend/src/app/matches/MatchesPageClient.tsx
apps/frontend/src/components/matches/MatchCard.tsx
apps/frontend/src/components/MatchScore.tsx
apps/frontend/src/components/SkillBadge.tsx
```

**Suggested changes**

- Extract repeated card layout into `MatchCard` if not already — PDF card is consistent: avatar, title stack, pills, score ring right-aligned on desktop / top on mobile.
- Filter chips: map to existing `scoreFilter` state; style as `rounded-full` toggles with green fill when active (PDF **All**, **80%+**, etc.).
- Ensure **View job** uses outline/ghost and **Apply** uses `btn-primary` (PDF).
- Replace any `text-emerald-*` with design tokens per `design_system.md`.

### 4. Home / marketing (Priority: P2)

```
apps/frontend/src/app/HomePageClient.tsx
apps/frontend/src/components/marketing/
├── landing-page.tsx (if used)
├── FourStepsSection.tsx
├── HeroVisualComposition.tsx
├── ScoreMathSection.tsx
└── FinalCtaSection.tsx
```

**Suggested changes**

- Audit hero CTA pair against PDF (primary + outline).
- Pricing cards: ensure Starter `highlight: true` gets copper border/background per PDF.
- FAQ: accordion animation and chevron consistent with profile/settings patterns.

### 5. Profile (Priority: P1)

```
apps/frontend/src/app/profile/ProfilePageClient.tsx
apps/frontend/src/app/profile/_tabs/
├── CvSkillsTab.tsx
├── AnalysisTab.tsx
├── GeneratorTab.tsx
└── PreferencesTab.tsx
```

**Suggested changes**

- Welcome banner: implement gradient `from-green-800 to-green-700` per PDF §14; tier pill on right.
- Tabs: underline active tab in green; avoid duplicate nav with global navbar where possible.
- **CV Generator tab:** Primary CTA should open `TailoredCvBuilder` with clear copy matching PDF §4.

### 6. Auth (Priority: P2)

```
apps/frontend/src/app/auth/AuthPageClient.tsx
apps/frontend/src/components/auth/LoginPage.tsx
apps/frontend/src/components/auth/OtpPage.tsx
apps/frontend/src/app/(auth)/layout.tsx
```

**Suggested changes**

- Match split-panel proportions (40/60) and right-panel bullet list from PDF §15.
- Phone field: national prefix `+260` visible in control (already in schema).
- Consent checkbox styling and legal links placement.

### 7. Dashboard (Priority: P2 — **design decision required**)

```
apps/frontend/src/app/dashboard/page.tsx
apps/frontend/src/components/dashboard/UserDashboard.tsx
```

**Suggested changes**

- **Decision:** PDF 16 is dark analytics; rest of PDFs are light cream. Options:
  - **A)** Keep dark dashboard as “power user” view but align stat colors to brand greens/ambers.
  - **B)** Re-skin dashboard to cream cards like Matches (consistent with §5 “other pages”).
- Document choice in `design_system.md` under “Dashboard variant”.
- Remove raw `bg-zinc-950` in favor of tokens (`--bg`, `--surface-dark-elevated`) if keeping dark.

---

## Proposed new shared components

To avoid duplicating PDF patterns across pages, add under `apps/frontend/src/components/`:

| Component | Purpose | Used by |
|-----------|---------|---------|
| `layout/PageHeader.tsx` | Serif title + subtitle + optional actions | Matches, Profile, Jobs list |
| `jobs/JobMetaPillRow.tsx` | Extract `MetaPill` from `JobDetailBody` | Job detail, match cards |
| `matches/MatchScoreCard.tsx` | Ring + breakdown + skill lists | Job detail panel, hero mock |
| `documents/DocumentPreviewPane.tsx` | Right-hand preview shell (CV or letter) | Tailored CV builder |
| `documents/CoverLetterPanel.tsx` | Generate/edit/copy letter | Builder + modal refactor |

Keep each file **under 300 lines** per project rules.

---

## Content & data requirements (non-UI)

| Requirement | Owner | Notes |
|-------------|-------|-------|
| Full job descriptions in DB | Scraper + admin review | PDF assumes long-form text with section headings. |
| `description_markdown` preferred | Backend normalizer | Feeds `JobDescription` with predictable `h2`/`h3`. |
| Strip scraper attribution | `jobDetailHtml.ts` + ingest | PDF §3.3 — regex list of Zambian boards + generic patterns. |
| Preserve intentional spacing | `plainTextToMarkdown` | Double newlines → paragraph breaks; don’t collapse `\n\n`. |
| Cover letter API | Existing `POST …/generate-cover-letter` | Tier-gated Professional; surface in builder. |
| Tailored CV persistence | TBD | Store drafts per user+job if product requires resume-later. |

---

## Implementation phases

### Phase 1 — Job Details parity (1–2 PRs)

1. Scraper line stripping + heading whitelist expansion.
2. Visual spacing pass on `JobDescription` + `JobDetailBody`.
3. QA with Gastec-style long description (manual test job).
4. Snapshot updates: `apps/frontend/src/app/jobs/[id]/__tests__/`.

### Phase 2 — Tailored CV + Cover Letter (2–3 PRs)

1. Job context query params + header copy.
2. Implement Experience → Review steps (or hide stepper until ready).
3. Integrate cover letter panel; deprecate modal-only flow for signed-in users.
4. Mobile: keep bottom-sheet preview pattern already in `TailoredCvBuilder`.

### Phase 3 — Matches & Profile polish (1–2 PRs)

1. `MatchCard` visual alignment.
2. Profile welcome banner + tabs.

### Phase 4 — Home, Auth, Dashboard (1–2 PRs)

1. Marketing/pricing micro-alignment.
2. Dashboard theme decision + implementation.

### Phase 5 — Design system consolidation (ongoing)

Per `frontend_visual_audit.md`: migrate `.btn` usage to shadcn `Button` with `min-h-11`, single primary green `#0E5C3A`.

---

## Testing & acceptance checklist

- [ ] Job detail: long description renders `JOB PURPOSE`, bullets, and `METHOD OF APPLICATION` with clear spacing.
- [ ] Job detail: no scraper site name, “view original”, or source URL in description body.
- [ ] Job detail: match panel shows score ring + semantic/skills/location + matched/missing lists when signed in.
- [ ] Tailored CV: stepper shows 5 steps; Basics form matches PDF labels.
- [ ] Tailored CV: live preview updates on typing (desktop split / mobile sheet).
- [ ] Cover letter: generatable from builder; Professional tier gate shows upgrade path.
- [ ] Matches: filter chips and sort match PDF; cards readable at 380px width.
- [ ] Profile: welcome banner + four tabs match PDF structure.
- [ ] Auth: split layout; OTP path unchanged functionally.
- [ ] Dashboard: explicit sign-off on dark vs light theme.
- [ ] Dark mode: all touched surfaces readable (`dark:` variants).
- [ ] Responsive snapshots pass: `__tests__/layout.responsive.test.tsx` where applicable.

---

## Risks & open questions

1. **Dashboard dark vs light** — PDF 16 conflicts with PDFs 12–15. Confirm with product owner before re-skinning.
2. **Tailored CV steps without backend** — Placeholder steps may need API work; don’t ship fake “Next” that loses data.
3. **Cover letter in builder vs modal** — Two entry points are fine if they share `CoverLetterPanel`.
4. **Description source of truth** — If ingest sends HTML blobs, frontend-only stripping may be insufficient; prefer backend normalization at job publish time.
5. **Brand name** — PDFs say “ZedApply”; repo folder is `ZedCV`. UI copy should stay consistent with production domain.

---

## Quick reference: PDF → route mapping

| PDF § | Screen | App route | Primary component |
|-------|--------|-----------|-------------------|
| 3 | Job Details | `/jobs/[id]` | `JobDetailBody` |
| 4 | Tailored CV | `/profile/cv-builder` | `TailoredCvBuilder` |
| 5.12 | Home | `/` | `HomePageClient` |
| 5.13 | Matches | `/matches` | `MatchesPageClient` |
| 5.14 | Profile | `/profile` | `ProfilePageClient` |
| 5.15 | Auth | `/auth` | `AuthPageClient` |
| 5.16 | Dashboard | `/dashboard` | `UserDashboard` |

---

## Appendix: assets

Extracted PNGs (2× scale) for design QA:

- `docs/ui-ux-pdf-extract/Styling_UI-UX-06-08_ddd9_p*.png` — Job details before/after
- `docs/ui-ux-pdf-extract/Styling_UI-UX-09-11_268f_p*.png` — Tailored CV
- `docs/ui-ux-pdf-extract/Styling_UI-UX-12-12_6d25_p1.png` — Home
- `docs/ui-ux-pdf-extract/Styling_UI-UX-13-13_5b1a_p1.png` — Matches
- `docs/ui-ux-pdf-extract/Styling_UI-UX-14-14_7f1a_p1.png` — Profile
- `docs/ui-ux-pdf-extract/Styling_UI-UX-15-15_ef55_p1.png` — Auth
- `docs/ui-ux-pdf-extract/Styling_UI-UX-16-16_89dd_p1.png` — Dashboard

Original uploads remain in the Cursor session upload path; extracted copies are committed for team visibility.
