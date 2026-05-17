"""Integration tests for /api/v1/preferences."""
from unittest.mock import MagicMock

from tests.conftest import FakeSupabaseQuery


class _PrefsTable(FakeSupabaseQuery):
    """Mock that tracks update + upsert calls and returns the latest row.

    Mirrors enough of supabase-py's table behaviour for the preferences
    endpoint flow (select/update/upsert with the row cached in-memory).
    """

    def __init__(self, initial_row=None):
        super().__init__(data=[initial_row] if initial_row else [])
        self.updates: list[dict] = []
        self.upserts: list[dict] = []

    def update(self, payload):
        self.updates.append(payload)
        if self._data:
            merged = dict(self._data[0])
            merged.update(payload)
            self._data = [merged]
        return self

    def upsert(self, payload, **_kw):
        self.upserts.append(payload)
        if not self._data:
            self._data = [dict(payload)]
        return self


class TestGetPreferences:
    def test_requires_auth(self, client):
        resp = client.get("/api/v1/preferences")
        assert resp.status_code in (401, 403)

    def test_auto_creates_empty_row(self, client, auth_headers, fake_supabase):
        prefs = _PrefsTable(initial_row=None)
        fake_supabase.set_table("user_preferences", prefs)
        resp = client.get("/api/v1/preferences", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["target_roles"] == []
        assert body["salary_min"] is None
        assert body["salary_currency"] == "ZMW"
        # Empty row → upsert was called.
        assert prefs.upserts, "expected upsert to seed an empty row"

    def test_returns_existing_row(self, client, auth_headers, fake_supabase):
        prefs = _PrefsTable(
            initial_row={
                "user_id": "test-user-id",
                "target_roles": ["Software Engineer"],
                "target_roles_source": "user_provided",
                "salary_min": 1000000,
                "salary_max": 2000000,
                "salary_currency": "ZMW",
                "salary_frequency": "monthly",
                "preferred_work_arrangement": "remote",
                "willing_to_relocate": False,
                "acceptable_regions": ["Lusaka"],
                "languages": [],
                "industries": [],
                "extras": {},
                "auto_populated_at": None,
                "manually_updated_at": None,
            }
        )
        fake_supabase.set_table("user_preferences", prefs)
        resp = client.get("/api/v1/preferences", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["target_roles"] == ["Software Engineer"]
        assert body["salary_min"] == 1000000
        assert body["salary_max"] == 2000000


class TestPatchPreferences:
    def test_requires_auth(self, client):
        resp = client.patch("/api/v1/preferences", json={"target_roles": ["X"]})
        assert resp.status_code in (401, 403)

    def test_updates_fields(self, client, auth_headers, fake_supabase):
        prefs = _PrefsTable(
            initial_row={
                "user_id": "test-user-id",
                "target_roles": [],
                "target_roles_source": "user_provided",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": "ZMW",
                "salary_frequency": None,
                "preferred_work_arrangement": None,
                "willing_to_relocate": False,
                "acceptable_regions": [],
                "languages": [],
                "industries": [],
                "extras": {},
                "auto_populated_at": None,
                "manually_updated_at": None,
            }
        )
        fake_supabase.set_table("user_preferences", prefs)
        resp = client.patch(
            "/api/v1/preferences",
            headers=auth_headers,
            json={"target_roles": ["Data Analyst"], "salary_min": 500000},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["target_roles"] == ["Data Analyst"]
        assert body["salary_min"] == 500000
        # manually_updated_at should be stamped.
        assert prefs.updates, "PATCH should have produced an update call"
        last = prefs.updates[-1]
        assert "manually_updated_at" in last

    def test_rejects_salary_min_greater_than_max(
        self, client, auth_headers, fake_supabase
    ):
        prefs = _PrefsTable(initial_row={"user_id": "test-user-id"})
        fake_supabase.set_table("user_preferences", prefs)
        resp = client.patch(
            "/api/v1/preferences",
            headers=auth_headers,
            json={"salary_min": 2000, "salary_max": 1000},
        )
        assert resp.status_code == 422

    def test_caps_target_roles_at_ten(self, client, auth_headers, fake_supabase):
        prefs = _PrefsTable(initial_row={"user_id": "test-user-id"})
        fake_supabase.set_table("user_preferences", prefs)
        many_roles = [f"Role {i}" for i in range(20)]
        resp = client.patch(
            "/api/v1/preferences",
            headers=auth_headers,
            json={"target_roles": many_roles},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["target_roles"]) <= 10

    def test_caps_languages_at_eight(self, client, auth_headers, fake_supabase):
        prefs = _PrefsTable(initial_row={"user_id": "test-user-id"})
        fake_supabase.set_table("user_preferences", prefs)
        resp = client.patch(
            "/api/v1/preferences",
            headers=auth_headers,
            json={
                "languages": [
                    {"language": f"Lang{i}", "proficiency": "intermediate"}
                    for i in range(15)
                ]
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["languages"]) <= 8

    def test_dedup_target_roles_case_insensitive(
        self, client, auth_headers, fake_supabase
    ):
        prefs = _PrefsTable(initial_row={"user_id": "test-user-id"})
        fake_supabase.set_table("user_preferences", prefs)
        resp = client.patch(
            "/api/v1/preferences",
            headers=auth_headers,
            json={"target_roles": ["Engineer", "engineer", "ENGINEER", "Analyst"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["target_roles"]) == 2

    def test_empty_patch_returns_current_state(
        self, client, auth_headers, fake_supabase
    ):
        prefs = _PrefsTable(
            initial_row={
                "user_id": "test-user-id",
                "target_roles": ["X"],
                "target_roles_source": "user_provided",
                "willing_to_relocate": True,
            }
        )
        fake_supabase.set_table("user_preferences", prefs)
        resp = client.patch(
            "/api/v1/preferences", headers=auth_headers, json={}
        )
        assert resp.status_code == 200

    def test_invalid_proficiency_rejected(
        self, client, auth_headers, fake_supabase
    ):
        prefs = _PrefsTable(initial_row={"user_id": "test-user-id"})
        fake_supabase.set_table("user_preferences", prefs)
        resp = client.patch(
            "/api/v1/preferences",
            headers=auth_headers,
            json={
                "languages": [
                    {"language": "English", "proficiency": "expert-plus"}
                ]
            },
        )
        assert resp.status_code == 422

    def test_invalid_work_arrangement_rejected(
        self, client, auth_headers, fake_supabase
    ):
        prefs = _PrefsTable(initial_row={"user_id": "test-user-id"})
        fake_supabase.set_table("user_preferences", prefs)
        resp = client.patch(
            "/api/v1/preferences",
            headers=auth_headers,
            json={"preferred_work_arrangement": "yacht"},
        )
        assert resp.status_code == 422

    def test_industry_years_clamped(self, client, auth_headers, fake_supabase):
        prefs = _PrefsTable(initial_row={"user_id": "test-user-id"})
        fake_supabase.set_table("user_preferences", prefs)
        # years 999 should validation-fail (Pydantic le=80).
        resp = client.patch(
            "/api/v1/preferences",
            headers=auth_headers,
            json={
                "industries": [
                    {"industry": "Banking", "years_experience": 999}
                ]
            },
        )
        assert resp.status_code == 422


class TestApplyPreferencesToMatch:
    """Unit tests for the matching service's preference bonus."""

    def test_no_preferences_no_adjustment(self):
        from app.services.matching import apply_preferences_to_match

        score, bonus, note = apply_preferences_to_match(
            base_score=70.0,
            base_bonus=5.0,
            job={"title": "Software Engineer", "location": "Lusaka"},
            preferences=None,
        )
        assert score == 70.0
        assert bonus == 5.0
        assert note is None

    def test_target_role_match_bumps_score(self):
        from app.services.matching import apply_preferences_to_match

        score, bonus, note = apply_preferences_to_match(
            base_score=70.0,
            base_bonus=5.0,
            job={"title": "Senior Software Engineer", "location": "Lusaka"},
            preferences={"target_roles": ["Software Engineer"]},
        )
        assert score > 70.0
        assert bonus > 5.0
        assert note and "target role" in note

    def test_arrangement_match(self):
        from app.services.matching import apply_preferences_to_match

        score, bonus, note = apply_preferences_to_match(
            base_score=70.0,
            base_bonus=0.0,
            job={"title": "X", "work_arrangement": "remote"},
            preferences={"preferred_work_arrangement": "remote"},
        )
        assert score > 70.0
        assert note and "remote" in note

    def test_arrangement_any_is_wildcard(self):
        from app.services.matching import apply_preferences_to_match

        score, _, _ = apply_preferences_to_match(
            base_score=70.0,
            base_bonus=0.0,
            job={"title": "X", "work_arrangement": "remote"},
            preferences={"preferred_work_arrangement": "any"},
        )
        # 'any' shouldn't fire the arrangement bonus.
        assert score == 70.0

    def test_score_capped_at_100(self):
        from app.services.matching import apply_preferences_to_match

        score, _, _ = apply_preferences_to_match(
            base_score=99.0,
            base_bonus=0.0,
            job={
                "title": "Software Engineer",
                "location": "Lusaka",
                "work_arrangement": "remote",
                "salary_min": 1000,
                "salary_max": 5000,
            },
            preferences={
                "target_roles": ["Software Engineer"],
                "preferred_work_arrangement": "remote",
                "salary_min": 2000,
                "salary_max": 4000,
                "acceptable_regions": ["Lusaka"],
            },
        )
        assert score <= 100.0

    def test_salary_overlap_fires_bonus(self):
        from app.services.matching import apply_preferences_to_match

        score, _, _ = apply_preferences_to_match(
            base_score=50.0,
            base_bonus=0.0,
            job={"title": "X", "salary_min": 1000, "salary_max": 5000},
            preferences={"salary_min": 2000, "salary_max": 6000},
        )
        assert score > 50.0
