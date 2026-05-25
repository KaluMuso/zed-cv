"""Tests for Phase 2 job_skills extraction backfill script."""
from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_BACKEND_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from scripts import backfill_job_skills_extraction as mod  # noqa: E402


class TestTierRouting:
    def test_short_description_with_url_is_tier2(self):
        job = {
            "id": "j1",
            "description": "x" * 100,
            "source_url": "https://example.com/job/1",
        }
        assert mod._tier_for_job(job) == "tier2"

    def test_long_description_is_tier1(self):
        job = {
            "id": "j2",
            "description": "x" * 500,
            "source_url": "https://example.com/job/2",
        }
        assert mod._tier_for_job(job) == "tier1"

    def test_short_without_url_is_tier1(self):
        job = {"id": "j3", "description": "brief", "source_url": None}
        assert mod._tier_for_job(job) == "tier1"


class TestNullSkillCount:
    def test_count_null_skill_jobs(self):
        fake = MagicMock()
        jobs_table = MagicMock()
        skills_table = MagicMock()

        def table(name: str):
            return jobs_table if name == "jobs" else skills_table

        fake.table.side_effect = table
        jobs_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "a"}, {"id": "b"}, {"id": "c"}]
        )
        skills_table.select.return_value.execute.return_value = MagicMock(
            data=[{"job_id": "a"}]
        )

        assert mod.count_null_skill_jobs(fake) == 2


@pytest.mark.asyncio
async def test_dry_run_reports_before_and_after(monkeypatch):
    fake = MagicMock()
    jobs_table = MagicMock()
    skills_table = MagicMock()

    def table(name: str):
        return jobs_table if name == "jobs" else skills_table

    fake.table.side_effect = table
    jobs_table.select.return_value.eq.return_value.order.return_value.execute.return_value = (
        MagicMock(
            data=[
                {
                    "id": "job-long",
                    "title": "Engineer",
                    "company": "Co",
                    "description": "x" * 500,
                    "source_url": None,
                    "employment_type": None,
                    "work_arrangement": None,
                    "experience_min_years": None,
                    "experience_max_years": None,
                    "seniority_level": None,
                    "qualifications_required": None,
                }
            ]
        )
    )
    jobs_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "job-long"}]
    )
    skills_table.select.return_value.execute.return_value = MagicMock(data=[])

    monkeypatch.setattr(mod, "create_client", lambda *_a, **_k: fake)
    monkeypatch.setattr(
        mod,
        "get_settings",
        lambda: MagicMock(
            openrouter_api_key="sk-test",
            supabase_url="https://x.supabase.co",
            supabase_key="key",
        ),
    )
    monkeypatch.setattr(mod, "_load_progress", lambda: {})
    monkeypatch.setattr(
        mod,
        "_run_enrich_apply",
        AsyncMock(return_value=(False, 3)),
    )

    with patch("builtins.print") as mock_print:
        code = await mod.run_backfill(apply=False, tier_filter="all", limit=1)

    assert code == 0
    printed = " ".join(str(c[0][0]) for c in mock_print.call_args_list)
    assert "null_skill_jobs_before:" in printed
    assert "null_skill_jobs_after:" in printed
