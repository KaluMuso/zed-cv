"""Public FAQs catalog + superadmin FAQs editor."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import get_supabase, require_superadmin


class FaqRow(BaseModel):
    id: UUID
    question: str
    answer: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class FaqList(BaseModel):
    faqs: list[FaqRow]


class FaqCreate(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    is_active: bool = True
    sort_order: int = 0


class FaqUpdate(BaseModel):
    question: Optional[str] = Field(None, min_length=1)
    answer: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


public_router = APIRouter(prefix="/faqs", tags=["FAQs"])
admin_router = APIRouter(
    prefix="/admin/faqs",
    tags=["Admin"],
    dependencies=[Depends(require_superadmin)],
)


@public_router.get("", response_model=FaqList)
async def list_public_faqs(supabase=Depends(get_supabase)):
    """Public FAQ catalog."""
    result = (
        supabase.table("site_faqs")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )
    return FaqList(faqs=result.data or [])


@admin_router.get("", response_model=FaqList)
async def list_admin_faqs(supabase=Depends(get_supabase)):
    """Admin FAQ catalog."""
    result = (
        supabase.table("site_faqs")
        .select("*")
        .order("sort_order")
        .execute()
    )
    return FaqList(faqs=result.data or [])


@admin_router.post("", response_model=FaqRow)
async def create_admin_faq(
    body: FaqCreate,
    supabase=Depends(get_supabase),
):
    """Admin create FAQ."""
    row = body.model_dump()
    result = supabase.table("site_faqs").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create FAQ")
    return result.data[0]


@admin_router.patch("/{faq_id}", response_model=FaqRow)
async def update_admin_faq(
    faq_id: UUID,
    body: FaqUpdate,
    supabase=Depends(get_supabase),
):
    """Admin update FAQ."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = supabase.table("site_faqs").update(updates).eq("id", str(faq_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return result.data[0]


@admin_router.delete("/{faq_id}")
async def delete_admin_faq(
    faq_id: UUID,
    supabase=Depends(get_supabase),
):
    """Admin delete FAQ."""
    result = supabase.table("site_faqs").delete().eq("id", str(faq_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"success": True}
