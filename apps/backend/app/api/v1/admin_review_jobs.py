"""Admin review queue for jobs missing apply path or deadline (Track 4e)."""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.deps import get_supabase, require_admin
from app.schemas.admin import AdminJobReviewQueue, AdminJobReviewRow, AdminJobReviewUpdate
from app.services.job_activation import can_publish_after_admin_edit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


class ReviewJobsBulkRequest(BaseModel):
    job_ids: list[str] = Field(..., min_length=1, max_length=100)


def _split_reasons(value: str | None) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in value.replace(",", " ").split() if p.strip()]


@router.get("/review-jobs", response_model=AdminJobReviewQueue)
async def list_review_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    supabase=Depends(get_supabase),
):
    """Jobs pending review (is_review_required), newest first."""
    query = (
        supabase.table("jobs")
        .select(
            "id, title, company, source, source_url, review_reason, "
            "admin_review_reason, created_at",
            count="exact",
        )
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .order("created_at", desc=True)
    )
    offset = (page - 1) * per_page
    result = query.range(offset, offset + per_page - 1).execute()
    total = result.count or 0
    pages = math.ceil(total / per_page) if total > 0 else 1
    rows = [
        AdminJobReviewRow(
            id=j["id"],
            title=j["title"],
            company=j.get("company"),
            source=j["source"],
            source_url=j.get("source_url"),
            reasons=_split_reasons(j.get("review_reason") or j.get("admin_review_reason")),
            created_at=j.get("created_at"),
        )
        for j in (result.data or [])
    ]
    return AdminJobReviewQueue(
        jobs=rows, total=total, page=page, per_page=per_page, pages=pages
    )


@router.patch("/review-jobs/{job_id}")
async def update_review_job(
    job_id: str,
    body: AdminJobReviewUpdate,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    """Fill apply fields / deadline and promote when complete."""
    patch = body.model_dump(exclude_unset=True, exclude_none=True, mode="json")
    existing = (
        supabase.table("jobs")
        .select("apply_url, apply_email, closing_date, review_reason")
        .eq("id", job_id)
        .single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Job not found")

    merged = {**existing.data, **patch}
    now = datetime.now(timezone.utc).isoformat()
    can_publish = can_publish_after_admin_edit(
        merged.get("apply_url"),
        merged.get("apply_email"),
        merged.get("closing_date"),
    )
    patch.update(
        {
            "updated_at": now,
            "updated_by_user_id": current_user["id"],
            "is_review_required": not can_publish,
            "review_reason": None if can_publish else merged.get("review_reason"),
            "admin_review_reason": None if can_publish else "pending_admin",
            "is_active": can_publish,
            "admin_reviewed_at": now if can_publish else None,
            "admin_reviewed_by_user_id": current_user["id"] if can_publish else None,
        }
    )
    result = supabase.table("jobs").update(patch).eq("id", job_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"id": job_id, "is_active": can_publish, "is_review_required": not can_publish}


@router.post("/review-jobs/bulk-mark-duplicate")
async def bulk_mark_duplicate(
    body: ReviewJobsBulkRequest,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    now = datetime.now(timezone.utc).isoformat()
    for job_id in body.job_ids:
        supabase.table("jobs").update(
            {
                "is_active": False,
                "is_review_required": False,
                "review_reason": "duplicate",
                "admin_reviewed_at": now,
                "admin_reviewed_by_user_id": current_user["id"],
                "updated_at": now,
            }
        ).eq("id", job_id).execute()
    return {"updated": len(body.job_ids)}


@router.post("/review-jobs/bulk-permanently-inactive")
async def bulk_permanently_inactive(
    body: ReviewJobsBulkRequest,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    now = datetime.now(timezone.utc).isoformat()
    for job_id in body.job_ids:
        supabase.table("jobs").update(
            {
                "is_active": False,
                "is_review_required": False,
                "review_reason": "permanently_inactive",
                "admin_reviewed_at": now,
                "admin_reviewed_by_user_id": current_user["id"],
                "updated_at": now,
            }
        ).eq("id", job_id).execute()
    return {"updated": len(body.job_ids)}
