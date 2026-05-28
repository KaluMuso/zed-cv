"""Web Push subscription routes."""
from fastapi import APIRouter, Depends, Header, Request

from app.core.deps import get_current_user_id, get_supabase
from app.schemas.push import PushSubscribeRequest, PushSubscribeResponse
from app.services.web_push import upsert_subscription, vapid_configured
from app.core.config import get_settings

router = APIRouter(prefix="/push", tags=["Push"])


@router.post("/subscribe", response_model=PushSubscribeResponse)
async def subscribe_push(
    body: PushSubscribeRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    settings = get_settings()
    if not vapid_configured(settings):
        return PushSubscribeResponse(
            ok=False,
            message="Web Push is not configured on this server",
        )

    user_agent = request.headers.get("user-agent")
    await upsert_subscription(
        user_id,
        body.endpoint,
        body.keys.p256dh,
        body.keys.auth,
        supabase,
        user_agent=user_agent,
    )
    return PushSubscribeResponse(ok=True, message="Subscribed")
