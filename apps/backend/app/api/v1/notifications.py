"""In-app notification inbox — GET /notifications, PATCH /notifications/{id}/read."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user_id, get_supabase
from app.schemas.notifications import (
    InAppNotificationList,
    InAppNotificationReadResponse,
)
from app.services.in_app_notifications import (
    list_user_notifications,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=InAppNotificationList)
async def get_notifications(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
    limit: int = Query(default=50, ge=1, le=100),
):
    items, unread_count = await list_user_notifications(
        user_id, supabase, limit=limit
    )
    return InAppNotificationList(items=items, unread_count=unread_count)


@router.patch("/{notification_id}/read", response_model=InAppNotificationReadResponse)
async def mark_notification_as_read(
    notification_id: UUID,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    row = await mark_notification_read(user_id, str(notification_id), supabase)
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return InAppNotificationReadResponse(notification=row)
