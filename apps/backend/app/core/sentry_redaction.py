"""Sentry `before_send` PII redactor (task #77).

`send_default_pii=False` already hides Sentry's standard PII fields
(IP, user.email when set by the SDK). It does NOT scrub our
domain-specific PII that ends up inside exception messages, request
bodies, breadcrumbs, and extras — phone numbers (which the OTP flow
echoes), email addresses (which the CV parser extracts), and
JWT-shaped tokens (which can appear in stack-trace locals).

This module owns the redaction. Kept out of main.py so unit tests can
import the function directly and feed it event-shaped dicts without
booting the full app or initialising the SDK.
"""
from __future__ import annotations

import re
from typing import Any

# ── patterns ──
# Order of application matters: JWT first (most specific, contains
# characters that overlap with email + phone), then email, then phone.
# A misordered chain would, for example, redact the local-part of an
# email as a "phone" if we ran phone first.

# Zambian E.164 phone — the only format the platform accepts (see the
# phoneSchema in /auth and the +260 enforcement in OTPRequest). We
# only redact this specific shape so unrelated numerics in logs
# (timestamps, IDs) survive intact.
_PHONE_RE = re.compile(r"\+260\d{9}")

# Pragmatic email pattern. Doesn't pretend to cover the full RFC 5322
# grammar — it just needs to catch the shapes that show up in our
# logs (CV-parsed addresses, support@vergeo emails, etc.) without
# false-positives on URLs or version strings.
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)

# JWT pattern: three base64url segments separated by dots, prefixed by
# "eyJ" (the base64 encoding of `{"`, which every JOSE header starts
# with). Length floors on each segment avoid matching arbitrary
# dotted tokens. The output of `python-jose` always satisfies this.
_JWT_RE = re.compile(
    r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{4,}"
)


def redact_string(s: str) -> str:
    """Apply the three redactions to a single string, in safe order."""
    s = _JWT_RE.sub("[jwt-redacted]", s)
    s = _EMAIL_RE.sub("[email-redacted]", s)
    s = _PHONE_RE.sub("[phone-redacted]", s)
    return s


def _walk(obj: Any) -> Any:
    """Recursively walk dicts/lists/tuples, redacting any string values.

    Returns the same object back (mutates in place for dicts/lists) so
    callers can swap or pass through. Tuples are immutable so we
    return a fresh tuple if we touched anything.
    """
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, str):
                obj[k] = redact_string(v)
            else:
                _walk(v)
        return obj
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                obj[i] = redact_string(v)
            else:
                _walk(v)
        return obj
    if isinstance(obj, tuple):
        # rare in Sentry payloads (frame.vars sometimes), but handled
        # for completeness so a tuple doesn't escape redaction.
        return tuple(
            redact_string(v) if isinstance(v, str) else _walk(v) for v in obj
        )
    return obj


def before_send(event: dict[str, Any], hint: Any = None) -> dict[str, Any]:
    """Sentry `before_send` hook. Mutates `event` in place and returns it.

    Idempotent: redacting an already-redacted event is a no-op (the
    redaction tokens don't match any of the patterns). Returning `None`
    here would drop the event entirely — we always want to keep the
    breadcrumb trail, just with the PII stripped.

    `hint` is unused — Sentry passes a dict with the original exception
    object when applicable, which we don't need for redaction. Kept in
    the signature (with a default of None) to match the SDK contract
    and to allow tests to omit it.
    """
    del hint  # explicitly unused; named for the SDK contract.
    _walk(event)
    return event
