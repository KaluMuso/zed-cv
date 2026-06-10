from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BoosterPurchaseRequest(BaseModel):
    sku: str
    phone: str


class BoosterPurchaseResponse(BaseModel):
    message: str
    transaction_id: str
    reference: str
    amount_ngwee: int


class EntitlementResponse(BaseModel):
    id: str
    user_id: str
    booster_sku: str
    payment_id: Optional[str]
    status: str
    created_at: datetime
    consumed_at: Optional[datetime]


class ConsumeBoosterRequest(BaseModel):
    job_id: str
