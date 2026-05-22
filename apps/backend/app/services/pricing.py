"""Checkout pricing with first-two-months promotion."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client


def _parse_promotion_until(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def promotion_active(
    promotion_applied_until: Any,
    *,
    now: datetime | None = None,
) -> bool:
    """True when the user is still within the first-two-months 50% window."""
    until = _parse_promotion_until(promotion_applied_until)
    if until is None:
        return False
    current = now or datetime.now(timezone.utc)
    return current < until


def effective_checkout_price_ngwee(
    list_price_ngwee: int,
    promotion_applied_until: Any,
    *,
    now: datetime | None = None,
) -> int:
    """Half list price during promotion; free tier stays 0."""
    if list_price_ngwee <= 0:
        return 0
    if promotion_active(promotion_applied_until, now=now):
        return list_price_ngwee // 2
    return list_price_ngwee


async def load_user_promotion_until(
    supabase: Client, user_id: str
) -> datetime | None:
    result = (
        supabase.table("users")
        .select("promotion_applied_until")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return _parse_promotion_until(result.data[0].get("promotion_applied_until"))
