"""Bwana FAQ intents — tiers and matching weights."""
import pytest

from app.services.bwana_faq import (
    is_contact_admin_request,
    is_unsatisfied_request,
    match_faq,
    match_faq_from_db,
)
from app.services.matching_weights_copy import MATCH_WEIGHTS
from app.services.tier_config import TierPricingSnapshot, clear_tier_config_cache
from tests.test_tier_config_admin import _TierConfigQuery, _tier_config_rows


def test_algorithm_faq_uses_50_20_15_10_5():
    match = match_faq("how does matching work?")
    assert match is not None
    assert match.intent_id == "algorithm"
    assert "50%" in match.response
    assert "20%" in match.response
    assert "15%" in match.response
    assert "10%" in match.response
    assert "5%" in match.response


def test_starter_tier_no_tailored_cv_claim():
    match = match_faq("tell me about starter plan")
    assert match is not None
    assert match.intent_id == "starter_tier"
    lower = match.response.lower()
    assert "professional" in lower
    assert "tailored cvs start on professional" in lower


def test_pricing_faq_uses_tier_config_snapshot():
    custom = TierPricingSnapshot(
        prices={
            "free": 0,
            "starter": 15000,
            "professional": 30000,
            "super_standard": 60000,
        },
        limits={"free": 5, "starter": 40, "professional": 100, "super_standard": 99999},
    )
    match = match_faq("how much do plans cost?", pricing=custom)
    assert match is not None
    assert match.intent_id == "pricing"
    assert "K150" in match.response
    assert "40 matches/mo" in match.response
    assert "K600" in match.response


@pytest.mark.asyncio
async def test_match_faq_from_db_reads_tier_config(fake_supabase):
    clear_tier_config_cache()
    rows = _tier_config_rows()
    fake_supabase.set_table("tier_config", _TierConfigQuery(data=rows))
    match = await match_faq_from_db("what's the price?", fake_supabase)
    assert match is not None
    assert match.intent_id == "pricing"
    free = next(r for r in rows if r["tier"] == "free")
    starter = next(r for r in rows if r["tier"] == "starter")
    assert f"K{starter['price_ngwee'] // 100}" in match.response
    assert f"{free['matches_limit']} matches/mo" in match.response


def test_matching_weights_constants():
    assert MATCH_WEIGHTS["semantic"] == 50
    assert sum(MATCH_WEIGHTS.values()) == 100


def test_contact_admin_detection():
    assert is_contact_admin_request("what's your support email?")
    assert is_unsatisfied_request("I'm not satisfied with this")
