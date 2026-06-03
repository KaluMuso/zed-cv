"""Persist and query in-app notification inbox rows."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import Client

from app.schemas.notifications import InAppNotification, InAppNotificationType

logger = logging.getLogger(__name__)

V1_TYPES: frozenset[str] = frozenset(
    {"web_push", "tier_expiry", "invoice", "admin_broadcast"}
)


def _row_to_model(row: dict[str, Any]) -> InAppNotification:
    payload = row.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    return InAppNotification(
        id=str(row["id"]),
        type=row["type"],
        payload=payload,
        read_at=row.get("read_at"),
        created_at=row["created_at"],
    )


async def record_in_app_notification(
    user_id: str,
    notification_type: InAppNotificationType,
    payload: dict[str, Any],
    supabase: Client,
) -> str | None:
    """Best-effort insert; returns new row id or None on failure."""
    if notification_type not in V1_TYPES:
        logger.warning("unknown in-app notification type: %s", notification_type)
        return None
    try:
        result = (
            supabase.table("notifications")
            .insert(
                {
                    "user_id": user_id,
                    "type": notification_type,
                    "payload": payload,
                }
            )
            .execute()
        )
        if result.data and isinstance(result.data[0], dict):
            return str(result.data[0].get("id") or "")
    except Exception:
        logger.warning(
            "failed to record in-app notification user=%s type=%s",
            user_id,
            notification_type,
            exc_info=True,
        )
    return None


async def list_user_notifications(
    user_id: str,
    supabase: Client,
    *,
    limit: int = 50,
) -> tuple[list[InAppNotification], int]:
    """Return recent notifications and unread count for the user."""
    capped = max(1, min(limit, 100))
    rows_result = (
        supabase.table("notifications")
        .select("id, type, payload, read_at, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(capped)
        .execute()
    )
    items = [
        _row_to_model(row)
        for row in (rows_result.data or [])
        if isinstance(row, dict)
    ]

    unread_result = (
        supabase.table("notifications")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .is_("read_at", "null")
        .execute()
    )
    unread_count = int(unread_result.count or 0)
    return items, unread_count


async def mark_notification_read(
    user_id: str,
    notification_id: str,
    supabase: Client,
) -> InAppNotification | None:
    """Mark one notification read; returns None when not found for this user."""
    existing = (
        supabase.table("notifications")
        .select("id, type, payload, read_at, created_at")
        .eq("id", notification_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        return None

    row = existing.data[0]
    if row.get("read_at"):
        return _row_to_model(row)

    now_iso = datetime.now(timezone.utc).isoformat()
    updated = (
        supabase.table("notifications")
        .update({"read_at": now_iso})
        .eq("id", notification_id)
        .eq("user_id", user_id)
        .execute()
    )
    if updated.data and isinstance(updated.data[0], dict):
        return _row_to_model(updated.data[0])
    return _row_to_model({**row, "read_at": now_iso})
