"""First-two-months 50% checkout pricing."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.pricing import (
    effective_checkout_price_ngwee,
    promotion_active,
    resolve_paid_tier_from_amount_ngwee,
)

TIER_PRICES = {
    "free": 0,
    "starter": 12500,
    "professional": 25000,
    "super_standard": 50000,
}


def test_promotion_active_within_window():
    until = datetime.now(timezone.utc) + timedelta(days=30)
    assert promotion_active(until) is True


def test_promotion_inactive_after_window():
    until = datetime.now(timezone.utc) - timedelta(days=1)
    assert promotion_active(until) is False


def test_effective_price_halves_during_promotion():
    until = datetime.now(timezone.utc) + timedelta(days=10)
    assert effective_checkout_price_ngwee(12500, until) == 6250
    assert effective_checkout_price_ngwee(25000, until) == 12500
    assert effective_checkout_price_ngwee(50000, until) == 25000


def test_effective_price_list_after_promotion():
    until = datetime.now(timezone.utc) - timedelta(hours=1)
    assert effective_checkout_price_ngwee(12500, until) == 12500


def test_free_tier_stays_zero():
    until = datetime.now(timezone.utc) + timedelta(days=30)
    assert effective_checkout_price_ngwee(0, until) == 0


def test_resolve_tier_promo_professional_not_starter():
    """K125 promo checkout must not map to starter (list price collision)."""
    until = datetime.now(timezone.utc) + timedelta(days=10)
    tier, inexact = resolve_paid_tier_from_amount_ngwee(
        12500,
        TIER_PRICES,
        promotion_applied_until=until,
    )
    assert tier == "professional"
    assert inexact is False


def test_resolve_tier_list_price_starter_without_promo():
    until = datetime.now(timezone.utc) - timedelta(days=1)
    tier, inexact = resolve_paid_tier_from_amount_ngwee(
        12500,
        TIER_PRICES,
        promotion_applied_until=until,
    )
    assert tier == "starter"
    assert inexact is False


def test_tiers_endpoint_returns_checkout_price_for_promo_user(
    client, auth_headers, fake_supabase
):
    """Authenticated /tiers reflects 50% checkout while promotion_applied_until is future."""
    from tests.conftest import FakeSupabaseQuery

    promo_until = (datetime.now(timezone.utc) + timedelta(days=45)).isoformat()
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "test-user-id",
                    "phone": "+260971234567",
                    "role": "user",
                    "promotion_applied_until": promo_until,
                }
            ]
        ),
    )
    fake_supabase.set_table(
        "tier_config",
        FakeSupabaseQuery(
            data=[
                {
                    "tier": "free",
                    "display_name": "Free",
                    "price_ngwee": 0,
                    "matches_limit": 10,
                    "sort_order": 0,
                },
                {
                    "tier": "starter",
                    "display_name": "Starter",
                    "price_ngwee": 12500,
                    "matches_limit": 50,
                    "sort_order": 1,
                },
                {
                    "tier": "professional",
                    "display_name": "Professional",
                    "price_ngwee": 25000,
                    "matches_limit": 125,
                    "sort_order": 2,
                },
                {
                    "tier": "super_standard",
                    "display_name": "Super Standard",
                    "price_ngwee": 50000,
                    "matches_limit": 99999,
                    "sort_order": 3,
                },
            ]
        ),
    )

    from app.services import tier_config as tier_config_svc

    tier_config_svc.clear_tier_config_cache()

    resp = client.get("/api/v1/tiers", headers=auth_headers)
    assert resp.status_code == 200
    tiers = {t["tier"]: t for t in resp.json()["tiers"]}
    assert tiers["starter"]["checkout_price_ngwee"] == 6250
    assert tiers["starter"]["promotion_active"] is True
    assert tiers["free"].get("checkout_price_ngwee") is None
