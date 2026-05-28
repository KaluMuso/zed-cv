"""Web Push subscription schemas."""
from pydantic import BaseModel, Field


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(..., min_length=1)
    auth: str = Field(..., min_length=1)


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=8)
    keys: PushSubscriptionKeys
    expiration_time: int | None = Field(None, alias="expirationTime")

    model_config = {"populate_by_name": True}


class PushSubscribeResponse(BaseModel):
    ok: bool = True
    message: str = "Subscribed"


class PushTestRequest(BaseModel):
    user_id: str | None = None


class PushTestResponse(BaseModel):
    delivered: int
    message: str
