"""Subscription and payment schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class SubscriptionTier(str, Enum):
    mwana = "mwana"
    mwezi = "mwezi"
    bwino = "bwino"


class PaymentMethod(str, Enum):
    mtn_money = "mtn_money"
    airtel_money = "airtel_money"


class Subscription(BaseModel):
    id: str
    tier: SubscriptionTier
    status: str
    current_period_start: datetime
    current_period_end: Optional[datetime] = None
    matches_used: int = 0
    matches_limit: int = 5


class PaymentInitiate(BaseModel):
    tier: SubscriptionTier
    payment_method: PaymentMethod
    phone: str = Field(..., pattern=r"^\+260[0-9]{9}$")


class PaymentInitiateResponse(BaseModel):
    transaction_token: str
    payment_url: str
    status: str = "pending"
