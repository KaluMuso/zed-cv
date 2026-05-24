# Observability

Zed CV uses [Sentry](https://sentry.io) on the Next.js frontend and FastAPI backend. Events must not contain PII sent to third-party processors without explicit consent (ZDPA).

## PII redaction in Sentry

Both runtimes run a `before_send` hook that scrubs string leaves in the event payload and drops certain high-risk routes entirely.

| Pattern | Regex (summary) | Replacement |
| --- | --- | --- |
| JWT | `eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+` | `[REDACTED_JWT]` |
| NRC | `\d{6}/\d{2}/\d` | `[REDACTED_NRC]` |
| Email | `[\w.+-]+@[\w.-]+\.\w+` | `[REDACTED_EMAIL]` |
| Zambian phone | `(?:\+?260\|0)9[567]\d{7}` | `[REDACTED_PHONE]` |
| WhatsApp JID | `\d{9,15}@c\.us` | `[REDACTED_PHONE]` |

Redactions run in order: JWT → NRC → WhatsApp JID → email → phone (WhatsApp before email so `@c.us` is not mistaken for an email). Processed events are tagged `redaction_version: 1.0`.

### Dropped events (not scrubbed)

These events return `null` from `before_send` so nothing is transmitted:

- Any event mentioning `/auth/verify-otp` or `/auth/otp/verify` (OTP codes and phones in request bodies).
- Any event for `/webhooks/lenco` that includes a non-empty `request.data` body (payment webhook payloads).

### IP addresses

`send_default_pii=False` is set on both SDKs. The scrubber also removes `user.ip_address` and common proxy IP headers from the event.

### Code locations

- Frontend: `apps/frontend/src/lib/sentry_scrub.ts`, wired via `apps/frontend/sentry.shared.ts`
- Backend: `apps/backend/app/observability/sentry_scrub.py`, init in `apps/backend/app/observability/sentry.py`

### Staging verification

Trigger a test error that embeds a phone number:

```javascript
throw new Error("OTP send failed for +260977123456");
```

In Sentry, the message should read `OTP send failed for [REDACTED_PHONE]` and the event should show `redaction_version: 1.0`.

Backend equivalent:

```python
raise RuntimeError("OTP send failed for +260977123456")
```

(Use `/api/v1/test-error` only when `DEBUG=true`.)
