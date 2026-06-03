# Settings audit — `/settings/*`

**Date:** 2026-06-03  
**Scope:** Account, Notifications, Job preferences, Billing, Privacy, Danger zone  
**Method:** Code review, API contract check (`docs/openapi.yaml`, `apps/frontend/src/lib/api.ts`), unit tests for section components, cross-link comparison with `/profile`.

## Summary

| Page | Route | Result | Notes |
|------|-------|--------|-------|
| Account | `/settings/account` | **PASS** | Profile fields + locale prefs persist via `PATCH /profile` and `PATCH /users/me/preferences` |
| Notifications | `/settings/notifications` | **PASS** (fixed) | Alert frequency checkboxes were conflicting; fixed in this PR |
| Job preferences | `/settings/job-preferences` | **PASS** | Reuses `PreferencesTab` with debounced auto-save to `PATCH /preferences` |
| Billing | `/settings/billing` | **PASS** | Read-only plan display; cancel uses `POST /subscription/cancel`; invoices wired |
| Privacy | `/settings/privacy` | **PASS** | Consent, visibility, export persist; delete delegated to Danger zone |
| Danger zone | `/settings/danger` | **PASS** (fixed) | Delete now uses `DELETE /me` with phone confirmation (was wrong endpoint/UX) |

---

## Per-page detail

### Account — PASS

**Forms / persistence**

| Control | API | Persists |
|---------|-----|----------|
| Full name, email, location | `PATCH /profile` | Yes — inline edit + Save |
| Currency | `PATCH /users/me/preferences` | Yes — on change |
| Time zone | `PATCH /users/me/preferences` | Yes — on change |
| WhatsApp number | — | Read-only (verified at sign-in) |
| Display language | — | Static "English" (no backend field) |

**Profile cross-links**

- Header links to `/settings/privacy` and `/profile` (CV & skills tools).
- Matches Profile sidebar: Account settings → `/settings/account`, Privacy → `/settings/privacy`.

**Tests:** `AccountSection.test.tsx` (4 cases).

---

### Notifications — PASS (fixed)

**Forms / persistence**

| Control | API | Persists |
|---------|-----|----------|
| Digest channel (email / WhatsApp / both) | `PATCH /users/me/preferences` (`preferred_notification_channel`) | Yes |
| New match notifications | same (`alert_frequency`: daily \| muted) | Yes — **fixed** |
| Weekly job alerts | same (`alert_frequency`: weekly \| daily) | Yes — **fixed**; disabled when muted |
| Product updates | same (`notify_product_updates`) | Yes |
| Quiet hours start/end | same (`quiet_hours_start`, `quiet_hours_end`) | Yes — errors now surfaced |
| Auto-match toggle | `PATCH /users/me/auto-match-preferences` | Yes |

**Bug fixed (this PR):** `alert_frequency` is a single enum (`daily` \| `weekly` \| `muted`), but two independent checkboxes both wrote to it. Unchecking "New match notifications" while weekly was on could leave contradictory UI; weekly stayed visually "on" because `weekly !== muted`. Logic now:

- Mute → `muted`; weekly checkbox disabled.
- Unmute → restores `daily` (or keeps `weekly` if re-enabling from a weekly state).
- Weekly toggle only applies when not muted.

**Profile cross-links**

- Profile Quick links → `/settings/notifications`.
- User menu → Notifications.
- No back-link on Notifications page (acceptable; nav + Profile cover entry points).

**Tests:** `NotificationsSection.test.tsx` (8 cases, including alert-frequency regression).

---

### Job preferences — PASS

**Forms / persistence**

- Embeds `PreferencesTab` from Profile — same auto-save hook (`usePreferencesAutoSave` → `PATCH /preferences`).
- Years of experience saves on blur via `PATCH /profile`.
- Local validation blocks save when `salary_min > salary_max`.

**Profile cross-links**

- **Added in this PR:** header link to `/profile` for CV & skills tools.
- Profile sidebar "Job preferences" opens in-tab; Settings route is the dedicated full-width view of the same form.

**Tests:** Covered indirectly by `PreferencesTab` / preferences API tests elsewhere; no dedicated settings wrapper test (low risk — thin wrapper).

---

### Billing — PASS

**Forms / persistence**

| Control | API | Persists |
|---------|-----|----------|
| Current plan / usage | `GET /profile`, `GET /subscription` | Read-only display |
| Upgrade | Link → `/pricing` | Checkout flow |
| Cancel at period end | `POST /subscription/cancel` | Yes — confirm dialog + reload |
| Invoice view / download / email | `GET /subscription/payments/{id}/invoice*` | Yes |

**Profile cross-links**

- Profile → `/settings/billing` ("Billing & plan").
- Dashboard `PlanUsageCard` → `/settings/billing`.

**Tests:** `BillingSection.test.tsx` (4 cases).

---

### Privacy — PASS

**Forms / persistence**

| Control | API | Persists |
|---------|-----|----------|
| Consent toggles (6 types) | `POST /data-rights/consent` | Yes — audit log on server |
| Show profile to employers | `PATCH /users/me/preferences` | Yes |
| Hide from current employer | same (`hidden_employer_name`) | Yes — on blur |
| Export my data | `GET /me/export` | Yes — browser download (1/hour rate limit) |

**Profile cross-links**

- Profile Quick links → `/settings/privacy` ("Privacy & data export").
- Account → `/settings/privacy`.
- `DataPrivacyCard` used with `exportOnly` — delete intentionally on Danger zone only.

**Tests:** No dedicated Privacy section test; `DataPrivacyCard` and consent API covered elsewhere.

---

### Danger zone — PASS (fixed)

**Forms / persistence**

| Control | API | Persists |
|---------|-----|----------|
| Pause matching | `PATCH /users/me/auto-match-preferences` | Yes |
| Delete account | `DELETE /me` + `{ confirm_phone }` | Yes — **fixed** |

**Bug fixed (this PR):** Delete dialog required typing `DELETE` and called `DELETE /profile` (`profile.remove`), which:

- Skipped phone confirmation required by the data-rights endpoint.
- Did not purge CV storage or OTP rows (`/me` handler does both).

Now aligned with `DataPrivacyCard` / OpenAPI: user types WhatsApp number exactly (`+260…`).

**Profile cross-links**

- No direct Profile link (destructive area); Profile export/delete copy points users to Settings.

**Tests:** `DangerSection.test.tsx` (3 cases) — **added in this PR**.

---

## Profile tools link matrix

| Profile entry | Target | Settings reciprocal |
|---------------|--------|---------------------|
| Billing & plan | `/settings/billing` | — (billing links to `/pricing`) |
| Job preferences (tab) | `/profile?tab=preferences` | `/settings/job-preferences` → `/profile` ✓ |
| Account settings | `/settings/account` | Account → `/profile` ✓ |
| Notification preferences | `/settings/notifications` | — |
| Privacy & data export | `/settings/privacy` | Account → privacy ✓ |
| CV Generator (menu) | `/profile?tab=cv-generator` | Job prefs / Account → Profile ✓ |

Nav (`UserMenuDropdown`): Settings → `/settings/account`; Notifications → `/settings/notifications`; Profile → `/profile`.

---

## Missing / not implemented features

These are **not bugs** in current code — documented gaps vs. common SaaS settings expectations:

| Feature | Status | Notes |
|---------|--------|-------|
| **Two-factor authentication (2FA)** | Not implemented | Auth is WhatsApp OTP only at sign-in; no TOTP/WebAuthn or step-up 2FA for sensitive actions |
| **Export data** | Implemented | `/settings/privacy` → Export my data (`GET /me/export`); 1 export/hour |
| **Delete account flow** | Implemented (fixed) | `/settings/danger` — phone confirmation + `DELETE /me`; OTP step-up listed in backend economics (`delete_account` action) but **not wired in UI** |
| **Change phone number** | Not implemented | Phone is identity key; would need re-verification flow |
| **Display language i18n** | UI placeholder only | Account shows "English"; no locale switcher |
| **Email change verification** | Partial | Email saves via `PATCH /profile`; no separate verify-email flow in settings |
| **Payment method on file** | Read-only history | Last payment shown; new method chosen at `/pricing` checkout |
| **Session / device management** | Not implemented | No "log out other devices" |

### Recommended follow-ups (priority)

1. **OTP step-up before delete** — backend already defines `delete_account` as OTP-gated; wire Danger zone to request OTP before `DELETE /me`.
2. **2FA** — out of scope for $30/mo stack unless product requires it; document as WhatsApp OTP = primary factor.
3. **Phone change** — requires new migration + WAHA re-bind; high effort.

---

## Files changed in this audit

| File | Change |
|------|--------|
| `apps/frontend/src/app/settings/_sections/NotificationsSection.tsx` | Fix `alert_frequency` mutual exclusion; shared error handling for quiet hours |
| `apps/frontend/src/app/settings/_sections/DangerSection.tsx` | Phone-confirmed `DELETE /me` |
| `apps/frontend/src/app/settings/_sections/JobPreferencesSection.tsx` | Profile cross-link |
| `apps/frontend/src/app/settings/_sections/__tests__/NotificationsSection.test.tsx` | Regression tests |
| `apps/frontend/src/app/settings/_sections/__tests__/DangerSection.test.tsx` | New tests |
| `docs/settings-audit.md` | This document |

---

## Verification commands

```bash
cd apps/frontend && npm test -- src/app/settings/_sections/__tests__/
```

19 tests passing as of 2026-06-03.
