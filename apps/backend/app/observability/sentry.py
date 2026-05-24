"""Sentry SDK initialisation (no-op when DSN is empty)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.observability.sentry_scrub import scrub_sentry_event

if TYPE_CHECKING:
    from app.core.config import Settings


def before_send(event: dict[str, Any], hint: Any = None) -> dict[str, Any] | None:
    del hint
    return scrub_sentry_event(event)


def init_sentry(settings: "Settings") -> None:
    """Initialise Sentry when `settings.sentry_dsn` is set."""
    if not settings.sentry_dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=0.1,
        send_default_pii=False,
        before_send=before_send,
    )
