"""User-facing job visibility (open / recently_closed / archived)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Literal

VisibilityStatus = Literal["open", "recently_closed", "archived"]

GRACE_DAYS = 3
FEED_STATUSES: frozenset[str] = frozenset({"open", "recently_closed"})


def compute_visibility_status(
    *,
    is_active: bool | None,
    closing_date: date | None,
    today: date | None = None,
) -> VisibilityStatus:
    """Mirror jobs_user_facing.visibility_status (migration 095)."""
    current = today or date.today()
    active = is_active is not False
    if active and (closing_date is None or closing_date >= current):
        return "open"
    if (
        closing_date is not None
        and closing_date < current
        and closing_date >= current - timedelta(days=GRACE_DAYS)
    ):
        return "recently_closed"
    return "archived"


def visibility_from_row(row: dict[str, Any], *, today: date | None = None) -> VisibilityStatus:
    raw = row.get("visibility_status")
    if raw in ("open", "recently_closed", "archived"):
        return raw  # type: ignore[return-value]
    closing = row.get("closing_date")
    parsed: date | None
    if closing is None:
        parsed = None
    elif isinstance(closing, date):
        parsed = closing
    else:
        try:
            parsed = date.fromisoformat(str(closing)[:10])
        except ValueError:
            parsed = None
    return compute_visibility_status(
        is_active=row.get("is_active"),
        closing_date=parsed,
        today=today,
    )


def include_in_default_feed(row: dict[str, Any], *, include_archived: bool) -> bool:
    if include_archived:
        return True
    return visibility_from_row(row) in FEED_STATUSES
