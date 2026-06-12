"""Tests for scraper LLM job enrichment (Track 4a)."""
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

from app.services.job_enricher import (
    JobEnrichment,
    enrich_job,
    parse_llm_enrichment_payload,
)
from app.services.job_enrichment import apply_job_enrichment
from tests.conftest import FakeSupabaseQuery
from tests.test_admin_jobs import JobsFakeSupabase


class TestApplyJobEnrichment:
    @pytest.mark.asyncio
    async def test_merges_skills_without_deleting_existing(self):
        """Existing 3 skill links + 5 resolved ids → 8 unique job_skills rows."""
        fake = JobsFakeSupabase()
        job_id = "job-merge-1"
        fake.tables["jobs"] = [
            {
                "id": job_id,
                "title": "Electrical Engineer",
                "employment_type": None,
                "work_arrangement": None,
            }
        ]
        fake.tables["job_skills"] = [
            {"job_id": job_id, "skill_id": "existing-1"},
            {"job_id": job_id, "skill_id": "existing-2"},
            {"job_id": job_id, "skill_id": "existing-3"},
        ]
        enrichment = JobEnrichment(
            skills=[
                "electrical engineering",
                "circuit design",
                "power systems",
                "plc programming",
                "hvac",
            ],
            employment_type="full_time",
            work_arrangement="on_site",
        )
        resolved = ["new-1", "new-2", "new-3", "new-4", "new-5"]
        with patch(
            "app.services.job_enrichment.resolve_skill_ids",
            new_callable=AsyncMock,
            return_value=resolved,
        ):
            stats = await apply_job_enrichment(
                fake,
                job_id=job_id,
                job_row=fake.tables["jobs"][0],
                enrichment=enrichment,
                source="ingest",
            )

        links = fake.tables["job_skills"]
        assert len(links) == 8
        assert stats["skills_added"] == 5
        assert stats["employment_type_set"] is True
        assert stats["work_arrangement_set"] is True
        assert fake.tables["jobs"][0]["employment_type"] == "full_time"
        assert fake.tables["jobs"][0]["work_arrangement"] == "on_site"
        events = fake.tables["analytics_events"]
        assert len(events) == 1
        assert events[0]["event"] == "job_enriched"
        assert events[0]["properties"]["source"] == "ingest"

    @pytest.mark.asyncio
    async def test_does_not_overwrite_existing_employment_type(self):
        fake = JobsFakeSupabase()
        job_id = "job-enum-1"
        fake.tables["jobs"] = [
            {
                "id": job_id,
                "title": "Analyst",
                "employment_type": "full_time",
                "work_arrangement": "remote",
            }
        ]
        enrichment = JobEnrichment(
            skills=[],
            employment_type="part_time",
            work_arrangement="hybrid",
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

        assert fake.tables["jobs"][0]["employment_type"] == "full_time"
        assert fake.tables["jobs"][0]["work_arrangement"] == "remote"
        assert stats["employment_type_set"] is False
        assert stats["work_arrangement_set"] is False


class TestJobIngestEnrichment:
    @patch("app.api.v1.jobs.apply_job_enrichment", new_callable=AsyncMock)
    @patch("app.api.v1.jobs.enrich_job", new_callable=AsyncMock)
    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    def test_ingest_calls_enrich_and_apply(
        self, mock_embed, mock_enrich, mock_apply, client, fake_supabase
    ):
        mock_embed.return_value = [0.1] * 768
        mock_enrich.return_value = JobEnrichment(
            skills=["python", "fastapi"],
            employment_type="full_time",
            work_arrangement=None,
        )
        mock_apply.return_value = {"skills_added": 2}

        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "jobs", FakeSupabaseQuery(data=[])
        )

        job = {
            "title": "Backend Engineer",
            "company": "TechCo",
            "location": "Lusaka",
            "description": "Build APIs with Python and FastAPI for our payments platform team.",
            "source": "scraper",
        }
        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [job]},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["ingested"] == 1
        mock_enrich.assert_awaited_once()
        mock_apply.assert_awaited_once()
        call_kw = mock_apply.await_args.kwargs
        assert call_kw["job_id"] == "fake-uuid-001"
        assert call_kw["source"] == "ingest"


class TestBackfillScript:
    def test_format_diff_line(self):
        scripts_dir = os.path.join(_BACKEND_ROOT, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from backfill_job_enrichment import format_enrichment_diff_line

        job = {
            "id": "d4a31f8e-0000-0000-0000-000000000001",
            "title": "Electrical Engineer",
            "employment_type": None,
            "work_arrangement": None,
        }
        enrichment = JobEnrichment(
            skills=[
                "electrical engineering",
                "circuit design",
                "power systems",
                "leadership",
            ],
            employment_type="full_time",
            work_arrangement="on_site",
        )
        line = format_enrichment_diff_line(
            job, enrichment, existing_skill_names={"leadership"}
        )
        assert line.startswith("d4a31f8e | Electrical Engineer")
        assert "+ skills: [circuit design, electrical engineering, power systems]" in line
        assert "et: null→full_time" in line
        assert "wa: null→on_site" in line

    @pytest.mark.asyncio
    async def test_dry_run_three_job_fixture(self, tmp_path, monkeypatch):
        scripts_dir = os.path.join(_BACKEND_ROOT, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import backfill_job_enrichment as mod

        monkeypatch.setattr(mod, "PROGRESS_PATH", tmp_path / "progress.json")

        jobs = [
            {
                "id": f"job-{i}",
                "title": f"Role {i}",
                "company": "Co",
                "description": "x" * 60,
                "employment_type": None,
                "work_arrangement": None,
            }
            for i in range(3)
        ]

        fake = MagicMock()
        fake.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=jobs
        )

        from app.services.job_enricher import EnrichJobOutcome

        async def _fake_enrich(**_kw):
            return EnrichJobOutcome(
                enrichment=JobEnrichment(
                    skills=["python"],
                    employment_type="full_time",
                    work_arrangement="remote",
                ),
                completed=True,
            )

        monkeypatch.setattr(mod, "enrich_job_for_backfill", _fake_enrich)
        monkeypatch.setattr(
            mod,
            "create_client",
            lambda *_a, **_k: fake,
        )
        monkeypatch.setattr(
            mod,
            "_existing_skill_names",
            lambda *_a, **_k: set(),
        )

        with patch.object(mod, "get_settings") as mock_settings:
            mock_settings.return_value.openrouter_api_key = "sk-test"
            mock_settings.return_value.supabase_url = "https://x.supabase.co"
            mock_settings.return_value.supabase_key = "key"
            mock_settings.return_value.llm_model = "google/gemini-2.0-flash-001"

            buf = StringIO()
            with patch("sys.stdout", buf):
                code = await mod.run_backfill(apply=False, delay_seconds=0.01)

        assert code == 0
        out = buf.getvalue()
        assert out.count("job-0") >= 1
        assert "Estimated 3 jobs" in out
        assert "dry-run" in out


class TestJobEnricher:
    def test_coerces_unknown_employment_type_but_keeps_skills(self):
        result = parse_llm_enrichment_payload(
            {
                "skills": ["zica", "bookkeeping"],
                "employment_type": "volunteer",
                "work_arrangement": "on_site",
            }
        )
        assert result.skills == ["zica", "bookkeeping"]
        assert result.employment_type is None
        assert result.work_arrangement == "on_site"

    def test_multi_job_array_uses_first_row(self):
        result = parse_llm_enrichment_payload(
            [
                {
                    "skills": ["masonry"],
                    "employment_type": "contract",
                    "work_arrangement": "on_site",
                },
                {"skills": ["ignored"], "employment_type": None, "work_arrangement": None},
            ]
        )
        assert result.skills == ["masonry"]
        assert result.employment_type == "contract"

    @pytest.mark.asyncio
    async def test_returns_empty_skills_on_api_error(self):
        with patch("app.services.job_enricher._client") as mock_client_factory:
            client = MagicMock()
            mock_client_factory.return_value = client
            client.chat.completions.create.side_effect = Exception("boom")

            result = await enrich_job(
                title="Engineer",
                company="Co",
                description="A" * 100,
            )
            assert result.skills == []
            assert result.employment_type is None

    def test_normalizes_skill_strings(self):
        data = JobEnrichment.model_validate(
            {
                "skills": ["  Python  ", "X" * 101, ""],
                "employment_type": None,
                "work_arrangement": None,
            }
        )
        assert data.skills == ["python"]
