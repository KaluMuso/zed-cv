"""Client analytics events (apply clicks, etc.)."""
from __future__ import annotations

import logging
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import get_current_user_id, get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

ApplyClickSource = Literal["direct", "source_fallback", "enriched"]


class AnalyticsEventCreate(BaseModel):
    event: str = Field(..., max_length=64)
    properties: dict[str, Any] = Field(default_factory=dict)


@router.post("/events", status_code=204)
async def track_event(
    body: AnalyticsEventCreate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Best-effort product analytics (e.g. apply_click on /matches)."""
    try:
        supabase.table("analytics_events").insert({
            "event": body.event,
            "properties": body.properties,
            "user_id": user_id,
        }).execute()
    except Exception as exc:
        logger.debug("analytics_events insert failed: %s", exc)
