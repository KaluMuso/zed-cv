"""Tests for nightly batch matching and cached refresh."""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services import batch_matching
from tests.conftest import FakeSupabase, FakeSupabaseQuery

INGEST_HEADERS = {"INGEST_API_KEY": "test-ingest-key"}


class TestRunNightlyBatchMatch:
    def test_batch_match_processes_all_users(self):
        supabase = MagicMock()
        user_ids = [f"user-{i}" for i in range(3)]
        with (
            patch.object(
                batch_matching,
                "_fetch_active_user_ids",
                side_effect=[user_ids, []],
            ),
            patch.object(
                batch_matching,
                "_primary_cv_id",
                new=AsyncMock(return_value="cv-1"),
            ),
            patch.object(
                batch_matching,
                "run_batch_match_for_user",
                new=AsyncMock(return_value=2),
            ) as mock_run,
            patch.object(
                batch_matching,
                "create_batch_run",
                new=AsyncMock(return_value="batch-1"),
            ),
            patch.object(
                batch_matching,
                "finalize_batch_run",
                new=AsyncMock(),
            ),
            patch.object(
                batch_matching,
                "prune_old_batch_matches",
                new=AsyncMock(return_value=0),
            ),
        ):
            result = asyncio.run(
                batch_matching.run_nightly_batch_match(supabase, "batch-1")
            )
        assert result["users_processed"] == 3
        assert result["matches_created"] == 6
        assert mock_run.call_count == 3

    def test_batch_match_chunks_handle_failures_independently(self):
        supabase = MagicMock()
        user_ids = ["ok-user", "bad-user", "ok-user-2"]

        async def _run(user_id, cv_id, batch_id, batch_at, sb):
            if user_id == "bad-user":
                raise RuntimeError("rpc failed")
            return 1

        with (
            patch.object(
                batch_matching,
                "_fetch_active_user_ids",
                side_effect=[user_ids, []],
            ),
            patch.object(
                batch_matching,
                "_primary_cv_id",
                new=AsyncMock(return_value="cv-1"),
            ),
            patch.object(
                batch_matching,
                "run_batch_match_for_user",
                side_effect=_run,
            ),
            patch.object(
                batch_matching,
                "finalize_batch_run",
                new=AsyncMock(),
            ),
            patch.object(
                batch_matching,
                "prune_old_batch_matches",
                new=AsyncMock(return_value=0),
            ),
        ):
            result = asyncio.run(
                batch_matching.run_nightly_batch_match(supabase, "batch-2")
            )
        assert result["users_processed"] == 2
        assert result["error_count"] == 1


class TestRefreshEndpoint:
    @patch(
        "app.api.v1.matches.check_match_quota",
        new_callable=AsyncMock,
        return_value=(True, 5),
    )
    @patch(
        "app.api.v1.matches.get_user_tier_limit",
        new_callable=AsyncMock,
        return_value=("starter", 50, True),
    )
    @patch(
        "app.api.v1.matches.get_credited_match_count",
        new_callable=AsyncMock,
        return_value=0,
    )
    @patch(
        "app.api.v1.matches.get_latest_batch_for_user",
        new_callable=AsyncMock,
        return_value=("batch-x", "2026-05-22T10:00:00+00:00"),
    )
    @patch(
        "app.api.v1.matches.fetch_cached_batch_matches",
        new_callable=AsyncMock,
        return_value=[
            {
                "id": "m1",
                "score": 80.0,
                "vector_score": 40.0,
                "skill_score": 16.0,
                "experience_score": 12.0,
                "location_score": 8.0,
                "recency_score": 4.0,
                "bonus_score": 12.0,
                "matched_skills": [],
                "missing_skills": [],
                "explanation": "fit",
                "created_at": "2026-05-22T10:00:00Z",
                "jobs": {
                    "id": "job-1",
                    "title": "Dev",
                    "company": "Co",
                    "location": "Lusaka",
                    "description": "x",
                    "source": "manual",
                    "posted_at": "2026-05-01T00:00:00Z",
                    "is_active": True,
                },
            }
        ],
    )
    @patch(
        "app.api.v1.matches.run_on_demand_match_for_user",
        new_callable=AsyncMock,
    )
    def test_refresh_returns_cached_matches_not_live_rpc(
        self,
        mock_on_demand,
        mock_fetch,
        mock_latest,
        mock_credited,
        mock_tier,
        mock_quota,
        client,
        auth_headers,
    ):
        resp = client.post("/api/v1/matches/refresh", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["from_cache"] is True
        assert body["last_batch_run_at"] is not None
        assert len(body["matches"]) == 1
        assert "matches_used" in body
        assert "matches_unlimited" in body
        assert body.get("refresh_computing") is False
        mock_on_demand.assert_not_called()
        mock_fetch.assert_called_once()

    @patch(
        "app.api.v1.matches.check_match_quota",
        new_callable=AsyncMock,
        return_value=(True, 5),
    )
    @patch(
        "app.api.v1.matches.get_user_tier_limit",
        new_callable=AsyncMock,
        return_value=("starter", 50, True),
    )
    @patch(
        "app.api.v1.matches.get_credited_match_count",
        new_callable=AsyncMock,
        return_value=0,
    )
    @patch(
        "app.api.v1.matches.get_latest_batch_for_user",
        new_callable=AsyncMock,
        side_effect=[(None, None), ("batch-new", "2026-05-23T08:00:00+00:00")],
    )
    @patch(
        "app.api.v1.matches.run_on_demand_match_for_user",
        new_callable=AsyncMock,
        return_value=("batch-new", 3),
    )
    @patch(
        "app.api.v1.matches.fetch_cached_batch_matches",
        new_callable=AsyncMock,
        return_value=[],
    )
    @patch(
        "app.api.v1.matches._primary_cv_id",
        new_callable=AsyncMock,
        return_value="cv-1",
    )
    def test_first_time_user_falls_back_to_live_rpc_then_cache(
        self,
        mock_cv,
        mock_fetch,
        mock_on_demand,
        mock_latest,
        mock_credited,
        mock_tier,
        mock_quota,
        client,
        auth_headers,
    ):
        resp = client.post("/api/v1/matches/refresh", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["from_cache"] is False
        assert body.get("message")
        mock_on_demand.assert_called_once()


class TestPruneOldBatches:
    def test_old_batches_pruned_after_7_days(self):
        deleted_rows = [{"id": "old-1"}, {"id": "old-2"}]
        query = FakeSupabaseQuery(data=deleted_rows)
        supabase = FakeSupabase()
        supabase.set_table("matches", query)
        pruned = asyncio.run(batch_matching.prune_old_batch_matches(supabase, days=7))
        assert pruned == 2


class TestBatchMatchAdminEndpoint:
    @patch(
        "app.api.v1.admin_ingest.create_batch_run",
        new_callable=AsyncMock,
        return_value="batch-admin",
    )
    @patch("app.api.v1.admin_ingest._run_batch_match_task", new_callable=AsyncMock)
    def test_batch_match_endpoint_returns_202(
        self, mock_task, mock_create, client: TestClient
    ):
        resp = client.post("/api/v1/admin/batch-match", headers=INGEST_HEADERS)
        assert resp.status_code == 202
        assert resp.json()["batch_run_id"] == "batch-admin"

    def test_batch_match_endpoint_rejects_bad_key(self, client: TestClient):
        resp = client.post(
            "/api/v1/admin/batch-match",
            headers={"INGEST_API_KEY": "wrong"},
        )
        assert resp.status_code == 401


class TestMigration061:
    def test_migration_defines_batch_columns(self):
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        sql = (repo_root / "infra/supabase/migrations/061_match_batches.sql").read_text()
        assert "batch_run_id" in sql
        assert "match_batch_runs" in sql
        assert "idx_matches_user_batch" in sql
