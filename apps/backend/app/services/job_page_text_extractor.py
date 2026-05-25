"""Extract plain job-posting text from scraped HTML (Tier 2 skills backfill)."""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

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

    # Prefer the longest substantive block (posting pages beat nav crumbs).
    best = max(candidates, key=len)
    host = (urlparse(page_url).netloc or "").lower()
    if host and host in best.lower() and len(best) < 400:
        # Very short meta-only snippets are weak; keep body if longer exists.
        if len(body_text) > len(best):
            best = body_text

    return best[:_MAX_CHARS]
