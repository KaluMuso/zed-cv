"""Tests for aggregator homepage vs listing source_url handling."""
from __future__ import annotations

from app.services.deep_link_parsers.base import (
    is_aggregator_site_root,
    sanitize_listing_source_url,
)


class TestAggregatorSiteRoot:
    def test_jobweb_homepage(self):
        assert is_aggregator_site_root("https://jobwebzambia.com/") is True
        assert is_aggregator_site_root("https://www.jobwebzambia.com") is True

    def test_jobweb_listing(self):
        url = "https://jobwebzambia.com/jobs/accounts-officer-teveta/"
        assert is_aggregator_site_root(url) is False
        assert sanitize_listing_source_url(url) == url

    def test_employer_url_unchanged(self):
        url = "https://careers.example.com/role/1"
        assert is_aggregator_site_root(url) is False
        assert sanitize_listing_source_url(url) == url

    def test_homepage_sanitized_to_none(self):
        assert sanitize_listing_source_url("https://jobwebzambia.com/") is None

    def test_uppercase_scheme_preserved(self):
        url = "HTTPS://WWW.ZIMBOJOBS.COM/JOBS/abc"
        assert sanitize_listing_source_url(url) == url
