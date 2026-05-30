import Script from "next/script";

const PLAUSIBLE_INIT =
  "window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};plausible.init()";

/**
 * Privacy-preserving analytics via Plausible (https://plausible.io).
 *
 * Preferred (Plausible dashboard “Script” install): set
 * NEXT_PUBLIC_PLAUSIBLE_SCRIPT_URL to the site-specific loader, e.g.
 * https://plausible.io/js/pa-….js
 *
 * Legacy fallback: NEXT_PUBLIC_PLAUSIBLE_DOMAIN + /js/script.js
 */
export function PlausibleAnalytics() {
  const scriptUrl = process.env.NEXT_PUBLIC_PLAUSIBLE_SCRIPT_URL?.trim();
  const domain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN?.trim();

  if (scriptUrl) {
    return (
      <>
        <Script src={scriptUrl} strategy="lazyOnload" />
        <Script id="plausible-init" strategy="lazyOnload">
          {PLAUSIBLE_INIT}
        </Script>
      </>
    );
  }

  if (!domain) return null;

  return (
    <Script
      defer
      data-domain={domain}
      src="https://plausible.io/js/script.js"
      strategy="lazyOnload"
    />
  );
}
