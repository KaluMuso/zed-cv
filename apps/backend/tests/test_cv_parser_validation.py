"""Unit tests for CVParseResult — the Pydantic schema that validates and
coerces LLM output before it lands in `cvs.parsed_data`.

The LLM frequently returns slightly-wrong shapes (strings instead of
arrays, dicts inside skill arrays, "5+ years" as years_experience).
These tests pin the tolerant-coercion behavior so a future "let's just
trust the LLM" refactor can't regress past failures back into prod.
"""
import pytest
from pydantic import ValidationError

from app.services.cv_parser import CVParseResult


class TestSkillsCoercion:
    def test_normal_lowercase_array(self):
        r = CVParseResult(skills=["python", "sql"])
        assert r.skills == ["python", "sql"]

    def test_mixed_case_deduplicates_after_lowercasing(self):
        r = CVParseResult(skills=["Python", "python", "PYTHON", "SQL"])
        assert r.skills == ["python", "sql"]

    def test_array_of_dicts_with_name_field(self):
        # Real LLM output we've seen: [{"name": "react", "level": "advanced"}]
        r = CVParseResult(skills=[{"name": "react", "level": "advanced"}, {"name": "node"}])
        assert r.skills == ["react", "node"]

    def test_single_string_instead_of_array(self):
        # LLM occasionally drops the array wrapper
        r = CVParseResult(skills="python")
        assert r.skills == ["python"]

    def test_drops_null_and_empty(self):
        r = CVParseResult(skills=["python", None, "", "  "])
        assert r.skills == ["python"]

    def test_handles_completely_missing(self):
        r = CVParseResult()
        assert r.skills == []


class TestYearsExperienceCoercion:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            (5, 5),
            ("5", 5),
            ("5 years", 5),
            ("5+", 5),
            ("5.7", 5),
            (5.0, 5),
            (None, 0),
            ("", 0),
            ("a lot", 0),
            (-3, 0),       # clamp negative
            (999, 80),     # clamp absurd
            ("100", 80),
        ],
    )
    def test_lenient_coercion(self, raw, expected):
        r = CVParseResult(years_experience=raw)
        assert r.years_experience == expected


class TestConfidenceCoercion:
    def test_normalizes_0_to_100_scale(self):
        # LLM occasionally returns 85 instead of 0.85
        r = CVParseResult(confidence=85)
        assert r.confidence == 0.85

    def test_passes_through_0_to_1(self):
        r = CVParseResult(confidence=0.92)
        assert r.confidence == 0.92

    def test_clamps_above_1(self):
        # Already-scaled but over 100 -> still clamped
        r = CVParseResult(confidence=200)
        assert r.confidence == 1.0

    def test_string_input(self):
        r = CVParseResult(confidence="0.5")
        assert r.confidence == 0.5

    def test_missing_defaults_to_zero(self):
        r = CVParseResult()
        assert r.confidence == 0.0


class TestRequiredFieldsAreNotRequired:
    """All fields have safe defaults — a totally-empty LLM response
    should still produce a valid model, not 422 the whole upload."""

    def test_empty_dict_is_valid(self):
        r = CVParseResult()
        assert r.full_name == ""
        assert r.email is None
        assert r.phone is None
        assert r.years_experience == 0
        assert r.confidence == 0.0

    def test_rejects_genuinely_bad_types(self):
        # full_name as a deeply-nested object is not coercible — bail.
        with pytest.raises(ValidationError):
            CVParseResult(full_name={"deeply": {"nested": "thing"}})


class TestEducationCoercion:
    def test_array_of_strings(self):
        r = CVParseResult(education=["BSc UNZA", "Grade 12"])
        assert r.education == ["BSc UNZA", "Grade 12"]

    def test_array_of_dicts(self):
        r = CVParseResult(
            education=[{"name": "BSc Computer Science"}, {"title": "Grade 12"}]
        )
        assert r.education == ["BSc Computer Science", "Grade 12"]

    def test_education_is_NOT_lowercased(self):
        # skills are lowercased (dedupe key), education is human-readable
        r = CVParseResult(education=["BSc Computer Science"])
        assert r.education == ["BSc Computer Science"]
