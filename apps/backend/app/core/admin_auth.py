"""Shared auth for n8n / admin cron endpoints."""
from fastapi import Header, HTTPException

from app.core.config import Settings, resolve_admin_api_key


def _admin_key_matches(
    settings: Settings,
    admin_api_key: str | None,
    x_admin_api_key: str | None,
    ingest_api_key: str | None,
    x_ingest_api_key: str | None,
) -> bool:
    expected = resolve_admin_api_key(settings)
    if not expected:
        return False
    supplied = (
        admin_api_key
        or x_admin_api_key
        or ingest_api_key
        or x_ingest_api_key
    )
    return bool(supplied and supplied == expected)


def require_admin_api_key(
    settings: Settings,
    admin_api_key: str | None = None,
    x_admin_api_key: str | None = None,
    ingest_api_key: str | None = None,
    x_ingest_api_key: str | None = None,
) -> None:
    if not _admin_key_matches(
        settings,
        admin_api_key,
        x_admin_api_key,
        ingest_api_key,
        x_ingest_api_key,
    ):
        raise HTTPException(status_code=401, detail="Invalid admin API key")
