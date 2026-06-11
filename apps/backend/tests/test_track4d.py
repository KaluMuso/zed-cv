"""Track 4d: multi-job splitter + deep-link enrichment."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.jobs import JobCreate, JobSource
from app.services.deep_link_enricher import (
    EnrichmentResult,
    enrich_from_source_url,
    enrich_job_row,
    extract_apply_from_html,
    job_needs_enrichment,
)
from app.services.job_splitter import (
    SplitJobItem,
    heuristic_is_multi_job,
    should_split_message,
    split_classification_to_jobs,
    split_items_to_job_creates,
)
from app.services.whatsapp_classifier import WhatsappJobClassification

MULTI_JOB_TEXT = (
    "Hiring at Tech Co Ltd, Lusaka:\n"
    "1) Software Engineer — Python, Django, 3+ years\n"
    "2) UX Designer — Figma, user research\n"
    "3) Account Manager — B2B sales, CRM\n"
    "Apply: jobs@techco.zm"
)

SINGLE_JOB_TEXT = (
    "Hiring: Software Engineer at Tech Co Ltd, Lusaka. "
    "Apply: jobs@techco.zm. Required: Python"
)


def _base_job_create(**kwargs) -> JobCreate:
    defaults = {
        "title": "Multi hire",
        "company": "Tech Co Ltd",
        "location": "Lusaka",
        "description": "Multiple roles listed in one WhatsApp post for Tech Co.",
        "apply_email": "jobs@techco.zm",
        "source": JobSource.scraper,
        "source_url": "whatsapp://channel/ch/msg-1",
    }
    defaults.update(kwargs)
    return JobCreate(**defaults)


class TestJobSplitter:
    def test_split_three_jobs_from_numbered_list(self):
        assert heuristic_is_multi_job(MULTI_JOB_TEXT) is True

    def test_split_skips_single_job_message(self):
        assert heuristic_is_multi_job(SINGLE_JOB_TEXT) is False
        classification = WhatsappJobClassification(
            is_job=True,
            title="Software Engineer",
            company="Tech Co Ltd",
            description=SINGLE_JOB_TEXT * 2,
            apply_email="jobs@techco.zm",
        )
        assert should_split_message(SINGLE_JOB_TEXT, classification) is False

    @pytest.mark.asyncio
    async def test_split_uses_llm_when_heuristics_fail(self):
        """Classifier is_multi_job triggers split even without numbered list."""
        subtle_multi = (
            "Tech Co is hiring a Backend Developer and a separate "
            "Frontend Developer role in Lusaka. Shared apply: hr@techco.zm"
        )
        classification = WhatsappJobClassification(
            is_job=True,
            is_multi_job=True,
            title="Tech Co hiring",
            company="Tech Co",
            description=subtle_multi,
            apply_email="hr@techco.zm",
        )
        items = [
            SplitJobItem(
                title="Backend Developer",
                description="Backend Developer at Tech Co in Lusaka.",
                skills=["python"],
            ),
            SplitJobItem(
                title="Frontend Developer",
                description="Frontend Developer at Tech Co in Lusaka.",
                skills=["react"],
            ),
        ]
        base = _base_job_create(description=subtle_multi)
        with patch(
            "app.services.job_splitter.split_message_with_llm",
            new_callable=AsyncMock,
            return_value=items,
        ):
            jobs = await split_classification_to_jobs(
                subtle_multi,
                classification,
                base,
                message_id="wa-99",
                supabase=None,
            )
        assert len(jobs) == 2
        assert jobs[0].title == "Backend Developer"
        assert jobs[0].apply_email == "jobs@techco.zm"
        assert jobs[1].company == "Tech Co Ltd"

    def test_split_items_assigns_distinct_whatsapp_ids(self):
        base = _base_job_create()
        items = [
            SplitJobItem(
                title="Software Engineer",
                description="Software Engineer role with Python and Django.",
                skills=["python"],
            ),
            SplitJobItem(
                title="UX Designer",
                description="UX Designer role with Figma and research skills.",
                skills=["figma"],
            ),
            SplitJobItem(
                title="Account Manager",
                description="Account Manager B2B sales role with CRM experience.",
                skills=["sales"],
            ),
        ]
        jobs = split_items_to_job_creates(items, base, message_id="msg-multi")
        assert len(jobs) == 3
        assert [j.title for j in jobs] == [
            "Software Engineer",
            "UX Designer",
            "Account Manager",
        ]


class TestDeepLinkEnricher:
    def test_enricher_finds_mailto_in_html(self):
        html = """
        <html><body>
          <a href="mailto:jobs@example.com?subject=Apply">Email us</a>
          <a href="https://example.com/careers/apply">Apply online</a>
        </body></html>
        """
        result = extract_apply_from_html(html, "https://example.com/jobs/123")
        assert result.apply_email == "jobs@example.com"

    def test_enricher_skips_already_populated(self):
        row = {
            "apply_url": "https://x.com/apply",
            "apply_email": None,
            "source_url": "https://example.com/jobs/1",
            "enrichment_attempted_at": None,
        }
        assert job_needs_enrichment(row) is False

    @pytest.mark.asyncio
    async def test_enricher_marks_attempted_to_prevent_loop(self):
        fake = MagicMock()
        table = MagicMock()
        fake.table.return_value = table
        chain = table.update.return_value
        chain.eq.return_value.execute.return_value = MagicMock(data=[{"id": "j1"}])

        row = {
            "apply_url": None,
            "apply_email": None,
            "source_url": "https://example.com/jobs/123",
            "enrichment_attempted_at": None,
        }
        with patch(
            "app.services.deep_link_enricher.enrich_from_source_url",
            new_callable=AsyncMock,
            return_value=EnrichmentResult(),
        ):
            updated = await enrich_job_row(fake, "j1", row)
        assert updated is False
        patch_body = table.update.call_args[0][0]
        assert "enrichment_attempted_at" in patch_body

    @pytest.mark.asyncio
    async def test_enrich_from_source_url_sets_enriched_email(self):
        html = "<html><body>Contact jobs@example.com for applications.</body></html>"
        with patch(
            "app.services.deep_link_enricher.fetch_page",
            new_callable=AsyncMock,
            return_value=(200, "text/html", html),
        ):
            result = await enrich_from_source_url("https://example.com/jobs/123")
        assert result.apply_email == "jobs@example.com"
        assert result.apply_source == "enriched"
