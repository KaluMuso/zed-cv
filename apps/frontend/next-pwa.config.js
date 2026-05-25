/** @type {import("@ducanh2912/next-pwa").PluginOptions} */
const pwaOptions = {
  dest: "public",
  sw: "sw.js",
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
        urlPattern: /^https:\/\/api\.zedcv\.com\/api\/v1\/.*/i,
        handler: "NetworkFirst",
        options: {
          cacheName: "zedapply-api",
          networkTimeoutSeconds: 10,
          expiration: { maxEntries: 64, maxAgeSeconds: 60 * 60 * 24 },
          cacheableResponse: { statuses: [0, 200] },
        },
      },
      {
        urlPattern: /^http:\/\/localhost:8000\/api\/v1\/.*/i,
        handler: "NetworkFirst",
        options: {
          cacheName: "zedapply-api-local",
          networkTimeoutSeconds: 10,
          expiration: { maxEntries: 32, maxAgeSeconds: 60 * 60 },
          cacheableResponse: { statuses: [0, 200] },
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
