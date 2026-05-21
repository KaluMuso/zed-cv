"""Job listing activation and review-queue rules (Track 4e)."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel


class ReviewState(BaseModel):
    is_active: bool = True
    is_review_required: bool = False
    review_reason: Optional[str] = None
    admin_review_reason: Optional[str] = None


def _has_apply_path(apply_url: str | None, apply_email: str | None) -> bool:
    return bool(
        (apply_url and str(apply_url).strip())
        or (apply_email and str(apply_email).strip())
    )


def compute_review_state(
    *,
    apply_url: str | None,
    apply_email: str | None,
    closing_date: date | str | None,
    application_instructions: str | None = None,
    instructions_have_contact: bool = False,
) -> ReviewState:
    """Apply Track 4e visibility rules for ingest and admin promote."""
    has_apply = _has_apply_path(apply_url, apply_email) or instructions_have_contact
    has_deadline = closing_date is not None and str(closing_date).strip() != ""

    reasons: list[str] = []
    if not has_apply:
        reasons.append("no_apply_path")
    if not has_deadline:
        reasons.append("no_deadline")

    if not reasons:
        return ReviewState()

    review_reason = "both" if len(reasons) == 2 else reasons[0]
    legacy = {
        "no_apply_path": "missing_apply_link,missing_contact",
        "no_deadline": "missing_deadline",
        "both": "missing_apply_link,missing_contact,missing_deadline",
    }[review_reason]

    is_active = has_apply
    return ReviewState(
        is_active=is_active,
        is_review_required=True,
        review_reason=review_reason,
        admin_review_reason=legacy,
    )


def apply_review_state_to_row(row: dict[str, Any], state: ReviewState) -> dict[str, Any]:
    """Merge ReviewState into a jobs insert/update dict."""
    row["is_active"] = state.is_active
    row["is_review_required"] = state.is_review_required
    row["review_reason"] = state.review_reason
    row["admin_review_reason"] = state.admin_review_reason
    return row


def can_publish_after_admin_edit(
    apply_url: str | None,
    apply_email: str | None,
    closing_date: date | str | None,
) -> bool:
    """True when admin filled enough to clear review and go live."""
    return _has_apply_path(apply_url, apply_email) and closing_date is not None
