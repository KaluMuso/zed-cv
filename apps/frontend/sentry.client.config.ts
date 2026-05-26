import * as Sentry from "@sentry/nextjs";
import { getSentryInitOptions } from "./sentry.shared";

function initSentryClient() {
  const { dsn, ...options } = getSentryInitOptions();
  if (!dsn || typeof window === "undefined") return;

  Sentry.init({
    dsn,
    ...options,
    enabled: true,
    ignoreErrors: [
      "ResizeObserver loop limit exceeded",
      "Hydration failed because the initial UI does not match",
      "Text content does not match server-rendered HTML",
      "Network Error",
    ],
    replaysSessionSampleRate: 0.0,
    replaysOnErrorSampleRate: 0.1,
  });
}

if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_SENTRY_DSN) {
  const schedule =
    typeof requestIdleCallback === "function"
      ? requestIdleCallback
      : (cb: () => void) => window.setTimeout(cb, 1);

  schedule(() => initSentryClient());
}
