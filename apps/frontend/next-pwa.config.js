/** @type {import("@ducanh2912/next-pwa").PluginOptions} */
const pwaOptions = {
  dest: "public",
  sw: "sw.js",
  customWorkerSrc: "worker",
  disable: process.env.NODE_ENV === "development",
  register: true,
  skipWaiting: true,
  reloadOnOnline: true,
  cacheOnFrontEndNav: true,
  extendDefaultRuntimeCaching: true,
  fallbacks: {
    document: "/~offline",
  },
  workboxOptions: {
    disableDevLogs: true,
    // RSC / Next flight must not be cached as static HTML (see docs/pwa_audit.md).
    navigateFallbackDenylist: [/^\/api\//, /^\/_next\/data\//],
    runtimeCaching: [
      {
        urlPattern:
          /^https:\/\/www\.zedapply\.com\/(jobs|matches|auth|profile|dashboard|settings|applications)/i,
        handler: "NetworkFirst",
        options: {
          cacheName: "zedapply-page-cache",
          networkTimeoutSeconds: 5,
          expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 },
          cacheableResponse: { statuses: [0, 200, 302] },
        },
      },
      {
        urlPattern: /^https:\/\/api\.zedapply\.com\/api\/v1\/.*/i,
        handler: "NetworkOnly",
        options: {
          plugins: [
            {
              fetchDidFail: async () => {
                /* Swallow — ApiFetch + Sentry capture real API failures in-app. */
              },
            },
          ],
        },
      },
      {
        urlPattern: /^http:\/\/localhost:8000\/api\/v1\/.*/i,
        handler: "NetworkOnly",
        options: {
          plugins: [
            {
              fetchDidFail: async () => {
                /* Local dev: no SW console noise on offline API probes. */
              },
            },
          ],
        },
      },
      {
        urlPattern: /^https:\/\/pay(\.sandbox)?\.lenco\.co\/.*/i,
        handler: "NetworkOnly",
        method: "GET",
      },
      {
        urlPattern: /\/_next\/static\/.*/i,
        handler: "CacheFirst",
        options: {
          cacheName: "zedapply-next-static",
          expiration: {
            maxEntries: 256,
            maxAgeSeconds: 60 * 60 * 24 * 365,
          },
        },
      },
      {
        urlPattern: /\/icons\/.*\.(?:png|svg|webp)$/i,
        handler: "CacheFirst",
        options: {
          cacheName: "zedapply-icons",
          expiration: { maxEntries: 32, maxAgeSeconds: 60 * 60 * 24 * 365 },
        },
      },
    ],
  },
};

module.exports = { pwaOptions };
