"""Supabase Storage helpers for CV blobs and portable data exports."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

DOCUMENTS_BUCKET = "documents"
EXPORT_URL_TTL_SECONDS = 7 * 24 * 3600


def purge_cv_storage(user_id: str, supabase: Any) -> int:
    """Remove all files under cvs/{user_id}/ in the documents bucket."""
    prefix = f"cvs/{user_id}"
    try:
        listing = supabase.storage.from_(DOCUMENTS_BUCKET).list(prefix)
    except Exception as exc:  # noqa: BLE001
        log.warning("storage list failed for %s: %s", prefix, exc)
        return 0

    if not listing:
        return 0

    paths = [
        f"{prefix}/{entry['name']}"
        for entry in listing
        if isinstance(entry, dict) and entry.get("name")
    ]
    if not paths:
        return 0

    try:
        supabase.storage.from_(DOCUMENTS_BUCKET).remove(paths)
    except Exception as exc:  # noqa: BLE001
        log.warning("storage remove failed for %s: %s", prefix, exc)
        return 0
    return len(paths)


def download_storage_object(path: str, supabase: Any) -> bytes | None:
    """Download a single object from the documents bucket."""
    try:
        data = supabase.storage.from_(DOCUMENTS_BUCKET).download(path)
        if isinstance(data, bytes):
            return data
        if hasattr(data, "read"):
            return data.read()
    except Exception as exc:  # noqa: BLE001
        log.warning("storage download failed for %s: %s", path, exc)
    return None


def upload_export_zip(
    user_id: str,
    request_id: str,
    zip_bytes: bytes,
    supabase: Any,
) -> tuple[str, str]:
    """Upload export ZIP and return (signed_url, expires_at_iso)."""
    storage_path = f"exports/{user_id}/{request_id}.zip"
    supabase.storage.from_(DOCUMENTS_BUCKET).upload(
        storage_path,
        zip_bytes,
        {"content-type": "application/zip", "upsert": "true"},
    )
    signed = supabase.storage.from_(DOCUMENTS_BUCKET).create_signed_url(
        storage_path,
        EXPORT_URL_TTL_SECONDS,
    )
    url = signed.get("signedURL") or signed.get("signedUrl") or ""
    if not url:
        raise RuntimeError("Storage did not return a signed export URL")
    from datetime import datetime, timedelta, timezone

    expires = datetime.now(timezone.utc) + timedelta(seconds=EXPORT_URL_TTL_SECONDS)
    return url, expires.isoformat()
