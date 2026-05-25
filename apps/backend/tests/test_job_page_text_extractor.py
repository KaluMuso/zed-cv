"""Tests for HTML → description text used in Tier 2 skills backfill."""
from __future__ import annotations

from app.services.job_page_text_extractor import extract_page_text_for_description


def test_og_description_preferred_when_substantial():
    html = """
    <html><head>
      <meta property="og:description" content="We need an electrical engineer with ZICA registration and PLC experience for our Lusaka site." />
    </head><body><p>Short nav</p></body></html>
    """
    text = extract_page_text_for_description(html, "https://example.com/jobs/1")
    assert "electrical engineer" in text
    assert len(text) >= 80


def test_job_container_beats_tiny_meta():
    html = """
    <html><body>
      <main class="job-description">
        <p>Responsibilities include financial reporting, budgeting, and Sage Pastel.</p>
        <p>Requirements: ACCA or ZICA, 3+ years in audit.</p>
      </main>
    </body></html>
    """
    text = extract_page_text_for_description(html, "https://careers.example.com/vacancy")
    assert "Sage Pastel" in text
    assert "ACCA" in text


def test_empty_html_returns_empty():
    assert extract_page_text_for_description("", "https://x.com") == ""
