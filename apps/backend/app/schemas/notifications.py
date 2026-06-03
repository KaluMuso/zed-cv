"""In-app notification inbox schemas — GET /notifications, PATCH /notifications/{id}/read."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

InAppNotificationType = Literal[
    "web_push",
    "tier_expiry",
    "invoice",
    "admin_broadcast",
]


class InAppNotificationPayload(BaseModel):
    """Common payload fields; extra keys allowed for type-specific data."""

    title: str = "Notification"
    body: str = ""
    url: str = "/dashboard"

    model_config = {"extra": "allow"}


class InAppNotification(BaseModel):
    id: str
    type: InAppNotificationType
    payload: dict[str, Any] = Field(default_factory=dict)
    read_at: Optional[datetime] = None
    created_at: datetime


class InAppNotificationList(BaseModel):
    items: list[InAppNotification]
    unread_count: int


class InAppNotificationReadResponse(BaseModel):
    notification: InAppNotification
