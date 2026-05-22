"""Pin canonical TIER_LIMITS and TIER_PRICES (zedapply.com/pricing)."""
from app.schemas.subscription import TIER_LIMITS, TIER_PRICES


def test_tier_limits_canonical_values():
    assert TIER_LIMITS == {
        "free": 10,
        "starter": 50,
        "professional": 125,
        "super_standard": 99999,
    }


def test_tier_prices_canonical_values():
    """Prices in ngwee — K125 / K250 / K500 on the public pricing page."""
    assert TIER_PRICES == {
        "free": 0,
        "starter": 12500,
        "professional": 25000,
        "super_standard": 50000,
    }


def test_tier_limits_covers_all_tiers():
    """Every tier in the SubscriptionTier enum must have a quota."""
    from app.schemas.subscription import SubscriptionTier

    for tier in SubscriptionTier:
        assert tier.value in TIER_LIMITS
