"""Deprecated — use app.observability.sentry_scrub / app.observability.sentry."""
from app.observability.sentry import before_send
from app.observability.sentry_scrub import redact_string

__all__ = ["before_send", "redact_string"]
