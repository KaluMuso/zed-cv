# Lenco checkout — Android manual test plan

**Scope:** Inline Lenco widget on `/pricing` (paid tier upgrade).  
**When:** After PWA/service-worker changes; run on a **low-end Android** device or emulator (API 28+, Chrome).

No physical device was available in the Cloud Agent VM; use this checklist on staging/production.

---

## Setup

1. Install Chrome on the test device (or Android Emulator with Google Play).
2. Open `https://www.zedapply.com/pricing` (or staging URL).
3. Sign in with a test account that is **not** already on the target paid tier.
4. Set `NEXT_PUBLIC_LENCO_PUBLIC_KEY` and sandbox widget URL in the environment (see `apps/frontend/.env.example`).

---

## Test cases

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 1 | Wait for pricing cards to load | Paid tiers show **Upgrade** (not stuck on “Loading checkout…”) | |
| 2 | Tap **Starter** (or any paid tier) | Lenco modal/overlay opens within ~3s | |
| 3 | Modal layout | Modal is fully visible; no content clipped under mobile tab bar or notch | |
| 4 | Scroll inside modal | Payment fields scroll; background page does not scroll behind modal | |
| 5 | Close modal (X or back) | Toast “Payment cancelled”; no stuck loading state on the card button | |
| 6 | Re-open checkout | Second open works without refresh | |
| 7 | Airplane mode **before** opening checkout | Tap upgrade → clear error (“widget failed” / network), no blank white overlay | |
| 8 | Airplane mode **after** modal open | Graceful error or spinner timeout; app remains usable after dismiss | |
| 9 | PWA installed (standalone) | Same as steps 2–6 from home-screen icon | |
| 10 | Small viewport (360×640) | CTA buttons on pricing page remain tappable; modal not wider than screen | |

---

## Known risks (service worker)

- Lenco script and API calls use **NetworkOnly** / **NetworkFirst** in `next-pwa.config.js` so the SW must not serve stale payment scripts or API responses.
- If checkout fails only when installed as PWA, clear site data: Chrome → Site settings → Clear & reset → unregister service worker, then retest.

---

## Report template

```
Device: (e.g. Samsung A12 / Emulator Pixel 4 API 30)
Chrome version:
Build URL:
Results: TC1–TC10 pass/fail
Issues: (screenshots + steps)
```
