"""Batch dismiss review-queue rows that are already hidden from customers."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

# Review reasons safe to clear when the job is already inactive (no public path).
AUTO_DISMISS_REVIEW_REASONS: frozenset[str] = frozenset({"both", "no_apply_path"})

# Ingest auto-hide markers — human still sets quality_score; we only clear review flags.
JUNK_DEACTIVATION_MARKERS: frozenset[str] = frozenset({
    "thin_description",
    "missing_source_url",
    "aggregator_root_url",
})

DismissMode = Literal["hidden_inactive", "expired", "junk"]


def build_hidden_inactive_dismiss_patch(
    *,
    reviewed_at: datetime | None = None,
) -> dict[str, Any]:
    """Patch applied when clearing review flags on already-hidden jobs."""
    ts = reviewed_at or datetime.now(timezone.utc)
    iso = ts.isoformat()
    return {
        "is_review_required": False,
        "review_reason": "auto_dismissed_hidden",
        "admin_review_reason": None,
        "admin_reviewed_at": iso,
        "updated_at": iso,
    }


def _pending_review_row(row: dict[str, Any]) -> bool:
    return row.get("is_review_required") is True and row.get("admin_reviewed_at") is None


def matches_hidden_inactive_dismiss(row: dict[str, Any]) -> bool:
    """True when a job row is eligible for bulk auto-dismiss (hidden backlog)."""
    if not _pending_review_row(row):
        return False
    if row.get("is_active") is not False:
        return False
    reason = row.get("review_reason")
    return reason in AUTO_DISMISS_REVIEW_REASONS


def matches_expired_review_dismiss(row: dict[str, Any], *, today: date | None = None) -> bool:
    """Past closing_date — safe to clear review without publishing."""
    if not _pending_review_row(row):
        return False
    closing = row.get("closing_date")
    if not closing:
        return False
    ref = today or date.today()
    try:
        closing_date = date.fromisoformat(str(closing)[:10])
    except ValueError:
        return False
    return closing_date < ref


def matches_junk_review_dismiss(row: dict[str, Any]) -> bool:
    """Ingest-marked junk (thin description, bad URL) already hidden from /jobs."""
    if not _pending_review_row(row):
        return False
    if row.get("is_active") is not False:
        return False
    deactivation = str(row.get("deactivation_reason") or "")
    return any(marker in deactivation for marker in JUNK_DEACTIVATION_MARKERS)


def build_review_dismiss_patch(
    *,
    review_reason: str,
    reviewed_at: datetime | None = None,
) -> dict[str, Any]:
    """Shared patch for bulk review-queue clears (never mutates quality_score)."""
    patch = build_hidden_inactive_dismiss_patch(reviewed_at=reviewed_at)
    patch["review_reason"] = review_reason
    return patch
