"""Unit tests for app.services.preferences_auto_populate."""
import asyncio
from unittest.mock import MagicMock

import pytest

from app.services.preferences_auto_populate import (
    auto_populate_from_cv,
    _classify_industry,
    _extract_languages_from_skills,
    _extract_languages_from_sections,
    _infer_target_roles,
    _infer_industries,
    _infer_regions,
)


# ── Pure helpers ────────────────────────────────────────────────────


class TestClassifyIndustry:
    def test_returns_none_when_no_keyword(self):
        assert _classify_industry("Acme Co.", "general work") is None

    def test_classifies_mining(self):
        assert _classify_industry("Mopani Copper Mines", "shift supervisor") == "Mining"

    def test_classifies_banking(self):
        assert _classify_industry("Zanaco", "branch teller") == "Banking"

    def test_classifies_healthcare(self):
        assert _classify_industry("UTH", "nurse on the ward") == "Healthcare"

    def test_classifies_ngo(self):
        assert _classify_industry("UNICEF Zambia", "field officer") == "NGO"

    def test_returns_none_for_empty(self):
        assert _classify_industry("", "") is None


class TestExtractLanguagesFromSkills:
    def test_picks_known_languages(self):
        result = _extract_languages_from_skills(["python", "english", "bemba", "javascript"])
        names = sorted(lang["language"] for lang in result)
        assert names == ["Bemba", "English"]

    def test_default_proficiency_intermediate(self):
        result = _extract_languages_from_skills(["english"])
        assert result == [{"language": "English", "proficiency": "intermediate"}]

    def test_deduplicates(self):
        result = _extract_languages_from_skills(["english", "English", "ENGLISH"])
        assert len(result) == 1

    def test_handles_non_strings(self):
        result = _extract_languages_from_skills(["english", None, 42, "bemba"])  # type: ignore
        assert len(result) == 2


class TestExtractLanguagesFromSections:
    def test_maps_conversational_to_intermediate(self):
        result = _extract_languages_from_sections(
            [{"name": "Bemba", "proficiency": "conversational"}]
        )
        assert result == [{"language": "Bemba", "proficiency": "intermediate"}]

    def test_preserves_native(self):
        result = _extract_languages_from_sections(
            [{"name": "English", "proficiency": "native"}]
        )
        assert result == [{"language": "English", "proficiency": "native"}]

    def test_handles_missing_proficiency(self):
        result = _extract_languages_from_sections([{"name": "French"}])
        assert result == [{"language": "French", "proficiency": "intermediate"}]


class TestInferTargetRoles:
    def test_from_work_experience(self):
        parsed = {
            "sections": {
                "work_experience": [
                    {"title": "Senior Software Engineer", "company": "Acme"},
                    {"title": "Software Engineer", "company": "Acme"},
                    {"title": "Data Analyst", "company": "BetaCorp"},
                ]
            }
        }
        result = _infer_target_roles(parsed)
        # Dedup happens after normalization: "Senior Software Engineer"
        # and "Software Engineer" both collapse to "Software Engineer".
        assert "Software Engineer" in result
        assert "Data Analyst" in result

    def test_empty_when_no_sections(self):
        assert _infer_target_roles({}) == []
        assert _infer_target_roles({"sections": {}}) == []
        assert _infer_target_roles({"sections": {"work_experience": []}}) == []

    def test_caps_at_three(self):
        parsed = {
            "sections": {
                "work_experience": [
                    {"title": f"Role {i}"} for i in range(10)
                ]
            }
        }
        assert len(_infer_target_roles(parsed)) <= 3


class TestInferIndustries:
    def test_collects_industries(self):
        parsed = {
            "sections": {
                "work_experience": [
                    {
                        "company": "Zanaco",
                        "start_date": "2020-01",
                        "end_date": "2023-01",
                        "achievements": ["branch operations"],
                    },
                    {
                        "company": "Mopani",
                        "start_date": "2015-01",
                        "end_date": "2020-01",
                        "achievements": [],
                    },
                ]
            }
        }
        result = _infer_industries(parsed)
        industries = sorted(r["industry"] for r in result)
        assert industries == ["Banking", "Mining"]

    def test_skips_unclassifiable_roles(self):
        # Acme + "writing code" — no keyword fires; this entry is dropped.
        parsed = {
            "sections": {
                "work_experience": [{"company": "Acme", "achievements": ["wrote code"]}]
            }
        }
        assert _infer_industries(parsed) == []


class TestInferRegions:
    def test_lifts_location(self):
        assert _infer_regions({"location": "Lusaka"}) == ["Lusaka"]

    def test_empty_when_missing(self):
        assert _infer_regions({}) == []
        assert _infer_regions({"location": ""}) == []
        assert _infer_regions({"location": "   "}) == []


# ── auto_populate_from_cv (end-to-end with mocked Supabase) ─────────


class FakeUserPrefsTable:
    """Tiny mock that records inserts/updates."""

    def __init__(self, initial=None):
        self._rows = list(initial) if initial else []
        self.update_calls: list[dict] = []
        self.upsert_calls: list[dict] = []
        self._mode = None  # tracks the pending op
        self._pending = None

    # supabase-py chain methods
    def select(self, *a, **kw):
        return self

    def eq(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return self

    def upsert(self, payload, **kw):
        self.upsert_calls.append(payload)
        if not self._rows:
            self._rows.append(dict(payload))
        return self

    def update(self, payload):
        self.update_calls.append(payload)
        # Apply to the in-memory row so a follow-up select sees it.
        if self._rows:
            self._rows[0].update(payload)
        return self

    def insert(self, payload):
        self._pending = payload
        return self

    def execute(self):
        result = MagicMock()
        result.data = list(self._rows)
        return result


class FakeAnalyticsTable:
    def __init__(self):
        self.events: list[dict] = []

    def insert(self, payload):
        self.events.append(payload)
        return self

    def execute(self):
        result = MagicMock()
        result.data = []
        return result


class FakeSupabase:
    def __init__(self, prefs_initial=None):
        self.prefs = FakeUserPrefsTable(prefs_initial)
        self.analytics = FakeAnalyticsTable()

    def table(self, name):
        if name == "user_preferences":
            return self.prefs
        if name == "analytics_events":
            return self.analytics
        return FakeUserPrefsTable()  # unused tables get an empty stub


RICH_CV = {
    "location": "Lusaka",
    "skills": ["python", "english", "bemba"],
    "sections": {
        "work_experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Acme Tech",
                "start_date": "2021-01",
                "end_date": "2024-01",
                "achievements": ["wrote code"],
            },
            {
                "title": "Software Engineer",
                "company": "Zanaco",
                "start_date": "2018-01",
                "end_date": "2021-01",
                "achievements": ["branch software"],
            },
        ],
        "languages": [{"name": "English", "proficiency": "native"}],
    },
}


@pytest.mark.asyncio
async def test_fills_empty_row_from_rich_cv():
    sb = FakeSupabase(prefs_initial=[])
    filled = await auto_populate_from_cv("user-1", RICH_CV, supabase=sb)
    # All four target fields can be filled from this CV.
    assert set(filled) >= {"target_roles", "languages", "acceptable_regions"}
    # Update should carry the new fields. target_roles normalized.
    assert sb.prefs.update_calls
    payload = sb.prefs.update_calls[-1]
    assert "Software Engineer" in payload["target_roles"]
    assert payload["target_roles_source"] == "cv_inferred"
    # Analytics event logged.
    assert any(e["event"] == "preferences_auto_populated" for e in sb.analytics.events)


@pytest.mark.asyncio
async def test_does_not_overwrite_manually_edited_row():
    """Once manually_updated_at is set, auto-populate leaves the row alone."""
    sb = FakeSupabase(
        prefs_initial=[
            {
                "user_id": "user-1",
                "target_roles": ["My Custom Role"],
                "manually_updated_at": "2026-05-17T12:00:00Z",
            }
        ]
    )
    filled = await auto_populate_from_cv("user-1", RICH_CV, supabase=sb)
    assert filled == []
    # No update call should have fired.
    assert sb.prefs.update_calls == []


@pytest.mark.asyncio
async def test_partial_fill_when_some_fields_already_present():
    """target_roles already set; languages/regions still empty → only those get filled."""
    sb = FakeSupabase(
        prefs_initial=[
            {
                "user_id": "user-1",
                "target_roles": ["Existing Role"],
                "languages": [],
                "industries": [],
                "acceptable_regions": [],
                "manually_updated_at": None,
            }
        ]
    )
    filled = await auto_populate_from_cv("user-1", RICH_CV, supabase=sb)
    assert "target_roles" not in filled
    assert "languages" in filled
    assert "acceptable_regions" in filled


@pytest.mark.asyncio
async def test_empty_cv_fills_nothing():
    sb = FakeSupabase(prefs_initial=[{"user_id": "user-1", "manually_updated_at": None}])
    empty_cv = {"location": "", "skills": [], "sections": {"work_experience": [], "languages": []}}
    filled = await auto_populate_from_cv("user-1", empty_cv, supabase=sb)
    assert filled == []


@pytest.mark.asyncio
async def test_flat_only_cv_uses_skills_for_languages():
    """No sections — fall back to extracting languages from flat skills."""
    sb = FakeSupabase(prefs_initial=[{"user_id": "user-1", "manually_updated_at": None}])
    flat_cv = {"location": "Lusaka", "skills": ["python", "english", "bemba"]}
    filled = await auto_populate_from_cv("user-1", flat_cv, supabase=sb)
    # No work_experience → no target_roles or industries.
    assert "target_roles" not in filled
    assert "industries" not in filled
    # languages + acceptable_regions come through.
    assert "languages" in filled
    assert "acceptable_regions" in filled


@pytest.mark.asyncio
async def test_non_dict_parsed_data_is_noop():
    sb = FakeSupabase(prefs_initial=[])
    filled = await auto_populate_from_cv("user-1", "not a dict", supabase=sb)  # type: ignore
    assert filled == []


@pytest.mark.asyncio
async def test_creates_row_when_missing():
    """A user with no user_preferences row gets one auto-created."""
    sb = FakeSupabase(prefs_initial=[])
    filled = await auto_populate_from_cv("user-1", RICH_CV, supabase=sb)
    assert sb.prefs.upsert_calls  # we did the create
    assert filled  # …and then filled at least one field
