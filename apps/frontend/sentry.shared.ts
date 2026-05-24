import { sentryBeforeSend } from "./src/lib/sentry_scrub";

export { sentryBeforeSend } from "./src/lib/sentry_scrub";

export function getSentryInitOptions() {
  return {
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    environment:
      process.env.SENTRY_ENVIRONMENT ||
      process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ||
      "production",
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
    beforeSend: sentryBeforeSend,
  } as const;
}
