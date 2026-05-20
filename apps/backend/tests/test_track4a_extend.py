"""Track 4a-extend: profile/job enrichment + experience matching penalty."""
from __future__ import annotations

import json
import os
import sys
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

_BACKEND_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.services.experience_matching import experience_score_multiplier
from app.services.job_enricher import JobEnrichment, parse_llm_enrichment_payload
from app.services.job_enrichment import apply_job_enrichment
from app.services.user_profile_enricher import (
    UserProfileEnrichment,
    build_user_profile_patch,
    enrich_user_profile,
    parse_user_profile_payload,
)
from tests.test_admin_jobs import JobsFakeSupabase

# ── Sample enriched jobs (for PR description / regression fixtures) ──
SAMPLE_ENRICHED_JOBS = [
    {
        "title": "Senior Electrical Engineer",
        "experience_min_years": 5,
        "experience_max_years": 8,
        "seniority_level": "senior",
        "qualifications_required": ["Bachelor's in Electrical Engineering", "EIZ"],
    },
    {
        "title": "Graduate Trainee Accountant",
        "experience_min_years": 0,
        "experience_max_years": 1,
        "seniority_level": "intern",
        "qualifications_required": ["ACCA Part-qualified"],
    },
    {
        "title": "IT Support Officer",
        "experience_min_years": 2,
        "experience_max_years": None,
        "seniority_level": "entry",
        "qualifications_required": ["Diploma in Computer Science"],
    },
    {
        "title": "Operations Manager",
        "experience_min_years": 7,
        "experience_max_years": None,
        "seniority_level": "lead",
        "qualifications_required": ["MBA", "ZICA"],
    },
    {
        "title": "Marketing Coordinator",
        "experience_min_years": 3,
        "experience_max_years": 5,
        "seniority_level": "mid",
        "qualifications_required": ["Bachelor's in Marketing"],
    },
]


class TestExperiencePenaltyMultiplier:
    """Acceptance RPC scenarios (mirrored in migration 033 SQL)."""

    def test_meets_minimum_no_penalty(self):
        assert experience_score_multiplier(3, 3) == 1.0

    def test_overqualified_no_penalty(self):
        assert experience_score_multiplier(10, 1) == 1.0

    def test_four_year_gap_penalty(self):
        assert experience_score_multiplier(1, 5) == pytest.approx(0.6)

    def test_unknown_job_min_is_neutral(self):
        assert experience_score_multiplier(1, None) == 1.0


class TestJobEnricherExtendedFields:
    def test_parse_experience_and_qualifications(self):
        result = parse_llm_enrichment_payload(
            {
                "skills": ["python"],
                "employment_type": "full_time",
                "work_arrangement": "hybrid",
                "experience_min_years": "5+",
                "experience_max_years": 8,
                "seniority_level": "SENIOR",
                "qualifications_required": ["ACCA", "  "],
            }
        )
        assert result.experience_min_years == 5
        assert result.experience_max_years == 8
        assert result.seniority_level == "senior"
        assert result.qualifications_required == ["ACCA"]

    @pytest.mark.asyncio
    async def test_enrich_job_mock_openrouter(self):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "skills": ["fastapi"],
                            "employment_type": "full_time",
                            "work_arrangement": "remote",
                            "experience_min_years": 3,
                            "experience_max_years": None,
                            "seniority_level": "mid",
                            "qualifications_required": ["Bachelor's in IT"],
                        }
                    )
                )
            )
        ]
        with patch("app.services.job_enricher._client") as mock_factory:
            client = MagicMock()
            mock_factory.return_value = client
            client.chat.completions.create.return_value = mock_response
            from app.services.job_enricher import enrich_job

            result = await enrich_job(
                title="Developer",
                company="Tech",
                description="Need 3 years Python. Bachelor's in IT required.",
            )
        assert result.experience_min_years == 3
        assert result.seniority_level == "mid"
        assert "Bachelor's in IT" in result.qualifications_required


class TestApplyJobEnrichmentExtended:
    @pytest.mark.asyncio
    async def test_null_only_writes_experience_fields(self):
        fake = JobsFakeSupabase()
        job_id = str(uuid4())
        fake.tables["jobs"] = [
            {
                "id": job_id,
                "title": "Engineer",
                "employment_type": "full_time",
                "work_arrangement": None,
                "experience_min_years": 2,
                "experience_max_years": None,
                "seniority_level": None,
                "qualifications_required": [],
            }
        ]
        enrichment = JobEnrichment(
            experience_min_years=5,
            experience_max_years=10,
            seniority_level="senior",
            qualifications_required=["EIZ"],
        )
        with patch(
            "app.services.job_enrichment.resolve_skill_ids",
            new_callable=AsyncMock,
            return_value=[],
        ):
            stats = await apply_job_enrichment(
                fake,
                job_id=job_id,
                job_row=fake.tables["jobs"][0],
                enrichment=enrichment,
            )
        row = fake.tables["jobs"][0]
        assert row["experience_min_years"] == 2
        assert row["seniority_level"] == "senior"
        assert row["qualifications_required"] == ["EIZ"]
        assert stats["experience_min_set"] is False
        assert stats["seniority_set"] is True


class TestUserProfileEnricher:
    def test_parse_user_profile_payload(self):
        result = parse_user_profile_payload(
            {
                "years_experience": "6 years",
                "seniority_level": "lead",
                "highest_qualification": "MBA",
                "qualifications": ["MBA", "BCom"],
            }
        )
        assert result.years_experience == 6
        assert result.seniority_level == "lead"
        assert result.highest_qualification == "MBA"
        assert result.qualifications == ["MBA", "BCom"]

    def test_build_user_profile_patch_fills_blanks(self):
        enrichment = UserProfileEnrichment(
            years_experience=8,
            seniority_level="senior",
            highest_qualification="BEng",
            qualifications=["BEng"],
        )
        patch = build_user_profile_patch(
            enrichment,
            user_row={
                "years_experience": 0,
                "seniority_level": None,
                "highest_qualification": None,
                "qualifications": [],
            },
        )
        assert patch["years_experience"] == 8
        assert patch["seniority_level"] == "senior"
        assert patch["highest_qualification"] == "BEng"

    def test_build_user_profile_patch_higher_confidence_overwrites(self):
        enrichment = UserProfileEnrichment(
            years_experience=8,
            seniority_level="senior",
        )
        patch = build_user_profile_patch(
            enrichment,
            user_row={
                "years_experience": 3,
                "seniority_level": "mid",
                "highest_qualification": "Diploma",
                "qualifications": ["Diploma"],
            },
            new_cv_confidence=0.95,
            previous_primary_confidence=0.7,
        )
        assert patch["years_experience"] == 8
        assert patch["seniority_level"] == "senior"

    def test_build_user_profile_patch_low_confidence_skips_overwrite(self):
        enrichment = UserProfileEnrichment(years_experience=8, seniority_level="senior")
        patch = build_user_profile_patch(
            enrichment,
            user_row={"years_experience": 3, "seniority_level": "mid"},
            new_cv_confidence=0.5,
            previous_primary_confidence=0.8,
        )
        assert patch == {}

    @pytest.mark.asyncio
    async def test_enrich_user_profile_mock_openrouter(self):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "years_experience": 4,
                            "seniority_level": "mid",
                            "highest_qualification": "Bachelor's in Accounting",
                            "qualifications": ["ACCA"],
                        }
                    )
                )
            )
        ]
        with patch("app.services.user_profile_enricher._client") as mock_factory:
            client = MagicMock()
            mock_factory.return_value = client
            client.chat.completions.create.return_value = mock_response
            result = await enrich_user_profile(cv_text="4 years audit experience. ACCA.")
        assert result.years_experience == 4
        assert result.seniority_level == "mid"


class TestBackfillIdempotency:
    @pytest.mark.asyncio
    async def test_apply_skips_done_jobs(self, tmp_path, monkeypatch):
        scripts_dir = os.path.join(_BACKEND_ROOT, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import backfill_job_enrichment as mod

        progress_path = tmp_path / "progress.json"
        progress_path.write_text(
            json.dumps({"job-done": "done"}),
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "PROGRESS_PATH", progress_path)

        job = {
            "id": "job-done",
            "title": "Done role",
            "description": "x" * 60,
            "employment_type": None,
            "work_arrangement": None,
        }
        enrich_calls = 0

        async def _fake_enrich(**_kw):
            nonlocal enrich_calls
            enrich_calls += 1
            from app.services.job_enricher import EnrichJobOutcome

            return EnrichJobOutcome(enrichment=JobEnrichment(skills=["x"]))

        monkeypatch.setattr(mod, "enrich_job_for_backfill", _fake_enrich)
        line, limited = await mod._process_job(
            MagicMock(),
            job,
            apply=True,
            progress=mod._load_progress(),
        )
        assert line == ""
        assert limited is False
        assert enrich_calls == 0


class TestMigration033ExperiencePenalty:
    @staticmethod
    def _sql_path() -> str:
        from pathlib import Path

        return str(
            Path(__file__).resolve().parents[3]
            / "infra"
            / "supabase"
            / "migrations"
            / "033_experience_penalty_0_1.sql"
        )

    def test_migration_defines_experience_columns(self):
        from pathlib import Path

        sql = Path(self._sql_path()).read_text()
        for col in (
            "experience_min_years",
            "experience_max_years",
            "seniority_level",
            "qualifications_required",
        ):
            assert col in sql
        assert "users" in sql and "highest_qualification" in sql
        assert "matches" in sql and "experience_score" in sql

    def test_rpc_contains_penalty_formula(self):
        from pathlib import Path

        sql = Path(self._sql_path()).read_text()
        assert "0.1 * (j.experience_min_years - v_user_years)" in sql
        assert "0.5::REAL" in sql
        assert "GREATEST" in sql
        assert "experience_score  REAL" in sql

    def test_rpc_three_scenario_multipliers_documented(self):
        """Python helper mirrors SQL — pin the three acceptance scenarios."""
        assert experience_score_multiplier(3, 3) == 1.0
        assert experience_score_multiplier(10, 1) == 1.0
        assert experience_score_multiplier(1, 5) == pytest.approx(0.6)
