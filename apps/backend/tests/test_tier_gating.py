"""Unit tests for subscription tier gating (canonical tier keys)."""
from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.core.tier_gating import (
    FEATURE_COVER_LETTER,
    FEATURE_JOB_MATCHES,
    normalize_tier,
    verify_tier_access,
)
from tests.conftest import FakeSupabaseQuery


def _seed_gating_user(fake_supabase, *, tier: str, viewed: int = 0, role: str = "user"):
    reset = (date.today() + timedelta(days=28)).isoformat()
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "test-user-id",
                    "phone": "+260971234567",
                    "role": role,
                    "subscription_tier": tier,
                    "matches_viewed_this_month": viewed,
                    "billing_cycle_reset": reset,
                }
            ]
        ),
    )


class TestNormalizeTier:
    def test_unknown_falls_back_to_free(self):
        assert normalize_tier("legacy_bwino") == "free"

    def test_canonical_tiers_unchanged(self):
        assert normalize_tier("starter") == "starter"
        assert normalize_tier("super_standard") == "super_standard"


class TestVerifyTierAccessCoverLetter:
    @pytest.mark.asyncio
    async def test_free_blocked(self, fake_supabase):
        _seed_gating_user(fake_supabase, tier="free")
        with pytest.raises(HTTPException) as exc:
            await verify_tier_access(
                FEATURE_COVER_LETTER, "test-user-id", fake_supabase
            )
        assert exc.value.status_code == 403
        assert "Professional" in exc.value.detail

    @pytest.mark.asyncio
    async def test_starter_blocked(self, fake_supabase):
        _seed_gating_user(fake_supabase, tier="starter")
        with pytest.raises(HTTPException) as exc:
            await verify_tier_access(
                FEATURE_COVER_LETTER, "test-user-id", fake_supabase
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_professional_allowed(self, fake_supabase):
        _seed_gating_user(fake_supabase, tier="professional")
        tier = await verify_tier_access(
            FEATURE_COVER_LETTER, "test-user-id", fake_supabase
        )
        assert tier == "professional"

    @pytest.mark.asyncio
    async def test_super_standard_allowed(self, fake_supabase):
        _seed_gating_user(fake_supabase, tier="super_standard")
        tier = await verify_tier_access(
            FEATURE_COVER_LETTER, "test-user-id", fake_supabase
        )
        assert tier == "super_standard"


class TestVerifyTierAccessJobMatches:
    @pytest.mark.asyncio
    async def test_free_at_limit_blocked(self, fake_supabase):
        _seed_gating_user(fake_supabase, tier="free", viewed=10)
        with pytest.raises(HTTPException) as exc:
            await verify_tier_access(
                FEATURE_JOB_MATCHES, "test-user-id", fake_supabase
            )
        assert exc.value.status_code == 403
        assert "limit" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_free_increment_over_limit_blocked(self, fake_supabase):
        _seed_gating_user(fake_supabase, tier="free", viewed=9)
        with pytest.raises(HTTPException) as exc:
            await verify_tier_access(
                FEATURE_JOB_MATCHES,
                "test-user-id",
                fake_supabase,
                increment_match_views=2,
            )
        assert exc.value.status_code == 403
