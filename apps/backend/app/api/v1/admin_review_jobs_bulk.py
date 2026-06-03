"""Bulk admin actions for the Track 4e job review queue."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import get_supabase, require_admin
from app.services.review_queue_cleanup import (
    AUTO_DISMISS_REVIEW_REASONS,
    JUNK_DEACTIVATION_MARKERS,
    build_hidden_inactive_dismiss_patch,
    build_review_dismiss_patch,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


class ReviewJobsBulkRequest(BaseModel):
    job_ids: list[str] = Field(..., min_length=1, max_length=100)


class ReviewQueueAutoDismissRequest(BaseModel):
    dry_run: bool = False
    limit: int = Field(2000, ge=1, le=5000)


class ReviewQueueAutoDismissResponse(BaseModel):
    dry_run: bool
    eligible: int
    dismissed: int


class ReviewQueueBulkDismissResponse(BaseModel):
    dry_run: bool
    eligible: int
    dismissed: int
    category: str


class ReviewQueueBulkDismissAllResponse(BaseModel):
    dry_run: bool
    hidden_eligible: int
    hidden_dismissed: int
    expired_eligible: int
    expired_dismissed: int
    junk_eligible: int
    junk_dismissed: int


@router.post(
    "/review-jobs/bulk-auto-dismiss-hidden",
    response_model=ReviewQueueAutoDismissResponse,
)
async def bulk_auto_dismiss_hidden(
    body: ReviewQueueAutoDismissRequest,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    """Clear review flags for jobs already inactive with no apply path (idempotent)."""
    count_query = (
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .eq("is_active", False)
        .in_("review_reason", list(AUTO_DISMISS_REVIEW_REASONS))
    )
    eligible = count_query.execute().count or 0

    if body.dry_run or eligible == 0:
        return ReviewQueueAutoDismissResponse(
            dry_run=body.dry_run,
            eligible=eligible,
            dismissed=0,
        )

    patch = build_hidden_inactive_dismiss_patch()
    patch["admin_reviewed_by_user_id"] = current_user["id"]

    result = (
        supabase.table("jobs")
        .update(patch)
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .eq("is_active", False)
        .in_("review_reason", list(AUTO_DISMISS_REVIEW_REASONS))
        .execute()
    )
    dismissed = len(result.data or []) if result.data else eligible
    logger.info(
        "review_queue_auto_dismiss_hidden admin=%s eligible=%s dismissed=%s",
        current_user["id"],
        eligible,
        dismissed,
    )
    return ReviewQueueAutoDismissResponse(
        dry_run=False,
        eligible=eligible,
        dismissed=dismissed,
    )


@router.post(
    "/review-jobs/bulk-dismiss-expired",
    response_model=ReviewQueueBulkDismissResponse,
)
async def bulk_dismiss_expired_review(
    body: ReviewQueueAutoDismissRequest,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    """Clear review flags on jobs past closing_date."""
    today = date.today().isoformat()
    count_query = (
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .not_.is_("closing_date", "null")
        .lt("closing_date", today)
    )
    eligible = count_query.execute().count or 0
    if body.dry_run or eligible == 0:
        return ReviewQueueBulkDismissResponse(
            dry_run=body.dry_run,
            eligible=eligible,
            dismissed=0,
            category="expired",
        )

    patch = build_review_dismiss_patch(review_reason="auto_dismissed_expired")
    patch["admin_reviewed_by_user_id"] = current_user["id"]
    result = (
        supabase.table("jobs")
        .update(patch)
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .not_.is_("closing_date", "null")
        .lt("closing_date", today)
        .execute()
    )
    dismissed = len(result.data or []) if result.data else eligible
    logger.info(
        "review_queue_dismiss_expired admin=%s eligible=%s dismissed=%s",
        current_user["id"],
        eligible,
        dismissed,
    )
    return ReviewQueueBulkDismissResponse(
        dry_run=False,
        eligible=eligible,
        dismissed=dismissed,
        category="expired",
    )


@router.post(
    "/review-jobs/bulk-dismiss-junk",
    response_model=ReviewQueueBulkDismissResponse,
)
async def bulk_dismiss_junk_review(
    body: ReviewQueueAutoDismissRequest,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    """Clear review on ingest-hidden junk (thin description, bad source URL)."""
    junk_filters = ",".join(
        f"deactivation_reason.ilike.%{marker}%" for marker in JUNK_DEACTIVATION_MARKERS
    )
    count_query = (
        supabase.table("jobs")
        .select("id", count="exact")
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .eq("is_active", False)
        .or_(junk_filters)
    )
    eligible = count_query.execute().count or 0
    if body.dry_run or eligible == 0:
        return ReviewQueueBulkDismissResponse(
            dry_run=body.dry_run,
            eligible=eligible,
            dismissed=0,
            category="junk",
        )

    patch = build_review_dismiss_patch(review_reason="auto_dismissed_junk")
    patch["admin_reviewed_by_user_id"] = current_user["id"]
    result = (
        supabase.table("jobs")
        .update(patch)
        .eq("is_review_required", True)
        .is_("admin_reviewed_at", "null")
        .eq("is_active", False)
        .or_(junk_filters)
        .execute()
    )
    dismissed = len(result.data or []) if result.data else eligible
    logger.info(
        "review_queue_dismiss_junk admin=%s eligible=%s dismissed=%s",
        current_user["id"],
        eligible,
        dismissed,
    )
    return ReviewQueueBulkDismissResponse(
        dry_run=False,
        eligible=eligible,
        dismissed=dismissed,
        category="junk",
    )


@router.post(
    "/review-jobs/bulk-dismiss-safe",
    response_model=ReviewQueueBulkDismissAllResponse,
)
async def bulk_dismiss_safe_review(
    body: ReviewQueueAutoDismissRequest,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    """Run hidden, expired, and junk bulk dismisses (idempotent, dry_run supported)."""
    hidden = await bulk_auto_dismiss_hidden(body, current_user, supabase)
    expired = await bulk_dismiss_expired_review(body, current_user, supabase)
    junk = await bulk_dismiss_junk_review(body, current_user, supabase)
    return ReviewQueueBulkDismissAllResponse(
        dry_run=body.dry_run,
        hidden_eligible=hidden.eligible,
        hidden_dismissed=hidden.dismissed,
        expired_eligible=expired.eligible,
        expired_dismissed=expired.dismissed,
        junk_eligible=junk.eligible,
        junk_dismissed=junk.dismissed,
    )


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
