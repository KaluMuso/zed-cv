"""Extract plain job-posting text and employer apply links from scraped HTML."""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.services.job_apply_url_heuristics import (
    AGGREGATOR_DOMAINS,
    ApplyContacts,
    extract_apply_contacts_from_page,
    extract_real_apply_url,
    is_aggregator,
    merge_resolved_apply_contacts,
    resolve_apply_contacts_from_aggregator_url,
)

__all__ = [
    "AGGREGATOR_DOMAINS",
    "ApplyContacts",
    "extract_apply_contacts_from_page",
    "extract_page_text_for_description",
    "extract_real_apply_url",
    "is_aggregator",
    "is_form_gated_page",
    "merge_resolved_apply_contacts",
    "resolve_apply_contacts_from_aggregator_url",
]

_MAX_CHARS = 12_000
_MIN_USEFUL_LEN = 80

_JOB_CONTAINER_SELECTORS: tuple[str, ...] = (
    "article",
    "main",
    "[class*='job-description']",
    "[class*='job_description']",
    "[class*='job-detail']",
    "[class*='vacancy']",
    "[id*='job-description']",
    "[id*='job_description']",
)

_NOISE_TAGS = ("script", "style", "nav", "footer", "header", "noscript", "svg")


def _meta_content(soup: BeautifulSoup, *, prop: str | None = None, name: str | None = None) -> str:
    if prop:
        tag = soup.find("meta", property=prop)
    else:
        tag = soup.find("meta", attrs={"name": name})
    if not tag:
        return ""
    content = tag.get("content")
    return str(content).strip() if content else ""


def _text_from_nodes(nodes: Iterable) -> str:
    chunks: list[str] = []
    for node in nodes:
        if node is None:
            continue
        text = node.get_text("\n", strip=True) if hasattr(node, "get_text") else ""
        if text:
            chunks.append(text)
    return "\n\n".join(chunks)


def _collapse_whitespace(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


_FORM_HOST_PATTERNS: tuple[str, ...] = (
    "docs.google.com",
    "forms.gle",
    "typeform.com",
    "jotform.com",
    "surveymonkey.com",
    "microsoft.com/forms",
    "forms.office.com",
    "airtable.com",
    "paperform.co",
    "tally.so",
    "wufoo.com",
    "cognito.com",
    "formstack.com",
)

_FORM_TEXT_SIGNALS: tuple[str, ...] = (
    "fill out this form",
    "fill in this form",
    "complete this form",
    "submit this form",
    "this form is required",
    "google forms",
    "survey monkey",
)


def is_form_gated_page(url: str, html: str = "") -> bool:
    """Return True when a page is primarily a fill-out form (Google Forms etc.).

    Such pages rarely contain enough structured job-description text for the
    LLM to extract meaningful roles.  Callers should skip or warn the user.
    """
    lower_url = (url or "").lower()
    # Fast-path on URL alone
    for pattern in _FORM_HOST_PATTERNS:
        if pattern in lower_url:
            return True
    # Slow-path: inspect page text for clear form signals
    if html:
        lower_body = html[:4000].lower()
        matches = sum(1 for sig in _FORM_TEXT_SIGNALS if sig in lower_body)
        if matches >= 2:
            return True
    return False


def extract_page_text_for_description(html: str, page_url: str = "") -> str:
    """Best-effort posting body for LLM enrichment after a deep-link fetch."""
    if not (html or "").strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for tag_name in _NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    candidates: list[str] = []
    for meta in (
        _meta_content(soup, prop="og:description"),
        _meta_content(soup, name="description"),
    ):
        if len(meta) >= _MIN_USEFUL_LEN:
            candidates.append(meta)

    for selector in _JOB_CONTAINER_SELECTORS:
        nodes = soup.select(selector)
        if nodes:
            block = _collapse_whitespace(_text_from_nodes(nodes))
            if len(block) >= _MIN_USEFUL_LEN:
                candidates.append(block)

    body = soup.body or soup
    body_text = _collapse_whitespace(body.get_text("\n", strip=True))
    if len(body_text) >= _MIN_USEFUL_LEN:
        candidates.append(body_text)

    if not candidates:
        return ""

    best = max(candidates, key=len)
    host = (urlparse(page_url).netloc or "").lower()
    if host and host in best.lower() and len(best) < 400:
        if len(body_text) > len(best):
            best = body_text

    return best[:_MAX_CHARS]
