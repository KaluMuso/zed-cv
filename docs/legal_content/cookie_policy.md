# Cookie Policy

**Last updated:** 2026-05-24 · **Version:** 1.0.0

This Cookie Policy explains how **Zed Apply** (ZedApply), a subsidiary of **Vergeo Group**, uses cookies and similar browser technologies on our website. Read it together with our [Privacy Policy](/legal/privacy).

We audited the frontend codebase on **2026-05-24**. Zed Apply does **not** set classic HTTP cookies via `document.cookie` or Next.js `cookies()` for authentication today. Instead, we use **browser local storage** and **session storage** for the items below. Under this policy, "cookies" includes those technologies unless we say otherwise.

## 1. What are cookies and similar technologies?

A **cookie** is a small file stored by your browser. **Local storage** and **session storage** hold data in your browser without automatically sending it on every request — but they serve a similar purpose (remembering sign-in, preferences, and UI state).

## 2. Cookies and storage we set

### Strictly necessary (no consent required)

These are required for core functionality. Blocking them will break sign-in or core pages.

| Name | Type | Purpose | Duration |
| --- | --- | --- | --- |
| `zed_cv_token` | localStorage | JWT access token after WhatsApp OTP sign-in | Until sign-out or you clear site data |
| `zed_cv_user_id` | localStorage | Your user ID paired with the token | Until sign-out or you clear site data |
| `zedapply_matches_cache_v1` | sessionStorage | Short-lived cache of match list to improve page load | Until browser tab/session ends |

**Note:** Authentication uses **localStorage**, not an HttpOnly cookie. This means any script running on our origin could theoretically read the token — we mitigate this with strict content security, no third-party ad scripts, and sanitised legal/admin content. Sign out clears `zed_cv_token` and `zed_cv_user_id`.

### Preferences (no separate banner today)

| Name | Type | Purpose | Duration |
| --- | --- | --- | --- |
| `zed_cv_theme` | localStorage | Light/dark theme choice | Until you change theme or clear site data |
| `zedcv:preferences:expanded` | localStorage | Which sections are expanded on the profile preferences tab | Until cleared |
| `zedapply_pwa_install_dismissed` | localStorage | Remembers if you dismissed the "install app" prompt | Until cleared |

### Functional (logged-in features)

| Name | Type | Purpose | Duration |
| --- | --- | --- | --- |
| `zedapply_bwana_session_id` | localStorage | Anonymous session ID for Bwana support chat | Until cleared or you start a new chat session |
| `zedcv_aptitude_session` | localStorage | In-progress aptitude test state (Interview Prep) | Until test completes or you clear site data |

### Admin-only (superadmin job wizard)

| Name | Type | Purpose | Duration |
| --- | --- | --- | --- |
| `zedcv:admin:job-draft:v1` | localStorage | Draft job form for admins | Up to **7 days**, then auto-discarded |

Regular job seekers will not see admin drafts.

### Analytics and marketing

We **do not** currently load Google Analytics, Meta Pixel, or other third-party analytics/marketing scripts. We **do not** set advertising cookies.

When we add product analytics, we will:

- ask for **opt-in consent** via a banner before loading scripts;
- update this policy; and
- list each new cookie by name.

## 3. Third-party cookies

We do **not** currently allow third parties to set cookies on zedapply.com when you browse our pages.

Payment (**Lenco**, **DPO Pay**) and WhatsApp (**WAHA**) run as **back-end processors** — they do not set cookies on your device when you simply view Zed Apply. When you complete checkout, you may interact with a processor-hosted page that sets its own cookies under **their** policies.

## 4. How to control cookies and storage

- **Browser settings:** View and delete cookies and site data (often under Privacy → Cookies / Site data). Deleting data for our site signs you out and clears preferences.
- **Sign out:** Removes `zed_cv_token` and `zed_cv_user_id`.
- **Private / incognito mode:** Usually clears session storage when you close the window; localStorage may still persist until the private session ends (browser-dependent).
- **Theme toggle:** Updates `zed_cv_theme` immediately.

When we launch an analytics consent banner, you will be able to change analytics choices in-app.

## 5. Relationship to the ZDPA

Where storage identifies you (e.g. auth token), it processes personal data under our [Privacy Policy](/legal/privacy) and the **Zambia Data Protection Act, 2021**. Strictly necessary storage is based on **contract** and **legitimate interests**; optional analytics will rely on **consent**.

## 6. Changes

We may update this policy when we add cookies or change storage keys. The "Last updated" date shows the revision date.

## 7. Contact

[convergeozambia@gmail.com](mailto:convergeozambia@gmail.com)
