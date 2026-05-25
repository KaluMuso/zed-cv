# PWA Audit — ZedApply (Track 5)

**Site:** https://www.zedapply.com  
**Date:** 2026-05-21  
**Scope:** Installability, manifest, service worker, offline UX

---

## Pre-fix findings

| Check | Status | Notes |
|-------|--------|-------|
| `manifest.json` linked | Pass | Via Next.js `metadata.manifest` in root layout |
| `display: standalone` | Pass | Present |
| `start_url` | Warn | Was `/` — install funnel targets `/matches` after sign-in |
| Theme / background colors | Warn | Did not match brand primary `#0E5C3A` |
| Icons 192 + 512 PNG | Pass | Files exist at `public/icons/icon-192.png`, `icon-512.png` |
| Maskable icon | Pass | SVG maskable + PNG 512 with `purpose: maskable` |
| Service worker registered | Pass | `PWAProvider` registers `/sw.js` (skipped on localhost) |
| Duplicate SW registration | Warn | Unused `RegisterServiceWorker` in dead `AppProviders` tree |
| `beforeinstallprompt` UI | **Fail** | No in-app install banner |
| Offline messaging | **Fail** | `OfflineBanner` component existed but was not mounted |
| SW HTML strategy | Warn | Cache-first navigations could serve stale RSC payloads |
| HTTPS | Pass | Production on `zedapply.com` |

### Likely Android install blockers

1. No engaged install prompt (`beforeinstallprompt` handler + user gesture path).
2. `start_url` not aligned with primary authenticated surface (`/matches`).
3. Stale shell / RSC caching confusing Lighthouse “installable” checks after deploys.

---

## Fixes applied (Track 5 PR)

### Manifest (`public/manifest.json`)

- `id: "/"`
- `start_url: "/matches"`
- `theme_color` / `background_color`: `#0E5C3A`
- PNG + maskable entries; removed broken references to missing assets
- `display_override`, `lang: en-ZM`

### Service worker (`@ducanh2912/next-pwa`)

- Generated at build into `public/sw.js` (gitignored; do not hand-edit)
- **Static assets:** cache-first (`/_next/static/`, icons)
- **API:** network-first (`api.zedcv.com/api/v1`, local backend)
- **Lenco payments:** network-only (no cached checkout scripts)
- **Offline fallback:** `app/~offline/page.tsx`
- Default next-pwa rules retain network-first for RSC / page navigations

### App integration

- `OfflineBanner` mounted in root layout (sticky offline copy per spec)
- `PWAInstallPrompt` on `/matches` — listens for `beforeinstallprompt`, dismissible, localStorage gate
- Viewport `themeColor` updated to `#0E5C3A`

---

## Verification steps (post-deploy)

Run on production (requires network):

```bash
npx lighthouse https://www.zedapply.com/matches --only-categories=pwa --chrome-flags="--headless" --output=json
```

**Acceptance targets:**

| Metric | Target |
|--------|--------|
| PWA installable | Score ≥ 90 |
| Manifest valid | No errors |
| SW registered | Yes |
| Icons | 192 + 512 + maskable |

### Manual Android smoke test

1. Open Chrome → https://www.zedapply.com/matches (signed in).
2. Confirm non-intrusive “Install ZedApply” banner (first visit).
3. Install → standalone mode, green theme splash.
4. Toggle airplane mode → offline banner; cached shell loads; network pages show offline message.

---

## Lighthouse note (Cloud Agent)

Automated Lighthouse against production was not executed in the cloud VM (no guaranteed Chrome + outbound crawl to prod in CI). Re-run the command above after merge on staging/production and attach JSON to the PR if scores are required for merge gate.

**Expected post-fix:** installability criteria pass when manifest + SW + HTTPS + icons are valid; engagement heuristics may still require a second visit and user interaction on `/matches`.
