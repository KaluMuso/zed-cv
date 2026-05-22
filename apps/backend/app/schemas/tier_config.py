"""Tier configuration schemas (DB-backed pricing + match quotas)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.subscription import SubscriptionTier

VALID_TIERS = frozenset(t.value for t in SubscriptionTier)
UNLIMITED_MATCHES = 99999


class TierConfigRow(BaseModel):
    tier: str
    display_name: str
    price_ngwee: int = Field(ge=0, description="List price in ngwee (1 ZMW = 100 ngwee)")
    matches_limit: int = Field(ge=0, description="Monthly match quota; 99999 = unlimited")
    sort_order: int = 0
    updated_at: Optional[datetime] = None
    checkout_price_ngwee: Optional[int] = Field(
        default=None,
        description="Effective checkout price for the authenticated user (50% promo when eligible).",
    )
    promotion_active: Optional[bool] = Field(
        default=None,
        description="True when the caller is within the first-two-months discount window.",
    )


class TierConfigList(BaseModel):
    tiers: list[TierConfigRow]


class TierConfigUpdateItem(BaseModel):
    tier: str = Field(
        ...,
        pattern="^(free|starter|professional|super_standard)$",
    )
    display_name: str = Field(..., min_length=1, max_length=64)
    price_ngwee: int = Field(..., ge=0)
    matches_limit: int = Field(..., ge=0, le=999999)


class TierConfigBulkUpdate(BaseModel):
    tiers: list[TierConfigUpdateItem] = Field(..., min_length=4, max_length=4)
