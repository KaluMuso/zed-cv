"""Unit tests for job ingest quality pipeline."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import job_quality


class TestHasValidApplyPath:
    def test_linkedin_url_alone_valid(self):
        ok, reason = job_quality.has_valid_apply_path(
            {"apply_url": "https://www.linkedin.com/jobs/view/123"}
        )
        assert ok is True
        assert reason is None

    def test_jobwebzambia_url_alone_invalid(self):
        ok, reason = job_quality.has_valid_apply_path(
            {"apply_url": "https://www.jobwebzambia.com/job/123"}
        )
        assert ok is False
        assert reason == "aggregator_only_no_contact"

    def test_jobwebzambia_url_plus_valid_email(self):
        ok, reason = job_quality.has_valid_apply_path(
            {
                "apply_url": "https://www.jobwebzambia.com/job/123",
                "apply_email": "hr@employer.co.zm",
            }
        )
        assert ok is True

    def test_jobwebzambia_url_plus_valid_zm_phone(self):
        ok, reason = job_quality.has_valid_apply_path(
            {
                "apply_url": "https://gozambiajobs.com/job/1",
                "contact_phone": "+260971715270",
            }
        )
        assert ok is True

    def test_zimbabwe_number_invalid(self):
        ok, reason = job_quality.has_valid_apply_path(
            {"contact_phone": "+263771234567"}
        )
        assert ok is False

    def test_non_standard_zm_prefix_invalid(self):
        ok, reason = job_quality.has_valid_apply_path(
            {"contact_phone": "+260813252760"}
        )
        assert ok is False

    def test_standard_mtn_prefix_valid(self):
        ok, reason = job_quality.has_valid_apply_path(
            {"contact_phone": "+260971715270"}
        )
        assert ok is True


class TestApplyPathIngestGate:
    def _run_ingest_quality(self, job_data: dict) -> dict:
        job_quality.apply_ingest_quality_to_job_data(
            job_data,
            original_contact_phone=job_data.get("contact_phone"),
        )
        return job_data

    def test_aggregator_with_source_url_pending_enrich(self):
        data = {
            "title": "Clerk",
            "description": "x" * 350,
            "source_url": "https://www.jobwebzambia.com/job/clerk-1",
            "apply_url": "https://www.jobwebzambia.com/job/clerk-1",
        }
        out = self._run_ingest_quality(data)
        assert out["is_active"] is False
        assert out["deactivation_reason"] == "no_valid_apply_path_pending_enrich"

    def test_aggregator_without_source_url_terminal(self):
        """No listing URL to deep-enrich — terminal deactivation."""
        data = {
            "title": "Clerk",
            "description": "x" * 350,
            "apply_url": None,
            "source_url": None,
        }
        out = self._run_ingest_quality(data)
        assert out["is_active"] is False
        assert out["deactivation_reason"] == "no_valid_apply_path_no_source"

    def test_clears_stale_apply_path_deactivation_when_email_present(self):
        data = {
            "title": "HR Officer",
            "description": "x" * 350,
            "source_url": "https://www.jobwebzambia.com/jobs/hr-officer/",
            "apply_url": "https://www.jobwebzambia.com/jobs/hr-officer/",
            "apply_email": "careers@karibaharvest.com",
            "deactivation_reason": "no_valid_apply_path_after_enrich",
            "is_active": False,
        }
        out = self._run_ingest_quality(data)
        assert out.get("deactivation_reason") is None

    def test_valid_email_not_blocked_by_apply_path_gate(self):
        from app.services.job_publication import apply_contact_activation

        data = {
            "title": "Clerk",
            "description": "x" * 350,
            "source_url": "https://www.jobwebzambia.com/job/clerk-1",
            "apply_url": "https://www.jobwebzambia.com/job/clerk-1",
            "apply_email": "careers@company.co.zm",
        }
        out = self._run_ingest_quality(data)
        assert out.get("deactivation_reason") != "no_valid_apply_path_pending_enrich"
        assert out.get("deactivation_reason") != "no_valid_apply_path_no_source"
        apply_contact_activation(out)
        if out.get("deactivation_reason"):
            out["is_active"] = False
        assert out.get("is_active") is True


class TestValidateSourceUrl:
    def test_missing_source_url(self):
        ok, reason = job_quality.validate_source_url(None, "https://employer.com/apply")
        assert ok is False
        assert reason == "missing_source_url"

    def test_aggregator_homepage_rejected(self):
        ok, reason = job_quality.validate_source_url(
            "https://www.jobwebzambia.com/", None
        )
        assert ok is False
        assert reason == "source_url_is_aggregator_homepage:jobwebzambia.com"

    def test_aggregator_listing_url_accepted(self):
        ok, reason = job_quality.validate_source_url(
            "https://www.gozambiajobs.com/job/accounts-officer-123", None
        )
        assert ok is True
        assert reason is None

    def test_employer_url_accepted(self):
        ok, reason = job_quality.validate_source_url(
            "https://careers.savethechildren.net/job/1", None
        )
        assert ok is True
        assert reason is None


class TestNormalizeContactPhone:
    def test_mtn_valid(self):
        assert job_quality.normalize_contact_phone("+260 97 123 4567") == "+260971234567"

    def test_invalid_prefix_cleared(self):
        assert job_quality.normalize_contact_phone("+260813252760") is None

    def test_empty(self):
        assert job_quality.normalize_contact_phone(None) is None


class TestDescriptionQualityOk:
    def test_thin_with_ats_rejected(self):
        ok, reason = job_quality.description_quality_ok(
            "Apply online",
            "https://company.myworkdayjobs.com/en-US/job/123",
        )
        assert ok is False
        assert "thin_description_with_ats_link" in (reason or "")

    def test_thin_without_ats_accepted(self):
        ok, reason = job_quality.description_quality_ok("Short ad", None)
        assert ok is True


class TestStripScraperMetadata:
    def test_removes_footer_lines(self):
        raw = "\n".join(
            [
                "Key responsibilities",
                "• Sell products",
                "First Posted: 2024-01-01",
                "Scraped from LinkedIn",
            ]
        )
        assert job_quality.strip_scraper_metadata(raw) == "\n".join(
            ["Key responsibilities", "• Sell products"]
        )

    def test_collapses_extra_blank_lines(self):
        raw = "Role summary\n\n\nScraped from gozambiajobs.com"
        assert job_quality.strip_scraper_metadata(raw) == "Role summary"


class TestNormalizeDescriptionMarkdown:
    SEC_RAW = """JOB PURPOSE
Provide security services across Lusaka sites.

RESPONSIBILITIES
 Patrol premises and write incident reports.

REQUIREMENTS
 Grade 12 and valid driver's licence.

HOW TO APPLY
 Email CV to careers@sec.co.zm before Friday."""

    ZAMFRESH_RAW = """DESCRIPTION
Zamfresh Limited seeks a Sales Representative in Lusaka.

QUALIFICATIONS
 Diploma in Marketing and 2 years FMCG experience.

BENEFITS
 Transport allowance and medical cover."""

    ZCAS_RAW = """SUMMARY
ZCAS University invites applications for a Lecturer in Accounting.

KEY DUTIES
 Deliver lectures and supervise student research.

BENEFITS
 Pension scheme and annual leave."""

    def test_sec_headers_normalized(self):
        md = job_quality.normalize_description_markdown(self.SEC_RAW)
        assert "## Job purpose" in md
        assert "## Responsibilities" in md
        assert "## Requirements" in md
        assert "## How to apply" in md
        assert job_quality.normalize_description_markdown(md) == md

    def test_zamfresh_headers_normalized(self):
        md = job_quality.normalize_description_markdown(self.ZAMFRESH_RAW)
        assert "## Job purpose" in md
        assert "Zamfresh" in md

    def test_zcas_headers_normalized(self):
        md = job_quality.normalize_description_markdown(self.ZCAS_RAW)
        assert "## Responsibilities" in md
        assert "## Benefits" in md


class TestExtractSections:
    def test_splits_h2_sections(self):
        md = """## Responsibilities
Line one

## Requirements
Line two"""
        sections = job_quality.extract_sections(md)
        assert sections["section_responsibilities"] == "Line one"
        assert sections["section_requirements"] == "Line two"


class TestSplitMultiRoleListing:
    @pytest.mark.asyncio
    async def test_single_role_unchanged(self):
        job = {"title": "Accountant", "description": "We need an accountant." * 5}
        out = await job_quality.split_multi_role_listing(job, None)
        assert out == [job]

    @pytest.mark.asyncio
    async def test_multi_role_llm_split(self):
        job = {
            "title": "Multiple positions: Driver and Clerk",
            "company": "ACME",
            "description": "1. DRIVER\nDrive fleet.\n\n2. CLERK\nFile papers." * 3,
            "source_url": "https://employer.com/jobs",
        }
        mock_client = MagicMock()
        payload = [
            {
                "title": "Driver",
                "description": "Drive fleet vehicles daily.",
                "skills_required": ["driving"],
                "requirements": ["valid licence"],
            },
            {
                "title": "Clerk",
                "description": "Maintain filing and records.",
                "skills_required": ["ms office"],
                "requirements": ["grade 12"],
            },
        ]

        with patch(
            "app.services.job_quality._call_split_llm",
            new_callable=AsyncMock,
            return_value=[job_quality.SplitRoleItem.model_validate(x) for x in payload],
        ):
            out = await job_quality.split_multi_role_listing(job, mock_client)

        assert len(out) == 2
        assert out[0]["title"] == "Driver"
        assert out[1]["title"] == "Clerk"
        assert out[0]["parent_listing_signature"] == out[1]["parent_listing_signature"]
