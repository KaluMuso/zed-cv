"""Bwana career assistant chat API."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.deps import get_current_user, get_supabase
from app.core.rate_limit import limiter
from app.services.bwana_chat import handle_bwana_chat

router = APIRouter(prefix="/bwana", tags=["Bwana"])


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
        response, source, took_ms = await handle_bwana_chat(
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
    )
