import type { ErrorEvent, EventHint } from "@sentry/nextjs";

/** Bump when regex set or drop rules change — visible in Sentry tags. */
export const SENTRY_REDACTION_VERSION = "1.0";

// Order: JWT → NRC → email → phone (most specific first).
const JWT_RE =
  /eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/g;
const NRC_RE = /\d{6}\/\d{2}\/\d/g;
const EMAIL_RE = /[\w.+-]+@[\w.-]+\.\w+/g;
/** Zambian mobile: +260/260/0 + 9[567] + 7 digits. */
const PHONE_RE = /(?:\+?260|0)9[567]\d{7}/g;
/** WAHA / WhatsApp JID suffix. */
const WHATSAPP_CUS_RE = /\d{9,15}@c\.us/g;

const HIGH_RISK_OTP_PATHS = ["/auth/verify-otp", "/auth/otp/verify"] as const;
const LENCO_WEBHOOK_PATH = "/webhooks/lenco";

export function redactString(value: string): string {
  return value
    .replace(JWT_RE, "[REDACTED_JWT]")
    .replace(NRC_RE, "[REDACTED_NRC]")
    .replace(WHATSAPP_CUS_RE, "[REDACTED_PHONE]")
    .replace(EMAIL_RE, "[REDACTED_EMAIL]")
    .replace(PHONE_RE, "[REDACTED_PHONE]");
}

function scrubStringLeaves(value: unknown): void {
  if (value === null || value === undefined) return;
  if (typeof value === "string") return;
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i++) {
      const item = value[i];
      if (typeof item === "string") {
        value[i] = redactString(item);
      } else {
        scrubStringLeaves(item);
      }
    }
    return;
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    for (const key of Object.keys(record)) {
      const item = record[key];
      if (typeof item === "string") {
        record[key] = redactString(item);
      } else {
        scrubStringLeaves(item);
      }
    }
  }
}

function eventMentionsPath(event: ErrorEvent, fragment: string): boolean {
  const request = event.request;
  const url = request?.url ?? "";
  if (typeof url === "string" && url.includes(fragment)) {
    return true;
  }
  const serialized = JSON.stringify(event);
  return serialized.includes(fragment);
}

function hasLencoWebhookPayloadBody(event: ErrorEvent): boolean {
  if (!eventMentionsPath(event, LENCO_WEBHOOK_PATH)) {
    return false;
  }
  const data = event.request?.data;
  if (data === null || data === undefined) {
    return false;
  }
  if (typeof data === "string") {
    return data.trim().length > 0;
  }
  if (typeof data === "object") {
    return Object.keys(data as Record<string, unknown>).length > 0;
  }
  return true;
}

function mentionsOtpVerifyPath(event: ErrorEvent): boolean {
  return HIGH_RISK_OTP_PATHS.some((path) => eventMentionsPath(event, path));
}

export function shouldDropSentryEvent(event: ErrorEvent): boolean {
  if (mentionsOtpVerifyPath(event)) {
    return true;
  }
  if (hasLencoWebhookPayloadBody(event)) {
    return true;
  }
  return false;
}

function stripUserIp(event: ErrorEvent): void {
  if (event.user && typeof event.user === "object") {
    const user = event.user as Record<string, unknown>;
    delete user.ip_address;
    delete user.ipAddress;
  }
  const headers = event.request?.headers;
  if (headers && typeof headers === "object") {
    const h = headers as Record<string, unknown>;
    delete h["X-Forwarded-For"];
    delete h["x-forwarded-for"];
    delete h["X-Real-IP"];
    delete h["x-real-ip"];
  }
}

function applyRedactionTag(event: ErrorEvent): void {
  event.tags = {
    ...event.tags,
    redaction_version: SENTRY_REDACTION_VERSION,
  };
}

/** Shared `beforeSend` — scrub PII, drop high-risk routes, strip IP. */
export function sentryBeforeSend(
  event: ErrorEvent,
  _hint?: EventHint
): ErrorEvent | null {
  if (shouldDropSentryEvent(event)) {
    return null;
  }
  scrubStringLeaves(event);
  stripUserIp(event);
  applyRedactionTag(event);
  return event;
}

/** Regex set exported for docs / parity checks with backend. */
export const SENTRY_SCRUB_PATTERNS = {
  jwt: JWT_RE.source,
  nrc: NRC_RE.source,
  email: EMAIL_RE.source,
  phone: PHONE_RE.source,
  whatsapp_c_us: WHATSAPP_CUS_RE.source,
} as const;
