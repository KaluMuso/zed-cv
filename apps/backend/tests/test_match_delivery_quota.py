"""Tier delivery quota: only credited matches appear in feeds."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.matching import (
    backfill_match_credits,
    fetch_delivered_match_rows,
    match_rpc_limit_for_user,
)
from tests.test_track4b import MemorySupabase


@pytest.mark.asyncio
async def test_match_rpc_limit_respects_remaining_quota():
    with (
        patch(
            "app.services.matching.check_match_quota",
            new_callable=AsyncMock,
            return_value=(True, 7),
        ),
        patch(
            "app.services.matching.get_user_tier_limit",
            new_callable=AsyncMock,
            return_value=("free", 7, True),
        ),
    ):
        limit = await match_rpc_limit_for_user("u1", object(), 50)
    assert limit == 7


@pytest.mark.asyncio
async def test_match_rpc_limit_zero_when_no_remaining():
    with (
        patch(
            "app.services.matching.check_match_quota",
            new_callable=AsyncMock,
            return_value=(False, 0),
        ),
        patch(
            "app.services.matching.get_user_tier_limit",
            new_callable=AsyncMock,
            return_value=("free", 3, True),
        ),
    ):
        limit = await match_rpc_limit_for_user("u1", object(), 50)
    assert limit == 0


@pytest.mark.asyncio
async def test_fetch_delivered_excludes_uncredited_rows():
    now = datetime.now(timezone.utc)
    supabase = MemorySupabase(
        {
            "matches": [
                {
                    "id": "m1",
                    "user_id": "u1",
                    "job_id": "j1",
                    "score": 90,
                    "status": "new",
                    "credited_at": now.isoformat(),
                    "jobs": {"id": "j1", "title": "A", "is_active": True},
                },
                {
                    "id": "m2",
                    "user_id": "u1",
                    "job_id": "j2",
                    "score": 85,
                    "status": "new",
                    "credited_at": None,
                    "jobs": {"id": "j2", "title": "B", "is_active": True},
                },
            ],
            "subscriptions": [{"user_id": "u1", "tier": "free", "status": "active"}],
        }
    )
    rows = await fetch_delivered_match_rows("u1", supabase, min_score=50, limit=50)
    job_ids = {r["job_id"] for r in rows}
    assert job_ids == {"j1"}


@pytest.mark.asyncio
async def test_backfill_credits_via_credit_matches_for_cycle():
    now = datetime.now(timezone.utc)
    supabase = MemorySupabase(
        {
            "matches": [
                {
                    "id": "m2",
                    "user_id": "u1",
                    "job_id": "high",
                    "score": 95,
                    "status": "new",
                    "credited_at": None,
                },
            ],
            "subscriptions": [],
            "users": [{"id": "u1", "subscription_tier": "free"}],
        }
    )
    with (
        patch(
            "app.services.matching.check_match_quota",
            new_callable=AsyncMock,
            return_value=(True, 1),
        ),
        patch(
            "app.services.matching.credit_matches_for_cycle",
            new_callable=AsyncMock,
            return_value=["high"],
        ) as mock_credit,
    ):
        credited = await backfill_match_credits("u1", supabase)
    assert credited == ["high"]
    mock_credit.assert_called_once()
