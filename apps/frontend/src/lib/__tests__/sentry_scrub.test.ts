import { describe, expect, it } from "vitest";
import {
  redactString,
  sentryBeforeSend,
  shouldDropSentryEvent,
  SENTRY_SCRUB_PATTERNS,
} from "../sentry_scrub";

describe("redactString", () => {
  it("redacts Zambian E.164 phone", () => {
    const out = redactString("OTP send failed for +260977123456");
    expect(out).toBe("OTP send failed for [REDACTED_PHONE]");
    expect(out).not.toContain("+260977123456");
  });

  it("redacts email, NRC, and JWT", () => {
    const raw =
      "nrc 123456/78/9 email a@b.co jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig";
    const out = redactString(raw);
    expect(out).toContain("[REDACTED_NRC]");
    expect(out).toContain("[REDACTED_EMAIL]");
    expect(out).toContain("[REDACTED_JWT]");
  });

  it("exports pattern sources for parity checks", () => {
    expect(SENTRY_SCRUB_PATTERNS.phone).toContain("260");
    expect(SENTRY_SCRUB_PATTERNS.whatsapp_c_us).toMatch(/c\\.us/);
  });
});

describe("shouldDropSentryEvent", () => {
  it("drops OTP verify routes", () => {
    expect(
      shouldDropSentryEvent({
        request: { url: "https://api.example.com/api/v1/auth/otp/verify" },
      })
    ).toBe(true);
  });

  it("drops Lenco webhook when request body present", () => {
    expect(
      shouldDropSentryEvent({
        request: {
          url: "/api/v1/webhooks/lenco",
          data: { status: "success" },
        },
      })
    ).toBe(true);
  });
});

describe("sentryBeforeSend", () => {
  it("tags redaction_version and scrubs message", () => {
    const event = { message: "fail +260977123456" };
    const result = sentryBeforeSend(event);
    expect(result).toEqual({
      message: "fail [REDACTED_PHONE]",
      tags: { redaction_version: "1.0" },
    });
  });

  it("returns null for OTP verify events", () => {
    expect(
      sentryBeforeSend({
        message: "error on /auth/otp/verify",
      })
    ).toBeNull();
  });
});
