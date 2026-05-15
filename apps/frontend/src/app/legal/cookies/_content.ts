// Static markdown source for the Cookie Policy. See _content.ts in
// /legal/privacy for the rationale behind this file layout.
export const VERSION = "1.0";
export const LAST_UPDATED = "2026-05-14";

export const COOKIES_MARKDOWN = `# Cookie Policy

**Last updated:** ${LAST_UPDATED} &middot; **Version:** ${VERSION}

This Cookie Policy explains how ZedApply uses cookies and similar
technologies on our website. It should be read together with our
[Privacy Policy](/legal/privacy), which explains how we handle
personal data more generally.

## 1. What are cookies?

A "cookie" is a small text file that a website stores on your device
when you visit. Cookies allow the website to remember information
about your visit &mdash; such as the fact that you are signed in or
which theme you prefer &mdash; so that the experience works smoothly
on subsequent pages and visits.

We also use related technologies such as **local storage** and
**session storage**, which work similarly to cookies but store data
directly in your browser rather than sending it back to our servers.
References to "cookies" in this policy include these related
technologies.

## 2. Categories of cookies we use

We group cookies into categories based on what they do. Each cookie we
set falls into one of the following categories.

### Strictly necessary

These cookies are essential for the Service to function. Without
them, you cannot sign in or use core features. We do **not** ask for
your consent for strictly necessary cookies because the Service
cannot operate without them, but you can still block them in your
browser settings (the Service will not work properly if you do).

Examples:

- **Authentication token (JWT).** Set when you sign in successfully
  via WhatsApp OTP, so we know it is you on subsequent requests.
- **Session state.** A small marker so we can recover gracefully if
  the page reloads mid-flow (for example, during the OTP step).
- **Security tokens** (e.g. CSRF protection) used to protect form
  submissions against cross-site request forgery.

### Preferences

These cookies remember choices you make so the Service feels
consistent across visits. They do not identify you to third parties.

Examples:

- **Theme preference** (light or dark mode).
- **Dismissed banners and tips** &mdash; so we do not show you the
  same prompt repeatedly.

### Analytics &mdash; *opt-in only*

We do not currently load any analytics or measurement scripts. When
we add product analytics in a future release, we will ask for your
**explicit, opt-in consent via a cookie banner** before loading any
analytics cookies, and you will be able to change your choice at any
time. If you decline, no analytics cookies will be set.

### Marketing or advertising

We do **not** use marketing or advertising cookies. We do not run
remarketing, retargeting or behavioural advertising.

## 3. Third-party cookies

We do not currently load third-party cookies onto your device.

The Service uses third-party processors (described in the
[Privacy Policy](/legal/privacy)), but they operate as **back-end
processors** &mdash; they receive data from our servers when you take
an action (for example, paying for a subscription), not by setting
cookies on your browser when you visit ZedApply.

We reserve the right to introduce third-party cookies in future
(for example, opt-in product analytics). We will update this Cookie
Policy and ask for your consent before doing so.

## 4. How to control cookies

You have several ways to control cookies:

- **Browser settings.** Most browsers let you view, manage and delete
  cookies, and block cookies from specific sites. Look for "Privacy"
  or "Cookies" in your browser settings. Note that blocking strictly
  necessary cookies will prevent you from signing in to ZedApply.
- **Sign out.** Signing out of ZedApply clears your authentication
  cookie immediately.
- **Private / incognito browsing.** Most browsers offer a private
  mode that does not retain cookies after you close the window.

When we introduce opt-in analytics, you will also be able to manage
that choice from within the Service itself.

## 5. Changes to this Cookie Policy

We may update this Cookie Policy from time to time, for example when
we add new categories of cookies or change processors. The "Last
updated" date at the top of this page shows when the policy was last
revised.

## 6. Contact

For any questions about this Cookie Policy, please contact us at
[convergeozambia@gmail.com](mailto:convergeozambia@gmail.com).
`;
