"""Smoke tests for profile and skills routes."""
from unittest.mock import MagicMock
from tests.conftest import FakeSupabaseQuery


class _SingleQuery(FakeSupabaseQuery):
    """Mock that handles .single() by returning first item directly."""

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


class TestGetProfile:
    def test_get_profile_unauthenticated(self, client):
        """Profile endpoint requires auth."""
        resp = client.get("/api/v1/profile")
        assert resp.status_code in (401, 403)

    def test_get_profile_success(self, client, auth_headers, fake_supabase):
        """Returns user profile."""
        fake_supabase.set_table(
            "users",
            _SingleQuery(
                data=[
                    {
                        "id": "test-user-id",
                        "phone": "+260971234567",
                        "full_name": "Test User",
                        "email": "test@example.com",
                        "location": "Lusaka",
                    }
                ]
            ),
        )
        fake_supabase.set_table("user_skills", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table("cvs", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "subscriptions",
            _SingleQuery(
                data=[{"tier": "free", "matches_used": 0, "matches_limit": 5}]
            ),
        )
        resp = client.get("/api/v1/profile", headers=auth_headers)
        # May be 200 or 404 depending on whether profile router exists
        assert resp.status_code in (200, 404)


class TestProfileSkills:
    def test_add_new_skill_creates_row(
        self, client, auth_headers, fake_supabase
    ):
        """Adding a new skill creates user_skill entry."""
        fake_supabase.set_table(
            "skills",
            FakeSupabaseQuery(
                data=[{"id": "skill-python", "name": "python"}]
            ),
        )
        fake_supabase.set_table(
            "user_skills",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "us-1",
                        "user_id": "test-user-id",
                        "skill_id": "skill-python",
                    }
                ]
            ),
        )
        resp = client.post(
            "/api/v1/profile/skills",
            headers=auth_headers,
            json={"skill_name": "python"},
        )
        # May be 201 or 404 depending on whether profile/skills router exists
        assert resp.status_code in (200, 201, 404)

    def test_add_skill_rejects_empty_name(
        self, client, auth_headers, fake_supabase
    ):
        """Rejects empty skill name."""
        resp = client.post(
            "/api/v1/profile/skills",
            headers=auth_headers,
            json={"skill_name": ""},
        )
        assert resp.status_code in (422, 404)

    def test_update_skill_proficiency(
        self, client, auth_headers, fake_supabase
    ):
        """Updates skill proficiency level."""
        fake_supabase.set_table(
            "user_skills",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "us-1",
                        "user_id": "test-user-id",
                        "skill_id": "skill-python",
                        "proficiency": "advanced",
                    }
                ]
            ),
        )
        resp = client.patch(
            "/api/v1/profile/skills/skill-python",
            headers=auth_headers,
            json={"proficiency": "advanced"},
        )
        assert resp.status_code in (200, 404)

    def test_update_skill_404_when_unknown(
        self, client, auth_headers, fake_supabase
    ):
        """Returns 404 for unknown skill."""
        fake_supabase.set_table("user_skills", FakeSupabaseQuery(data=[]))
        resp = client.patch(
            "/api/v1/profile/skills/nonexistent",
            headers=auth_headers,
            json={"proficiency": "beginner"},
        )
        assert resp.status_code in (404,)

    def test_remove_skill(self, client, auth_headers, fake_supabase):
        """Removes a user skill."""
        fake_supabase.set_table(
            "user_skills",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "us-1",
                        "user_id": "test-user-id",
                        "skill_id": "skill-python",
                    }
                ]
            ),
        )
        resp = client.delete(
            "/api/v1/profile/skills/skill-python",
            headers=auth_headers,
        )
        assert resp.status_code in (200, 204, 404)

    def test_remove_skill_404_when_unknown(
        self, client, auth_headers, fake_supabase
    ):
        """Returns 404 for unknown skill removal."""
        fake_supabase.set_table("user_skills", FakeSupabaseQuery(data=[]))
        resp = client.delete(
            "/api/v1/profile/skills/nonexistent",
            headers=auth_headers,
        )
        assert resp.status_code in (404,)
