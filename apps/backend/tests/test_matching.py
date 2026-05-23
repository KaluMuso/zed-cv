"""Smoke tests for matching routes."""
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import FakeSupabase, FakeSupabaseQuery


class _SingleQuery(FakeSupabaseQuery):
    """Mock that handles .single() properly."""

    def single(self):
        self._single = True
        return self

    def execute(self):
        result = MagicMock()
        if getattr(self, "_single", False) and self._data:
            result.data = (
                self._data[0] if isinstance(self._data, list) else self._data
            )
        else:
            result.data = self._data
        result.count = getattr(self, "_count", None)
        return result


class TestGetMatches:
    def test_get_matches_unauthenticated(self, client):
        """Matches endpoint requires auth."""
        resp = client.get("/api/v1/matches")
        assert resp.status_code in (401, 403)

    @patch(
        "app.api.v1.matches.check_match_quota",
        new_callable=AsyncMock,
        return_value=(True, 5),
    )
    def test_get_matches_empty(
        self, mock_quota, client, auth_headers, fake_supabase
    ):
        """Returns empty list when no matches exist."""
        fake_supabase.set_table("matches", FakeSupabaseQuery(data=[]))
        resp = client.get("/api/v1/matches", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["matches"] == []

    @patch(
        "app.api.v1.matches.check_match_quota",
        new_callable=AsyncMock,
        return_value=(True, 3),
    )
    def test_get_matches_with_results(
        self, mock_quota, client, auth_headers, fake_supabase
    ):
        """Returns formatted matches with job data."""
        fake_supabase.set_table(
            "matches",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "match-1",
                        "user_id": "test-user-id",
                        "score": 82.5,
                        "vector_score": 40.0,
                        "skill_score": 16.0,
                        "experience_score": 12.0,
                        "location_score": 10.0,
                        "recency_score": 4.5,
                        "bonus_score": 14.5,
                        "matched_skills": ["python", "fastapi"],
                        "missing_skills": ["kubernetes"],
                        "explanation": "Strong backend fit",
                        "created_at": "2025-01-01T00:00:00Z",
                        "jobs": {
                            "id": "job-1",
                            "title": "Backend Dev",
                            "company": "TechCo",
                            "location": "Lusaka",
                            "description": "Build APIs",
                            "source": "manual",
                            "posted_at": "2025-01-01T00:00:00Z",
                            "is_active": True,
                        },
                    }
                ]
            ),
        )
        resp = client.get("/api/v1/matches", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["matches"]) == 1
        assert body["matches"][0]["score"] == 82.5
        assert body["remaining_quota"] == 3
        assert body["matches"][0]["semantic_score"] == 40.0
        assert body["matches"][0]["skills_score"] == 16.0


class TestGetMatchesForUser:
    @patch(
        "app.api.v1.matches.check_match_quota",
        new_callable=AsyncMock,
        return_value=(True, 5),
    )
    @patch(
        "app.api.v1.matches.run_matching_for_user",
        new_callable=AsyncMock,
        return_value=[
            {
                "job_id": "job-1",
                "semantic_score": 40.0,
                "skills_score": 16.0,
                "experience_score": 12.0,
                "location_score": 10.0,
                "recency_score": 4.0,
                "score": 82.0,
                "matched_skills": ["python"],
                "missing_skills": [],
                "explanation": "Semantic 40/50, skills 16/20, experience 12/15, location 10/10, recency 4/5.",
            }
        ],
    )
    @patch(
        "app.api.v1.matches.fetch_jobs_by_ids",
        new_callable=AsyncMock,
        return_value={
            "job-1": {
                "id": "job-1",
                "title": "Backend Dev",
                "company": "TechCo",
                "location": "Lusaka",
                "description": "Build APIs",
                "source": "manual",
                "posted_at": "2025-01-01T00:00:00Z",
                "is_active": True,
            }
        },
    )
    def test_get_matches_for_user_live_rpc(
        self,
        mock_jobs,
        mock_rpc,
        mock_quota,
        client,
        auth_headers,
        fake_supabase,
    ):
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "test-user-id",
                        "phone": "+260971234567",
                        "role": "user",
                        "subscription_tier": "professional",
                        "matches_viewed_this_month": 0,
                        "billing_cycle_reset": "2099-06-01",
                    }
                ]
            ),
        )
        fake_supabase.set_table("matches", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table("user_preferences", FakeSupabaseQuery(data=[]))
        resp = client.get(
            "/api/v1/matches/test-user-id",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["matches"]) == 1
        match = body["matches"][0]
        assert match["score"] == 82.0
        assert match["semantic_score"] == 40.0
        assert match["skills_score"] == 16.0
        assert match["experience_score"] == 12.0
        assert match["location_score"] == 10.0
        assert match["recency_score"] == 4.0

    def test_get_matches_for_user_forbidden_other_user(
        self, client, auth_headers, fake_supabase
    ):
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "test-user-id",
                        "phone": "+260971234567",
                        "role": "user",
                        "subscription_tier": "free",
                        "matches_viewed_this_month": 0,
                        "billing_cycle_reset": "2099-06-01",
                    }
                ]
            ),
        )
        resp = client.get(
            "/api/v1/matches/other-user-id",
            headers=auth_headers,
        )
        assert resp.status_code == 403


class TestTriggerMatching:
    @patch(
        "app.api.v1.matches.check_match_quota",
        new_callable=AsyncMock,
        return_value=(False, 0),
    )
    def test_trigger_allows_refresh_when_credit_quota_full(
        self, mock_quota, client, auth_headers, fake_supabase
    ):
        """Refresh still runs; quota now gates credited rows, not insertion."""
        # /matches/trigger uses Depends(get_current_user), which looks up
        # the user in the `users` table. Tests must seed this table or
        # auth fails with 401 before the quota check runs.
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[{"id": "test-user-id", "phone": "+260971234567", "role": "user"}]
            ),
        )
        fake_supabase.set_table("cvs", FakeSupabaseQuery(data=[{"id": "cv-1"}]))
        resp = client.post("/api/v1/matches/trigger", headers=auth_headers)
        assert resp.status_code == 200

    @patch(
        "app.api.v1.matches.check_match_quota",
        new_callable=AsyncMock,
        return_value=(True, 5),
    )
    def test_trigger_no_cv(
        self, mock_quota, client, auth_headers, fake_supabase
    ):
        """Rejects matching when no CV uploaded."""
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[{"id": "test-user-id", "phone": "+260971234567", "role": "user"}]
            ),
        )
        fake_supabase.set_table("cvs", FakeSupabaseQuery(data=[]))
        resp = client.post("/api/v1/matches/trigger", headers=auth_headers)
        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────
# Regression-shape tests for slice 2D-1f (match_jobs_for_user 42804 fix).
#
# These use FakeSupabase and CANNOT detect a real PostgreSQL
#   42804: structure of query does not match function result type
# error — that requires applying migration 009 against a Supabase preview
# branch and calling SELECT * FROM match_jobs_for_user(...) for real.
# Treat the tests below as regression-shape coverage (call sites stay
# wired, the background task no longer swallows errors silently), not as
# integration coverage for the SQL function itself.
# ─────────────────────────────────────────────────────────────────────────
class TestMatchRpcRegression:
    def test_match_rpc_returns_without_type_error(self, fake_supabase):
        """run_matching_for_user wraps supabase.rpc('match_jobs_for_user', ...).execute()
        and returns a list. Shape-only check; does not validate Postgres types."""
        from app.services.matching import run_matching_for_user

        # Realistic-shape RPC result: one match row with the documented columns.
        fake_supabase.rpc = MagicMock(
            return_value=FakeSupabaseQuery(
                data=[
                    {
                        "job_id": "job-1",
                        "job_title": "Backend Dev",
                        "job_company": "TechCo",
                        "job_location": "Lusaka",
                        "vector_score": 78.0,
                        "skill_score": 85.0,
                        "bonus_score": 70.0,
                        "final_score": 80.0,
                        "matched_skills": ["python", "fastapi"],
                        "missing_skills": ["kubernetes"],
                    }
                ]
            )
        )
        result = asyncio.run(run_matching_for_user("test-user-id", fake_supabase))
        assert isinstance(result, list)
        assert result and result[0]["final_score"] == 80.0
        # Confirm the route-level caller used the RPC name we expect.
        fake_supabase.rpc.assert_called_once()
        assert fake_supabase.rpc.call_args.args[0] == "match_jobs_for_user"

    def test_run_matching_task_logs_rpc_errors(self, fake_supabase, caplog):
        """_run_matching_task must log RPC failures at ERROR (not silently
        swallow them) AND log digest-email failures at WARNING. The silent
        except-pass here is what hid the 42804 bug in prod for weeks."""
        from app.api.v1 import matches as matches_module

        # 1. RPC failure path: assert ERROR-level log, no propagation.
        with patch.object(
            matches_module, "run_matching_for_user", new=AsyncMock(side_effect=RuntimeError("simulated 42804")),
        ):
            with caplog.at_level(logging.ERROR, logger=matches_module.__name__):
                asyncio.run(
                    matches_module._run_matching_task("test-user-id", "cv-1", fake_supabase)
                )
        assert any(
            r.levelno == logging.ERROR and "matching task failed" in r.getMessage()
            for r in caplog.records
        ), "expected ERROR log when matching RPC raises"

        # 2. Digest-email failure path: assert WARNING-level log, task still completes.
        caplog.clear()
        # _SingleQuery (defined above) unwraps .single() to a dict so the
        # task's `sub.data["matches_used"]` access works.
        fake_supabase.set_table(
            "subscriptions",
            _SingleQuery(data=[{"tier": "starter", "status": "active"}]),
        )
        fake_supabase.set_table(
            "matches",
            FakeSupabaseQuery(data=[{"score": 80, "jobs": {"title": "X", "company": "Y"}}]),
        )
        with patch.object(
            matches_module, "run_matching_for_user", new=AsyncMock(return_value=[{
                "job_id": "job-1", "final_score": 80.0,
                "vector_score": 78.0, "skill_score": 85.0, "bonus_score": 70.0,
                "matched_skills": [], "missing_skills": [],
            }]),
        ), patch.object(
            matches_module, "store_matches", new=AsyncMock(return_value=1),
        ), patch.object(
            matches_module, "send_match_digest_email", new=AsyncMock(side_effect=RuntimeError("smtp boom")),
        ):
            with caplog.at_level(logging.WARNING, logger=matches_module.__name__):
                asyncio.run(
                    matches_module._run_matching_task("test-user-id", "cv-1", fake_supabase)
                )
        assert any(
            r.levelno == logging.WARNING and "digest email failed" in r.getMessage()
            for r in caplog.records
        ), "expected WARNING log when digest email raises"
