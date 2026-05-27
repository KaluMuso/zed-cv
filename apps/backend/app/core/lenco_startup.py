"""Fail-fast Lenco production configuration checks."""
from __future__ import annotations

from app.core.config import Settings


def assert_lenco_production_ready(settings: Settings) -> None:
    """Refuse startup when production Lenco env is misconfigured."""
    if settings.lenco_environment != "production":
        return

    assert settings.lenco_verify_signatures is True, (
        "Refusing to start: VERIFY_SIGNATURES must be true in production"
    )
    assert settings.lenco_webhook_secret, (
        "Refusing to start: WEBHOOK_SECRET must be set in production"
    )
    assert settings.lenco_api_key, (
        "Refusing to start: LENCO_API_KEY must be set in production"
    )
    assert settings.lenco_public_key, (
        "Refusing to start: LENCO_PUBLIC_KEY must be set in production"
    )
