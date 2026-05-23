"""Tests for per-aggregator deep-link parsers."""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.deep_link_enricher import enrich_from_source_url
from app.services.deep_link_phone import extract_phones_from_text
from app.services.deep_link_router import detect_parser_name, route_and_parse
from app.services.deep_link_parsers import (
    parse_gozambiajobs,
    parse_jobwebzambia,
    parse_linkedin,
)


class TestParseGozambiajobs:
    def test_parse_gozambiajobs_finds_mailto(self):
        html = """
        <html><body>
          <div class="application-method">
            <p>Send your CV to:</p>
            <a href="mailto:careers@acme.co.zm?subject=Application">Apply by email</a>
            <form action="https://acme.co.zm/apply"><input type="submit"></form>
          </div>
        </body></html>
        """
        result = parse_gozambiajobs(html, "https://gozambiajobs.com/jobs/1")
        assert result.apply_email == "careers@acme.co.zm"
        assert result.parser == "gozambiajobs"


class TestParseJobwebzambia:
    def test_parse_jobwebzambia_finds_email_pattern(self):
        html = """
        <html><body>
          <section class="job-application">
            <p>Email: hr@zambianbank.co.zm</p>
            <p>Call +260 97 123 4567 for enquiries.</p>
          </section>
        </body></html>
        """
        result = parse_jobwebzambia(html, "https://jobwebzambia.com/job/42")
        assert result.apply_email == "hr@zambianbank.co.zm"
        assert result.contact_phone == "+260971234567"


class TestParseLinkedin:
    @pytest.mark.asyncio
    async def test_parse_linkedin_redirects_to_employer_site(self):
        html = """
        <html><head>
          <meta property="og:see_also" content="https://employer.example/careers" />
        </head><body>LinkedIn job view</body></html>
        """
        linkedin_result = parse_linkedin(html, "https://www.linkedin.com/jobs/view/123")
        assert linkedin_result.redirect_url == "https://employer.example/careers"

        employer_html = """
        <html><body>
          <a href="mailto:jobs@employer.example">Apply</a>
        </body></html>
        """
        with patch(
            "app.services.deep_link_enricher.fetch_page",
            new_callable=AsyncMock,
            side_effect=[
                (200, "text/html", html),
                (200, "text/html", employer_html),
            ],
        ):
            result = await enrich_from_source_url(
                "https://www.linkedin.com/jobs/view/123"
            )
        assert result.apply_email == "jobs@employer.example"
        assert result.parser == "linkedin"


class TestContactPhoneExtraction:
    def test_contact_phone_extraction_zambia_format(self):
        phones = extract_phones_from_text(
            "Contact 0971234567 or +260971234567. Salary K12500. Closing 2024."
        )
        assert phones == ["+260971234567"]
        assert extract_phones_from_text("Posted in 1990 and 2024") == []
        assert extract_phones_from_text("Package worth 12500 ngwee") == []


class TestAggregatorRouter:
    def test_aggregator_router_picks_right_parser(self):
        assert detect_parser_name("https://www.gozambiajobs.com/job/1") == "gozambiajobs"
        assert detect_parser_name("https://jobwebzambia.com/x") == "jobwebzambia"
        assert detect_parser_name("https://jobsearchzm.com/x") == "jobsearchzm"
        assert detect_parser_name("https://www.linkedin.com/jobs/view/1") == "linkedin"
        assert detect_parser_name("https://example.com/jobs/1") == "generic"

    def test_route_uses_jobsearchzm_apply_now_mailto(self):
        html = """
        <html><body>
          <a class="btn" href="mailto:recruit@company.zm">Apply Now</a>
        </body></html>
        """
        result = route_and_parse(html, "https://jobsearchzm.com/jobs/9")
        assert result.apply_email == "recruit@company.zm"
        assert result.parser == "jobsearchzm"

    def test_route_falls_back_to_generic(self):
        html = "<html><body>Reach us at fallback@jobs.zm</body></html>"
        result = route_and_parse(html, "https://gozambiajobs.com/jobs/2")
        assert result.apply_email == "fallback@jobs.zm"
