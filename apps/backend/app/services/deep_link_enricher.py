"""Fetch source_url pages to discover apply_url / apply_email when missing."""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from app.services.deep_link_parsers import EnrichmentResult, parse_generic
from app.services.deep_link_router import detect_parser_name, parser_outcome, route_and_parse

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 10.0
_IMAGE_EXT_RE = re.compile(
    r"\.(?:png|jpe?g|gif|webp|bmp|svg|ico)(?:\?|$)", re.IGNORECASE
)

__all__ = [
    "EnrichmentResult",
    "enrich_from_source_url",
    "enrich_job_row",
    "extract_apply_from_html",
    "extract_linkedin_og",
    "fetch_page",
    "job_needs_enrichment",
    "reparse_job_row",
    "schedule_deep_link_enrichment",
]


def _is_image_source(source_url: str) -> bool:
    parsed = urlparse(source_url)
    path = (parsed.path or "").lower()
    if _IMAGE_EXT_RE.search(path):
        return True
    if path.endswith("/media") and "whatsapp" in (parsed.netloc or "").lower():
        return True
    return False


def extract_apply_from_html(html: str, page_url: str) -> EnrichmentResult:
    """Parse HTML for mailto, application links, and contact emails."""
    return parse_generic(html, page_url)


def extract_linkedin_og(html: str) -> EnrichmentResult:
    """Best-effort enrichment from LinkedIn public page OG tags (no auth)."""
    from app.services.deep_link_parsers import parse_linkedin

    return parse_linkedin(html, "https://www.linkedin.com/jobs/view/")


def _merge_results(primary: EnrichmentResult, secondary: EnrichmentResult) -> EnrichmentResult:
    return EnrichmentResult(
        apply_url=primary.apply_url or secondary.apply_url,
        apply_email=primary.apply_email or secondary.apply_email,
        apply_source=primary.apply_source or secondary.apply_source or "enriched",
        contact_phone=primary.contact_phone or secondary.contact_phone,
        parser=primary.parser or secondary.parser,
    )


async def fetch_page(url: str) -> tuple[int, str, str]:
    """Returns (status_code, content_type, body_text)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; ZedApplyBot/1.0; +https://zedapply.com)"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(
        timeout=_FETCH_TIMEOUT,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url, headers=headers)
        ctype = resp.headers.get("content-type", "")
        return resp.status_code, ctype, resp.text


async def _maybe_second_pass(
    result: EnrichmentResult,
    *,
    source_url: str,
) -> EnrichmentResult:
    """Follow LinkedIn employer-site redirect for a second parse pass."""
    redirect = (result.redirect_url or "").strip()
    if not redirect or result.apply_email:
        return result
    if redirect.rstrip("/") == source_url.rstrip("/"):
        return result
    try:
        status, ctype, body = await fetch_page(redirect)
    except Exception as exc:
        logger.info("deep_link second-pass fetch failed for %s: %s", redirect, exc)
        return result
    if status >= 400 or not body:
        return result
    if "html" not in ctype.lower() and "<html" not in body[:500].lower():
        return result
    second = parse_generic(body, redirect)
    merged = _merge_results(result, second)
    merged.parser = result.parser or "linkedin"
    return merged


async def enrich_from_source_url(source_url: str) -> EnrichmentResult:
    """Fetch source_url and extract apply contact info."""
    url = (source_url or "").strip()
    if not url or not url.startswith(("http://", "https://")):
        return EnrichmentResult()
    if _is_image_source(url):
        return EnrichmentResult()

    try:
        status, ctype, body = await fetch_page(url)
    except Exception as exc:
        logger.info("deep_link fetch failed for %s: %s", url, exc)
        return EnrichmentResult()

    if status >= 400 or not body:
        return EnrichmentResult()

    if "html" not in ctype.lower() and "<html" not in body[:500].lower():
        return EnrichmentResult()

    result = route_and_parse(body, url)
    if detect_parser_name(url) == "linkedin":
        result = await _maybe_second_pass(result, source_url=url)

    parser_name = result.parser or detect_parser_name(url)
    outcome = parser_outcome(result)
    logger.info(
        "deep_link parser=%s outcome=%s url=%s email=%s phone=%s",
        parser_name,
        outcome,
        url,
        bool(result.apply_email),
        bool(result.contact_phone),
    )
    return result


from app.services.deep_link_jobs import (  # noqa: E402
    enrich_job_row,
    job_needs_enrichment,
    reparse_job_row,
    schedule_deep_link_enrichment,
)
