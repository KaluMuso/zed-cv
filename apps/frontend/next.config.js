// @ts-check
const withPWA = require("@ducanh2912/next-pwa").default;
const { pwaOptions } = require("./next-pwa.config.js");

const SECURITY_HEADERS = [
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://plausible.io https://pay.lenco.co https://pay.sandbox.lenco.co https://sandbox.lenco.co https://browser.sentry-cdn.com",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https: blob:",
      "font-src 'self' data:",
      "connect-src 'self' https://api.zedapply.com https://*.supabase.co https://*.ingest.sentry.io https://*.ingest.de.sentry.io https://plausible.io https://pay.lenco.co https://pay.sandbox.lenco.co https://sandbox.lenco.co",
      "frame-src 'self' https://pay.lenco.co https://pay.sandbox.lenco.co https://sandbox.lenco.co",
      "object-src 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  compiler: {
    removeConsole:
      process.env.NODE_ENV === "production"
        ? { exclude: ["error", "warn"] }
        : false,
  },
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: SECURITY_HEADERS,
      },
    ];
  },
};

const configWithPwa = withPWA(pwaOptions)(nextConfig);

if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
  const { withSentryConfig } = require("@sentry/nextjs");
  module.exports = withSentryConfig(configWithPwa, {
    silent: true,
    disableLogger: true,
    widenClientFileUpload: false,
    hideSourceMaps: true,
    // Sentry API 500s during `releases new` must not fail Vercel builds.
    release: {
      create: false,
      finalize: false,
    },
    sourcemaps: {
      deleteSourcemapsAfterUpload: true,
    },
    errorHandler: (err) => {
      console.warn(
        "[sentry] source map upload failed (non-fatal):",
        err?.message || err
      );
    },
  });
} else {
  module.exports = configWithPwa;
}
