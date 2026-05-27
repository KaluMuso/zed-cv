"""Persist and list versioned cover letters scoped to a user match."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import HTTPException
from supabase import Client

GeneratedBy = Literal["ai", "user_edit"]


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


def assert_match_owned(user_id: str, match_id: str, supabase: Client) -> dict[str, Any]:
    """Return match row when it belongs to the user."""
    res = (
        supabase.table("matches")
        .select("id, user_id, job_id")
        .eq("id", match_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    row = _first_row(res.data)
    if not row:
        raise HTTPException(status_code=404, detail="Match not found")
    return row


def _next_version_number(
    user_id: str, match_id: str, supabase: Client
) -> int:
    res = (
        supabase.table("cover_letter_versions")
        .select("version_number")
        .eq("user_id", user_id)
        .eq("match_id", match_id)
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )
    row = _first_row(res.data)
    if not row:
        return 1
    return int(row["version_number"]) + 1


def _validate_parent(
    user_id: str,
    match_id: str,
    parent_version_id: str | None,
    supabase: Client,
) -> None:
    if not parent_version_id:
        return
    res = (
        supabase.table("cover_letter_versions")
        .select("id")
        .eq("id", parent_version_id)
        .eq("user_id", user_id)
        .eq("match_id", match_id)
        .limit(1)
        .execute()
    )
    if not _first_row(res.data):
        raise HTTPException(status_code=400, detail="parent_version_id not found for this match")


def save_cover_letter_version(
    *,
    user_id: str,
    match_id: str,
    content_md: str,
    generated_by: GeneratedBy,
    parent_version_id: str | None,
    supabase: Client,
) -> dict[str, Any]:
    """Insert a new cover letter version (version_number = max + 1)."""
    trimmed = content_md.strip()
    if not trimmed:
        raise HTTPException(status_code=422, detail="content_md cannot be empty")

    _validate_parent(user_id, match_id, parent_version_id, supabase)
    version_number = _next_version_number(user_id, match_id, supabase)

    payload = {
        "user_id": user_id,
        "match_id": match_id,
        "content_md": trimmed,
        "version_number": version_number,
        "parent_version_id": parent_version_id,
        "generated_by": generated_by,
    }
    res = supabase.table("cover_letter_versions").insert(payload).execute()
    row = _first_row(res.data)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to save cover letter version")
    return row


def list_cover_letter_versions(
    user_id: str, match_id: str, supabase: Client
) -> list[dict[str, Any]]:
    res = (
        supabase.table("cover_letter_versions")
        .select(
            "id, version_number, parent_version_id, generated_by, created_at, content_md"
        )
        .eq("user_id", user_id)
        .eq("match_id", match_id)
        .order("version_number", desc=True)
        .execute()
    )
    return list(res.data or [])
