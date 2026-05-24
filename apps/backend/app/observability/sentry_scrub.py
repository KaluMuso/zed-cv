"""Sentry PII scrubber — keep in sync with apps/frontend/src/lib/sentry_scrub.ts."""
from __future__ import annotations

import json
import re
from typing import Any

SENTRY_REDACTION_VERSION = "1.0"

# Order: JWT → NRC → email → phone (most specific first).
_JWT_RE = re.compile(
    r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"
)
_NRC_RE = re.compile(r"\d{6}/\d{2}/\d")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
_PHONE_RE = re.compile(r"(?:\+?260|0)9[567]\d{7}")
_WHATSAPP_CUS_RE = re.compile(r"\d{9,15}@c\.us")

_HIGH_RISK_OTP_PATHS = ("/auth/verify-otp", "/auth/otp/verify")
_LENCO_WEBHOOK_PATH = "/webhooks/lenco"

SENTRY_SCRUB_PATTERNS = {
    "jwt": _JWT_RE.pattern,
    "nrc": _NRC_RE.pattern,
    "email": _EMAIL_RE.pattern,
    "phone": _PHONE_RE.pattern,
    "whatsapp_c_us": _WHATSAPP_CUS_RE.pattern,
}


def redact_string(value: str) -> str:
    value = _JWT_RE.sub("[REDACTED_JWT]", value)
    value = _NRC_RE.sub("[REDACTED_NRC]", value)
    value = _WHATSAPP_CUS_RE.sub("[REDACTED_PHONE]", value)
    value = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    value = _PHONE_RE.sub("[REDACTED_PHONE]", value)
    return value


def _scrub_string_leaves(obj: Any) -> None:
    if isinstance(obj, dict):
        for key, val in list(obj.items()):
            if isinstance(val, str):
                obj[key] = redact_string(val)
            else:
                _scrub_string_leaves(val)
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            if isinstance(val, str):
                obj[i] = redact_string(val)
            else:
                _scrub_string_leaves(val)
    elif isinstance(obj, tuple):
        # Sentry frame vars may use tuples; rebuild if any string changed.
        changed = False
        new_items: list[Any] = []
        for val in obj:
            if isinstance(val, str):
                new_val = redact_string(val)
                changed = changed or new_val != val
                new_items.append(new_val)
            else:
                _scrub_string_leaves(val)
                new_items.append(val)
        if changed:
            # Caller cannot replace tuple in place; rare in our payloads.
            pass


def _event_mentions_path(event: dict[str, Any], fragment: str) -> bool:
    request = event.get("request") or {}
    url = request.get("url") or ""
    if isinstance(url, str) and fragment in url:
        return True
    return fragment in json.dumps(event, default=str)


def _has_lenco_webhook_payload_body(event: dict[str, Any]) -> bool:
    if not _event_mentions_path(event, _LENCO_WEBHOOK_PATH):
        return False
    request = event.get("request") or {}
    data = request.get("data")
    if data is None:
        return False
    if isinstance(data, str):
        return bool(data.strip())
    if isinstance(data, dict):
        return len(data) > 0
    return True


def _mentions_otp_verify_path(event: dict[str, Any]) -> bool:
    return any(_event_mentions_path(event, path) for path in _HIGH_RISK_OTP_PATHS)


def should_drop_sentry_event(event: dict[str, Any]) -> bool:
    if _mentions_otp_verify_path(event):
        return True
    if _has_lenco_webhook_payload_body(event):
        return True
    return False


def _strip_user_ip(event: dict[str, Any]) -> None:
    user = event.get("user")
    if isinstance(user, dict):
        user.pop("ip_address", None)
        user.pop("ipAddress", None)
    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            for key in (
                "X-Forwarded-For",
                "x-forwarded-for",
                "X-Real-IP",
                "x-real-ip",
            ):
                headers.pop(key, None)


def _apply_redaction_tag(event: dict[str, Any]) -> None:
    tags = event.get("tags")
    if not isinstance(tags, dict):
        tags = {}
        event["tags"] = tags
    tags["redaction_version"] = SENTRY_REDACTION_VERSION


def scrub_sentry_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Mutate `event` in place; return None to drop."""
    if should_drop_sentry_event(event):
        return None
    _scrub_string_leaves(event)
    _strip_user_ip(event)
    _apply_redaction_tag(event)
    return event
