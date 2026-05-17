"""Unit tests for app.services.role_inference."""
from app.services.role_inference import (
    normalize_role_title,
    normalize_role_titles,
)


class TestNormalizeRoleTitle:
    def test_strips_seniority_prefix(self):
        assert normalize_role_title("Senior Software Engineer") == "Software Engineer"

    def test_strips_junior_prefix(self):
        assert normalize_role_title("Junior Data Analyst") == "Data Analyst"

    def test_strips_lead_prefix(self):
        assert normalize_role_title("Lead Data Engineer") == "Data Engineer"

    def test_strips_trailing_year_range_parens(self):
        assert (
            normalize_role_title("Senior Software Engineer (2020-2023)")
            == "Software Engineer"
        )

    def test_strips_trailing_year_range_plain(self):
        assert (
            normalize_role_title("Software Engineer 2020-2023")
            == "Software Engineer"
        )

    def test_strips_employment_type_suffix(self):
        assert (
            normalize_role_title("Marketing Manager - Full-time")
            == "Marketing Manager"
        )

    def test_strips_present_in_year_range(self):
        assert (
            normalize_role_title("Senior Analyst (2022 - present)") == "Analyst"
        )

    def test_handles_empty_string(self):
        assert normalize_role_title("") == ""

    def test_handles_whitespace_only(self):
        assert normalize_role_title("   ") == ""

    def test_handles_non_string(self):
        assert normalize_role_title(None) == ""  # type: ignore[arg-type]
        assert normalize_role_title(123) == ""  # type: ignore[arg-type]

    def test_keeps_title_when_seniority_is_the_role(self):
        # "Senior" alone (no following word) stays — it might be the
        # actual title for a Senior at a law firm. The regex only fires
        # on Senior + space + word.
        assert normalize_role_title("Senior") == "Senior"

    def test_collapses_repeated_whitespace(self):
        assert (
            normalize_role_title("Senior   Software   Engineer")
            == "Software Engineer"
        )

    def test_strips_trailing_paren_location(self):
        assert normalize_role_title("Engineer (Lusaka)") == "Engineer"

    def test_strips_trailing_brackets(self):
        assert normalize_role_title("Engineer [Remote]") == "Engineer"

    def test_strips_multiple_trailing_parens(self):
        assert (
            normalize_role_title("Engineer (Lusaka) (2020-2023)") == "Engineer"
        )

    def test_keeps_location_after_comma(self):
        # Comma-separated location is part of the title we leave alone —
        # only employment-type suffixes after the comma get stripped.
        assert (
            normalize_role_title("Data Analyst, Lusaka") == "Data Analyst, Lusaka"
        )

    def test_strips_part_time_suffix(self):
        assert (
            normalize_role_title("Teacher - Part-time") == "Teacher"
        )

    def test_strips_internship_suffix(self):
        assert normalize_role_title("Software Engineer - Internship") == "Software Engineer"

    def test_nested_seniority_loop(self):
        # Pathological input. Should still terminate and produce
        # something sensible.
        result = normalize_role_title("Senior Lead Principal Engineer")
        assert "Engineer" in result

    def test_does_not_mistake_version_for_year(self):
        # "Web 2.0" should stay. The year regex is restricted to 19xx/20xx
        # 4-digit years.
        assert normalize_role_title("Web 2.0 Developer") == "Web 2.0 Developer"


class TestNormalizeRoleTitles:
    def test_dedup_case_insensitive(self):
        result = normalize_role_titles(
            ["Software Engineer", "software engineer", "SOFTWARE ENGINEER"]
        )
        assert result == ["Software Engineer"]

    def test_preserves_first_occurrence_order(self):
        result = normalize_role_titles(
            ["Senior Engineer", "Data Analyst", "Lead Engineer"]
        )
        assert result == ["Engineer", "Data Analyst"]

    def test_drops_empties(self):
        result = normalize_role_titles(["", "   ", "Engineer"])
        assert result == ["Engineer"]

    def test_empty_list(self):
        assert normalize_role_titles([]) == []
