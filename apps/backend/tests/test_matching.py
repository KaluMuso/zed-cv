"""Smoke tests for matching routes."""
from unittest.mock import AsyncMock, MagicMock, patch
from tests.conftest import FakeSupabaseQuery


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
                        "vector_score": 78.0,
                        "skill_score": 85.0,
                        "bonus_score": 84.5,
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


class TestTriggerMatching:
    @patch(
        "app.api.v1.matches.check_match_quota",
        new_callable=AsyncMock,
        return_value=(False, 0),
    )
    def test_trigger_no_quota(
        self, mock_quota, client, auth_headers, fake_supabase
    ):
        """Rejects matching when quota is exhausted."""
        resp = client.post("/api/v1/matches/trigger", headers=auth_headers)
        assert resp.status_code == 403

    @patch(
        "app.api.v1.matches.check_match_quota",
        new_callable=AsyncMock,
        return_value=(True, 5),
    )
    def test_trigger_no_cv(
        self, mock_quota, client, auth_headers, fake_supabase
    ):
        """Rejects matching when no CV uploaded."""
        fake_supabase.set_table("cvs", FakeSupabaseQuery(data=[]))
        resp = client.post("/api/v1/matches/trigger", headers=auth_headers)
        assert resp.status_code == 422
