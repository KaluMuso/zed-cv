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
    "free": 3,
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
    matches_limit: int = 3
    matches_unlimited: bool = Field(
        False,
        description="True when matches_limit is the unlimited sentinel (99999).",
    )
    active: bool = True
    expires_at: Optional[datetime] = None
    welcome_match_bonus: Optional[int] = Field(
        default=None,
        description="Free-tier welcome quota while welcome_match_bonus_until is active.",
    )
    welcome_match_bonus_until: Optional[datetime] = None
    promo_until: Optional[datetime] = Field(
        default=None,
        description="First-two-months 50% paid-tier checkout discount ends at this instant.",
    )
    welcome_bonus_active: Optional[bool] = None

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


class PaymentHistoryRow(BaseModel):
    id: str
    amount: int = Field(description="Amount in ngwee")
    currency: str = "ZMW"
    payment_method: str
    provider: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PaymentHistoryList(BaseModel):
    payments: list[PaymentHistoryRow]
    total: int


class InvoiceDetail(BaseModel):
    invoice_number: str
    payment_id: str
    reference: str
    status: str
    amount_ngwee: int
    amount_kwacha: int
    currency: str = "ZMW"
    tier: str
    tier_label: str
    payment_method: str
    provider: Optional[str] = None
    issued_at: Optional[datetime] = None
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


class SubscriptionCancelResponse(BaseModel):
    status: str
    message: str
    tier: str
    active_until: Optional[datetime] = None
    cancelled_at: datetime
