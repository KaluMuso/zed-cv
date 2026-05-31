"""Match list / refresh quota fields and refresh_computing flag."""
import asyncio
from unittest.mock import AsyncMock, patch

from app.schemas.tier_config import UNLIMITED_MATCHES
from app.services.match_quota import build_match_quota_snapshot


class TestBuildMatchQuotaSnapshot:
    @patch(
        "app.services.match_quota.check_match_quota",
        new_callable=AsyncMock,
        return_value=(True, 36),
    )
    @patch(
        "app.services.match_quota.get_user_tier_limit",
        new_callable=AsyncMock,
        return_value=("starter", 50, True),
    )
    @patch(
        "app.services.match_quota.get_credited_match_count",
        new_callable=AsyncMock,
        return_value=14,
    )
    def test_starter_quota_fields(self, *_mocks):
        snap = asyncio.run(build_match_quota_snapshot("user-1", object()))
        assert snap["matches_used"] == 14
        assert snap["credited_count"] == 14
        assert snap["matches_limit"] == 50
        assert snap["matches_unlimited"] is False
        assert snap["remaining_quota"] == 36

    @patch(
        "app.services.match_quota.check_match_quota",
        new_callable=AsyncMock,
        return_value=(True, UNLIMITED_MATCHES - 14),
    )
    @patch(
        "app.services.match_quota.get_user_tier_limit",
        new_callable=AsyncMock,
        return_value=("super_standard", UNLIMITED_MATCHES, True),
    )
    @patch(
        "app.services.match_quota.get_credited_match_count",
        new_callable=AsyncMock,
        return_value=14,
    )
    def test_unlimited_tier_flag(self, *_mocks):
        snap = asyncio.run(build_match_quota_snapshot("user-1", object()))
        assert snap["matches_limit"] == UNLIMITED_MATCHES
        assert snap["matches_unlimited"] is True


class TestRefreshEndpointQuota:
    @patch(
        "app.api.v1.matches.build_match_quota_snapshot",
        new_callable=AsyncMock,
        return_value={
            "matches_used": 14,
            "credited_count": 14,
            "matches_limit": 50,
            "matches_unlimited": False,
            "remaining_quota": 36,
        },
    )
    @patch(
        "app.api.v1.matches.get_latest_batch_for_user",
        new_callable=AsyncMock,
        return_value=("batch-x", "2026-05-22T10:00:00+00:00"),
    )
    @patch(
        "app.api.v1.matches.fetch_cached_batch_matches",
        new_callable=AsyncMock,
        return_value=[],
    )
    @patch(
        "app.api.v1.matches.run_on_demand_match_for_user",
        new_callable=AsyncMock,
    )
    def test_refresh_includes_quota_fields(
        self,
        mock_on_demand,
        mock_fetch,
        mock_latest,
        mock_quota,
        client,
        auth_headers,
    ):
        resp = client.post("/api/v1/matches/refresh", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["matches_used"] == 14
        assert body["matches_limit"] == 50
        assert body["matches_unlimited"] is False
        assert body["refresh_computing"] is False
        mock_on_demand.assert_not_called()
