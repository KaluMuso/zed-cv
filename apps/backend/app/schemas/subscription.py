from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class SubscriptionTier(str, Enum):
    free = "free"
    starter = "starter"
    professional = "professional"
    super_standard = "super_standard"

class PaymentMethod(str, Enum):
    mtn_money = "mtn_money"
    airtel_money = "airtel_money"


# Single source of truth for per-tier monthly match quotas. Import from here;
# do not redefine elsewhere. super_standard uses 99999 as a numeric "unlimited"
# sentinel so existing quota arithmetic doesn't need a NULL branch (matches
# migration 005).
TIER_LIMITS: dict[str, int] = {
    "free": 10,
    "starter": 50,
    "professional": 125,
    "super_standard": 99999,
}

# Prices in ngwee (1 ZMW = 100 ngwee).
TIER_PRICES: dict[str, int] = {
    "free": 0,
    "starter": 12500,
    "professional": 25000,
    "super_standard": 50000,
}


class Subscription(BaseModel):
    tier: SubscriptionTier
    matches_used: int = 0
    matches_limit: int = 10
    active: bool = True
    expires_at: Optional[datetime] = None

class PaymentInitiate(BaseModel):
    tier: SubscriptionTier
    payment_method: str = Field(
        ...,
        description=(
            "DPO short names (mtn, airtel, card) or Lenco sub-channels "
            "(lenco_mtn_money, lenco_airtel_money, lenco_card). Generic "
            "'lenco' is accepted and resolved from phone prefix."
        ),
    )
    phone: str = Field(..., pattern=r"^\+260[0-9]{9}$")

class PaymentInitiateResponse(BaseModel):
    message: str
    transaction_id: str


class PaymentVerifyRequest(BaseModel):
    reference: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Lenco widget reference (e.g. zedapply-<uuid>).",
    )
    tier: SubscriptionTier


class PaymentVerifyResponse(BaseModel):
    status: str
    tier: str
    reference: str
    payment_id: str | None = None
    message: str
