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


def resolve_paid_tier_from_amount_ngwee(
    amount_ngwee: int,
    tier_prices: dict[str, int],
    *,
    promotion_applied_until: Any = None,
    now: datetime | None = None,
) -> tuple[str, bool]:
    """Map a paid amount to a tier. Returns (tier, inexact_match).

    Exact list-price matches win. During an active promo window, promo checkout
    amounts are matched before the legacy \"highest tier <= amount\" fallback so
    K125 promo (professional) is not assigned starter.
    """
    paid_tiers = {
        price: tier for tier, price in tier_prices.items() if tier != "free"
    }

    # Promo checkout amounts can equal another tier's list price (e.g. K125
    # is starter list price and professional promo price). Prefer promo match
    # while the user's promotion window is active.
    if promotion_active(promotion_applied_until, now=now):
        promo_matches = [
            tier
            for tier, list_price in tier_prices.items()
            if tier != "free"
            and effective_checkout_price_ngwee(
                list_price, promotion_applied_until, now=now
            )
            == amount_ngwee
        ]
        if len(promo_matches) == 1:
            return promo_matches[0], False
        if len(promo_matches) > 1:
            promo_matches.sort(
                key=lambda t: tier_prices.get(t, 0), reverse=True
            )
            return promo_matches[0], True

    exact = paid_tiers.get(amount_ngwee)
    if exact is not None:
        return exact, False

    sorted_paid = sorted(paid_tiers.items())
    fallback = next(
        (tier for price, tier in reversed(sorted_paid) if price <= amount_ngwee),
        "starter",
    )
    return fallback, True


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
