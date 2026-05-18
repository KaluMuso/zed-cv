/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
};

// Sentry wraps the config only when a DSN is set so local dev stays
// unchanged. Source maps are generated and uploaded (so Sentry can
// symbolicate production stack traces) but hidden from the public
// bundle. withSentryConfig silently skips the upload at build time
// if SENTRY_AUTH_TOKEN/ORG/PROJECT aren't all set, so a local
// `next build` with only the DSN still works.
if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
  const { withSentryConfig } = require("@sentry/nextjs");
  module.exports = withSentryConfig(nextConfig, {
    silent: true,
    disableLogger: true,
    widenClientFileUpload: false,
    hideSourceMaps: true,
  });
} else {
  module.exports = nextConfig;
}
