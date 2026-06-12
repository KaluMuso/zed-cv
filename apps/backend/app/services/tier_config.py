"""Load tier pricing and match quotas from tier_config with code fallbacks."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from supabase import Client

from app.schemas.subscription import TIER_LIMITS, TIER_PRICES
from app.schemas.tier_config import UNLIMITED_MATCHES

logger = logging.getLogger(__name__)

_TIER_ORDER = ("free", "starter", "professional", "super_standard")
_cache_rows: list[dict[str, Any]] | None = None


def clear_tier_config_cache() -> None:
    """Invalidate in-process cache after superadmin updates."""
    global _cache_rows
    _cache_rows = None


def _default_rows() -> list[dict[str, Any]]:
    names = {
        "free": "Free",
        "starter": "Starter",
        "professional": "Professional",
        "super_standard": "Super Standard",
    }
    return [
        {
            "tier": tier,
            "display_name": names[tier],
            "price_ngwee": TIER_PRICES[tier],
            "matches_limit": TIER_LIMITS[tier],
            "sort_order": idx,
            "marketing_blurb": None,
            "is_highlighted": False,
            "updated_at": None,
        }
        for idx, tier in enumerate(_TIER_ORDER)
    ]


async def fetch_tier_config_rows(supabase: Client, *, force: bool = False) -> list[dict[str, Any]]:
    """Return tier rows from DB, falling back to schema defaults."""
    global _cache_rows
    if _cache_rows is not None and not force:
        return _cache_rows

    try:
        result = (
            supabase.table("tier_config")
            .select("tier, display_name, price_ngwee, matches_limit, sort_order, updated_at, billing_period_days, marketing_blurb, is_highlighted")
            .order("sort_order")
            .execute()
        )
        rows = result.data or []
    except Exception as exc:
        logger.warning("tier_config load failed, using defaults: %s", exc)
        rows = []

    if not rows:
        _cache_rows = _default_rows()
        return _cache_rows

    _cache_rows = rows
    return _cache_rows


async def get_tier_limits(supabase: Client) -> dict[str, int]:
    rows = await fetch_tier_config_rows(supabase)
    # Default to 30-day limits for legacy reverse mapping
    return {row["tier"]: int(row["matches_limit"]) for row in rows if row.get("billing_period_days", 30) == 30}


async def get_tier_prices(supabase: Client) -> dict[str, int]:
    rows = await fetch_tier_config_rows(supabase)
    # Default reverse-mapping dictionary is based on monthly (30-day) prices
    return {row["tier"]: int(row["price_ngwee"]) for row in rows if row.get("billing_period_days", 30) == 30}


@dataclass(frozen=True)
class TierPricingSnapshot:
    """Resolved tier prices and match quotas (DB or schema fallback)."""

    prices: dict[str, int]
    limits: dict[str, int]

    @classmethod
    def from_rows(cls, rows: list[dict[str, Any]]) -> TierPricingSnapshot:
        prices = {row["tier"]: int(row["price_ngwee"]) for row in rows if row.get("billing_period_days", 30) == 30}
        limits = {row["tier"]: int(row["matches_limit"]) for row in rows if row.get("billing_period_days", 30) == 30}
        return cls(prices=prices, limits=limits)

    @classmethod
    def from_defaults(cls) -> TierPricingSnapshot:
        return cls.from_rows(_default_rows())

    def price(self, tier: str) -> int:
        return self.prices.get(tier, TIER_PRICES.get(tier, 0))

    def limit(self, tier: str) -> int:
        return self.limits.get(tier, TIER_LIMITS.get(tier, 0))

    def price_label(self, tier: str) -> str:
        return price_to_kwacha_label(self.price(tier))

    def matches_label(self, tier: str) -> str:
        return matches_limit_label(self.limit(tier))

    def pricing_trigger_keywords(self) -> tuple[str, ...]:
        """User phrases that suggest a pricing question (includes live kwacha labels)."""
        base = ("price", "pricing", "cost", "how much", " tier", "plan")
        extras = tuple(
            self.price_label(t).lower()
            for t in _TIER_ORDER
            if self.price(t) > 0
        )
        return base + extras


async def load_tier_pricing_snapshot(supabase: Client) -> TierPricingSnapshot:
    rows = await fetch_tier_config_rows(supabase)
    return TierPricingSnapshot.from_rows(rows)


def price_to_kwacha_label(price_ngwee: int) -> str:
    if price_ngwee <= 0:
        return "K0"
    kwacha = price_ngwee // 100
    return f"K{kwacha}"


def matches_limit_label(matches_limit: int) -> str:
    if matches_limit >= UNLIMITED_MATCHES:
        return "Unlimited"
    return str(matches_limit)


async def build_tier_display_names(supabase: Client) -> dict[str, str]:
    rows = await fetch_tier_config_rows(supabase)
    out: dict[str, str] = {}
    for row in rows:
        # Only use monthly rows for default mapping
        if row.get("billing_period_days", 30) != 30:
            continue
        tier = row["tier"]
        if tier == "free":
            out[tier] = f"{row['display_name']} ({price_to_kwacha_label(row['price_ngwee'])})"
        else:
            out[tier] = (
                f"{row['display_name']} ({price_to_kwacha_label(row['price_ngwee'])}/mo)"
            )
    return out


async def build_plan_info_by_tier(supabase: Client) -> dict[str, str]:
    rows = await fetch_tier_config_rows(supabase)
    out: dict[str, str] = {}
    for row in rows:
        # Only use monthly rows for default mapping
        if row.get("billing_period_days", 30) != 30:
            continue
        tier = row["tier"]
        limit = int(row["matches_limit"])
        limit_txt = (
            "Unlimited matches/month"
            if limit >= UNLIMITED_MATCHES
            else f"{limit} matches/month"
        )
        price = price_to_kwacha_label(int(row["price_ngwee"]))
        if tier == "free":
            out[tier] = f"{row['display_name']} - {limit_txt}"
        else:
            out[tier] = f"{row['display_name']} ({price}/mo) - {limit_txt}"
    return out
