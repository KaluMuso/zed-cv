"""Tests for canonical_skills seed pollution guards."""
from __future__ import annotations

import pytest

from app.services.canonical_skills_seed import build_seed_row_from_raw
from app.services.canonical_skills_seed_validation import reject_seed_candidate


class TestRejectSeedCandidate:
    @pytest.mark.parametrize(
        "text",
        [
            "Degree or Diploma in Sales and Marketing/Business Administration or Any Related Course.",
            "Minimum 5 Years Practical Experience in a Reputable Abattoir Environment.",
        ],
    )
    def test_reject_polluted_job_requirements(self, text: str) -> None:
        assert reject_seed_candidate(text) is not None

    @pytest.mark.parametrize(
        "text,expected_reason",
        [
            ("Bachelor degree required.", "ends in punctuation"),
            ("Minimum five years experience", "qualification phrase"),
            ("Valid Drivers' Lincence", "known typo: lincence"),
            ("Python", None),
            ("Project Management", None),
            ("MS Excel", None),
        ],
    )
    def test_reject_examples(self, text: str, expected_reason: str | None) -> None:
        assert reject_seed_candidate(text) == expected_reason

    def test_too_long_sentence(self) -> None:
        long_text = "a" * 61
        assert reject_seed_candidate(long_text) == "too long"

    def test_too_many_words(self) -> None:
        text = "one two three four five six"
        assert reject_seed_candidate(text) == "too many words"

    def test_too_short(self) -> None:
        assert reject_seed_candidate("go") == "too short"


class TestBuildSeedRowValidation:
    def test_polluted_requirement_not_seeded(self) -> None:
        assert build_seed_row_from_raw(
            "Minimum 5 Years Practical Experience in a Reputable Abattoir Environment."
        ) is None

    def test_valid_skill_still_seeded(self) -> None:
        row = build_seed_row_from_raw("ms excel")
        assert row is not None
        assert row.name == "Microsoft Excel"
