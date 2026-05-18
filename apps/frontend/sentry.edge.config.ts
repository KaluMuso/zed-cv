import * as Sentry from "@sentry/nextjs";
import { getSentryInitOptions } from "./sentry.shared";

const { dsn, ...options } = getSentryInitOptions();

if (dsn) {
  Sentry.init({ dsn, ...options });
}
