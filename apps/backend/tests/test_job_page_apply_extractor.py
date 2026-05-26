"""Tests for aggregator apply URL deep-link extraction."""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.job_page_text_extractor import (
    AGGREGATOR_DOMAINS,
    ApplyContacts,
    extract_apply_contacts_from_page,
    extract_real_apply_url,
    is_aggregator,
    merge_resolved_apply_contacts,
    resolve_apply_contacts_from_aggregator_url,
)


class TestIsAggregator:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://jobwebzambia.com/jobs/foo/", True),
            ("https://www.gozambiajobs.com/job/1", True),
            ("https://jobsearchzambia.com/listing", True),
            ("https://wd1.myworkdaysite.com/recruiting/abinbev/job", False),
            ("", False),
        ],
    )
    def test_is_aggregator(self, url: str, expected: bool) -> None:
        assert is_aggregator(url) is expected

    def test_aggregator_domains_include_prompt_list(self) -> None:
        for domain in (
            "jobwebzambia.com",
            "gozambiajobs.com",
            "jobsearchzambia.com",
            "careersinafrica.com",
            "everjobs.com.zm",
        ):
            assert domain in AGGREGATOR_DOMAINS


class TestExtractRealApplyUrl:
    def test_jobwebzambia_company_website_link(self) -> None:
        html = """
        <html><body>
          <section class="job-application">
            <a href="https://jobwebzambia.com/other">Other listing</a>
            <a href="https://wd1.myworkdaysite.com/recruiting/abinbev/job/123">
              Submit your CV on Company Website
            </a>
          </section>
        </body></html>
        """
        url = extract_real_apply_url(
            html, "https://jobwebzambia.com/jobs/ndola-ppm-manager-ab-inbev/"
        )
        assert url == "https://wd1.myworkdaysite.com/recruiting/abinbev/job/123"

    def test_skips_other_aggregator_links(self) -> None:
        html = """
        <html><body>
          <a href="https://gozambiajobs.com/jobs/2">Apply on company site</a>
          <a href="https://employer.example/apply">Apply Now</a>
        </body></html>
        """
        url = extract_real_apply_url(html, "https://jobwebzambia.com/jobs/x")
        assert url == "https://employer.example/apply"

    def test_method_of_application_click_here_link(self) -> None:
        """Save the Children MEAL Lead: external link under Method of Application."""
        html = """
        <html><body>
          <h1 class="how-to-apply">Method of Application</h1>
          <p>
            <a href="https://hcri.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/16569?utm_medium=jobboard&amp;utm_source=linkedin">
              Submit your CV and Application on Company Website : Click Here
            </a>
          </p>
        </body></html>
        """
        url = extract_real_apply_url(
            html,
            "https://jobwebzambia.com/jobs/monitoring-evaluation-accountability-learning-meal-lead-save-children/",
        )
        assert url is not None
        assert "oraclecloud.com" in url

    def test_method_of_application_email_without_link(self) -> None:
        html = """
        <html><body>
          <h2>How to Apply</h2>
          <p>Send your CV to careers@savechildren.zm before Friday.</p>
        </body></html>
        """
        contacts = extract_apply_contacts_from_page(
            html, "https://jobwebzambia.com/jobs/meal-lead/"
        )
        assert contacts.apply_email == "careers@savechildren.zm"
        assert contacts.apply_url is None

    def test_method_of_application_mailto(self) -> None:
        html = """
        <html><body>
          <h3>Application Instructions</h3>
          <a href="mailto:hr@employer.co.zm">Email your application</a>
        </body></html>
        """
        contacts = extract_apply_contacts_from_page(
            html, "https://jobwebzambia.com/jobs/x/"
        )
        assert contacts.apply_email == "hr@employer.co.zm"

    def test_extract_email_and_phone_from_parser(self) -> None:
        html = """
        <html><body>
          <section class="job-application">
            <p>Email: hr@zambianbank.co.zm</p>
            <p>Call +260 97 123 4567</p>
            <a href="https://bank.example/careers/apply">Apply on company site</a>
          </section>
        </body></html>
        """
        contacts = extract_apply_contacts_from_page(
            html, "https://jobwebzambia.com/job/42"
        )
        assert contacts.apply_url == "https://bank.example/careers/apply"
        assert contacts.apply_email == "hr@zambianbank.co.zm"
        assert contacts.contact_phone == "+260971234567"


class TestMergeResolvedApplyContacts:
    def test_keeps_aggregator_url_when_resolution_fails(self) -> None:
        job_data: dict = {"apply_url": "https://jobwebzambia.com/jobs/x"}
        merge_resolved_apply_contacts(
            job_data,
            ApplyContacts(),
            original_apply_url="https://jobwebzambia.com/jobs/x",
        )
        assert job_data["apply_url"] == "https://jobwebzambia.com/jobs/x"
        assert "apply_source" not in job_data

    def test_replaces_url_when_resolved(self) -> None:
        job_data: dict = {"apply_url": "https://jobwebzambia.com/jobs/x"}
        merge_resolved_apply_contacts(
            job_data,
            ApplyContacts(apply_url="https://employer.example/apply"),
            original_apply_url="https://jobwebzambia.com/jobs/x",
        )
        assert job_data["apply_url"] == "https://employer.example/apply"
        assert job_data["apply_source"] == "enriched"


class TestResolveApplyContactsFromAggregatorUrl:
    @pytest.mark.asyncio
    async def test_fetch_and_resolve(self) -> None:
        html = """
        <html><body>
          <a href="https://employer.example/apply-now">Apply Now</a>
        </body></html>
        """
        with patch(
            "app.services.deep_link_enricher.fetch_page",
            new_callable=AsyncMock,
            return_value=(200, "text/html", html),
        ):
            contacts = await resolve_apply_contacts_from_aggregator_url(
                "https://jobwebzambia.com/jobs/test"
            )
        assert contacts.apply_url == "https://employer.example/apply-now"

    @pytest.mark.asyncio
    async def test_non_aggregator_returns_empty(self) -> None:
        contacts = await resolve_apply_contacts_from_aggregator_url(
            "https://employer.example/apply"
        )
        assert contacts == ApplyContacts()
