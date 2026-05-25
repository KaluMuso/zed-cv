// @ts-check
const withPWA = require("@ducanh2912/next-pwa").default;
const { pwaOptions } = require("./next-pwa.config.js");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
};

const configWithPwa = withPWA(pwaOptions)(nextConfig);

if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
  const { withSentryConfig } = require("@sentry/nextjs");
  module.exports = withSentryConfig(configWithPwa, {
    silent: true,
    disableLogger: true,
    widenClientFileUpload: false,
    hideSourceMaps: true,
  });
} else {
  module.exports = configWithPwa;
}
