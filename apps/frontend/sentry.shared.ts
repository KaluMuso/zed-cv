import type { ErrorEvent, EventHint } from "@sentry/nextjs";

// Mirror apps/backend/app/core/sentry_redaction.py — JWT first, then email, then phone.
const JWT_RE =
  /eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{4,}/g;
const EMAIL_RE =
  /[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/g;
const PHONE_RE = /\+260\d{9}/g;

function redactString(s: string): string {
  return s
    .replace(JWT_RE, "[jwt-redacted]")
    .replace(EMAIL_RE, "[email-redacted]")
    .replace(PHONE_RE, "[phone-redacted]");
}

function walk(obj: unknown): void {
  if (obj === null || obj === undefined) return;
  if (typeof obj === "string") return;
  if (Array.isArray(obj)) {
    for (let i = 0; i < obj.length; i++) {
      if (typeof obj[i] === "string") obj[i] = redactString(obj[i] as string);
      else walk(obj[i]);
    }
    return;
  }
  if (typeof obj === "object") {
    const record = obj as Record<string, unknown>;
    for (const key of Object.keys(record)) {
      const val = record[key];
      if (typeof val === "string") record[key] = redactString(val);
      else walk(val);
    }
  }
}

export function sentryBeforeSend(
  event: ErrorEvent,
  _hint?: EventHint
): ErrorEvent {
  walk(event);
  return event;
}

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
