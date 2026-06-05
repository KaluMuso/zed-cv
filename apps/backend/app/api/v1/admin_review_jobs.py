"""Admin review queue for jobs missing apply path or deadline (Track 4e)."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_supabase, require_admin
from app.schemas.admin import (
    AdminJobReviewQueue,
    AdminJobReviewRow,
    AdminJobReviewUpdate,
    AdminReviewQueueOverview,
)
from app.schemas.jobs import DeepEnrichTickResponse
from app.services.deep_enrich import run_deep_enrich_tick
from app.services.job_activation import can_publish_after_admin_edit
from app.services.review_queue_cleanup import (
    ACTIVE_NO_DEADLINE_PRESET,
    AUTO_DISMISS_REVIEW_REASONS,
    JUNK_DEACTIVATION_MARKERS,
    apply_active_no_deadline_preset,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


def _split_reasons(value: str | None) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in value.replace(",", " ").split() if p.strip()]


@router.get("/review-jobs/overview", response_model=AdminReviewQueueOverview)
async def review_jobs_overview(supabase=Depends(get_supabase)):
    """Need-review vs deactivated vs customer-visible job counts."""
    from datetime import date

    need = (
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .execute()
    )
    deactivated = (
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_active", False)
        .execute()
    )
    active_public = (
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_active", True)
        .eq("is_review_required", False)
        .or_(
            "apply_url.not.is.null,"
            "apply_email.not.is.null,"
            "contact_phone.not.is.null,"
            "admin_published.eq.true"
        )
        .execute()
    )
    hidden_eligible = (
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .eq("is_active", False)
        .in_("review_reason", list(AUTO_DISMISS_REVIEW_REASONS))
        .execute()
    )
    today = date.today().isoformat()
    expired_eligible = (
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .not_.is_("closing_date", "null")
        .lt("closing_date", today)
        .execute()
    )
    junk_filters = ",".join(
        f"deactivation_reason.ilike.%{marker}%" for marker in JUNK_DEACTIVATION_MARKERS
    )
    junk_eligible = (
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .eq("is_active", False)
        .or_(junk_filters)
        .execute()
    )
    active_no_deadline = apply_active_no_deadline_preset(
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
    ).execute()
    return AdminReviewQueueOverview(
        need_review=need.count or 0,
        deactivated=deactivated.count or 0,
        active_public=active_public.count or 0,
        auto_dismiss_hidden_eligible=hidden_eligible.count or 0,
        dismiss_expired_eligible=expired_eligible.count or 0,
        dismiss_junk_eligible=junk_eligible.count or 0,
        active_no_deadline_pending=active_no_deadline.count or 0,
    )


@router.get("/review-jobs", response_model=AdminJobReviewQueue)
async def list_review_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    preset: str | None = Query(
        None,
        description=(
            "Queue filter preset. "
            f"`{ACTIVE_NO_DEADLINE_PRESET}` = active, review_reason=no_deadline, apply path present."
        ),
    ),
    supabase=Depends(get_supabase),
):
    """Jobs pending review (is_review_required), newest first."""
    query = (
        supabase.table("jobs")
        .select(
            "id, title, company, source, source_url, review_reason, "
            "admin_review_reason, is_active, created_at",
            count="exact",
        )
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .order("created_at", desc=True)
    )
    if preset == ACTIVE_NO_DEADLINE_PRESET:
        query = apply_active_no_deadline_preset(query)
    elif preset is not None:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {preset}")
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
            is_active=bool(j.get("is_active")),
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
        .select(
            "apply_url, apply_email, contact_phone, closing_date, review_reason"
        )
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
        merged.get("contact_phone"),
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


@router.post("/review-jobs/deep-enrich-tick", response_model=DeepEnrichTickResponse)
async def admin_review_jobs_deep_enrich_tick(
    limit: int = Query(10, ge=1, le=50, description="Jobs to process sequentially"),
    dry_run: bool = Query(
        False,
        description="When true, log would-fetch URLs without LLM or DB writes",
    ),
    include_review_queue: bool = Query(
        True,
        description="Include is_review_required jobs even when inactive",
    ),
    supabase=Depends(get_supabase),
):
    """Run deep-enrich on review-queue candidates one job at a time.

    Returns per-job outcomes with success/failure reasons. Use after
    ``GET /admin/review-jobs/overview`` to drain backlog; pair with
    ``POST /admin/review-jobs/bulk-dismiss-safe`` for hidden junk rows.
    """
    tick = await run_deep_enrich_tick(
        supabase,
        limit=limit,
        dry_run=dry_run,
        include_review_queue=include_review_queue,
    )
    return DeepEnrichTickResponse(**tick.as_response_dict())
