"""Bwana career assistant chat API."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.deps import get_current_user, get_supabase
from app.core.rate_limit import limiter
from app.schemas.bwana_config import BwanaPublicConfig
from app.services.bwana_config import get_bwana_config
from app.services.bwana_chat import handle_bwana_chat

router = APIRouter(prefix="/bwana", tags=["Bwana"])


@router.get("/public-config", response_model=BwanaPublicConfig)
async def bwana_public_config(supabase=Depends(get_supabase)) -> BwanaPublicConfig:
    """Public support contact for widget footer (no escalation WhatsApp)."""
    cfg = get_bwana_config(supabase)
    return BwanaPublicConfig(
        chatbot_display_name=cfg.chatbot_display_name,
        support_email=cfg.support_email,
        support_phone=cfg.support_phone,
        escalation_sla_hours=cfg.escalation_sla_hours,
    )


class BwanaChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(
        default=None,
        max_length=64,
        description="Client session id; generated if omitted",
    )


class BwanaChatResponse(BaseModel):
    response: str
    source: str = Field(
        ...,
        description="faq | llm | escalated",
    )
    took_ms: int
    session_id: str
    escalation_ticket_id: str | None = Field(
        default=None,
        description="Present when source=escalated (e.g. ZD-A1B2C3D4)",
    )
    intent_id: str | None = Field(
        default=None,
        description="FAQ intent id when source=faq",
    )


@router.post("/chat", response_model=BwanaChatResponse)
@limiter.limit("30/minute")
async def bwana_chat(
    request: Request,
    body: BwanaChatRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """Route message through Bwana pipeline (n8n webhook or in-process fallback)."""
    del request
    session_id = (body.session_id or "").strip() or str(uuid.uuid4())
    try:
        response, source, took_ms, ticket_id, intent_id = await handle_bwana_chat(
            user_id=current_user["id"],
            message=body.message.strip(),
            session_id=session_id,
            supabase=supabase,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return BwanaChatResponse(
        response=response,
        source=source,
        took_ms=took_ms,
        session_id=session_id,
        escalation_ticket_id=ticket_id,
        intent_id=intent_id,
    )
