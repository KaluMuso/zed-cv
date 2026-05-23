import * as Sentry from "@sentry/nextjs";
import { getSentryInitOptions } from "./sentry.shared";

const { dsn, ...options } = getSentryInitOptions();
const enabled =
  Boolean(process.env.NEXT_PUBLIC_SENTRY_DSN) && typeof window !== "undefined";

if (dsn && enabled) {
  Sentry.init({
    dsn,
    ...options,
    enabled,
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
