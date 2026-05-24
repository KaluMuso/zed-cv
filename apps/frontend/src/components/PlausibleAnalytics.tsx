import Script from "next/script";

/**
 * Privacy-preserving analytics via Plausible (https://plausible.io).
 * Loaded only when NEXT_PUBLIC_PLAUSIBLE_DOMAIN is set (e.g. zedapply.com).
 */
export function PlausibleAnalytics() {
  const domain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN?.trim();
  if (!domain) return null;

  return (
    <Script
      defer
      data-domain={domain}
      src="https://plausible.io/js/script.js"
      strategy="afterInteractive"
    />
  );
}
