"""Fetch source_url pages to discover apply_url / apply_email when missing."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 10.0
_EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
)
_IMAGE_EXT_RE = re.compile(
    r"\.(?:png|jpe?g|gif|webp|bmp|svg|ico)(?:\?|$)", re.IGNORECASE
)
_LINKEDIN_JOB_RE = re.compile(
    r"linkedin\.com/(?:jobs/view|posts)/", re.IGNORECASE
)


class EnrichmentResult(BaseModel):
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    apply_source: Optional[str] = None


def _is_image_source(source_url: str) -> bool:
    parsed = urlparse(source_url)
    path = (parsed.path or "").lower()
    if _IMAGE_EXT_RE.search(path):
        return True
    if path.endswith("/media") and "whatsapp" in (parsed.netloc or "").lower():
        return True
    return False


def _normalize_http_url(href: str, base_url: str) -> Optional[str]:
    href = (href or "").strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:")):
        return None
    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    return absolute[:2000]


def _pick_apply_url(links: list[str]) -> Optional[str]:
    keywords = ("apply", "career", "vacanc", "job", "recruit", "submit")
    for url in links:
        lower = url.lower()
        if any(k in lower for k in keywords):
            return url
    return links[0] if links else None


def extract_apply_from_html(html: str, page_url: str) -> EnrichmentResult:
    """Parse HTML for mailto, application links, and contact emails."""
    soup = BeautifulSoup(html, "html.parser")
    emails: list[str] = []
    links: list[str] = []

    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "")
        if href.lower().startswith("mailto:"):
            addr = href.split(":", 1)[-1].split("?")[0].strip()
            if addr and _EMAIL_RE.fullmatch(addr):
                emails.append(addr.lower())
            continue
        normalized = _normalize_http_url(href, page_url)
        if normalized:
            links.append(normalized)

    text = soup.get_text(" ", strip=True)
    for match in _EMAIL_RE.findall(text):
        emails.append(match.lower())

    apply_email = emails[0] if emails else None
    apply_url = _pick_apply_url(links)

    if apply_email and apply_url:
        return EnrichmentResult(apply_email=apply_email)
    if apply_email:
        return EnrichmentResult(apply_email=apply_email, apply_source="enriched")
    if apply_url:
        return EnrichmentResult(apply_url=apply_url, apply_source="enriched")
    return EnrichmentResult()


def extract_linkedin_og(html: str) -> EnrichmentResult:
    """Best-effort enrichment from LinkedIn public page OG tags (no auth)."""
    soup = BeautifulSoup(html, "html.parser")
    og_desc = ""
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        if prop in ("og:description", "description"):
            content = meta.get("content") or ""
            if len(content) > len(og_desc):
                og_desc = content
    emails = _EMAIL_RE.findall(og_desc)
    if emails:
        return EnrichmentResult(apply_email=emails[0].lower(), apply_source="enriched")
    return EnrichmentResult()


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

    if _LINKEDIN_JOB_RE.search(url):
        result = extract_linkedin_og(body)
        if result.apply_email or result.apply_url:
            return result

    return extract_apply_from_html(body, url)


def job_needs_enrichment(row: dict) -> bool:
    """Skip when apply fields populated or enrichment already attempted."""
    if row.get("apply_url") or row.get("apply_email"):
        return False
    if not row.get("source_url"):
        return False
    if row.get("enrichment_attempted_at"):
        return False
    return True


async def enrich_job_row(supabase: Any, job_id: str, row: dict) -> bool:
    """Fetch source_url + description body, update jobs.apply_* when found."""
    working = dict(row)
    from app.services.description_body_extractor import merge_description_extraction

    merge_description_extraction(working, working.get("description"))

    if not job_needs_enrichment(working) and not (
        working.get("apply_url") or working.get("apply_email")
    ):
        return False

    patch_desc: dict[str, Any] = {}
    if working.get("apply_email") and not row.get("apply_email"):
        patch_desc["apply_email"] = working["apply_email"]
        patch_desc["apply_source"] = working.get("apply_source") or "description_email"
    elif working.get("apply_url") and not row.get("apply_url"):
        patch_desc["apply_url"] = working["apply_url"]
        patch_desc["apply_source"] = working.get("apply_source") or "description_url"
    if patch_desc:
        supabase.table("jobs").update(patch_desc).eq("id", job_id).execute()
        row.update(patch_desc)

    if not job_needs_enrichment(row):
        return bool(patch_desc)

    source_url = str(row.get("source_url") or "")
    now = datetime.now(timezone.utc).isoformat()
    patch: dict[str, Any] = {"enrichment_attempted_at": now}

    try:
        result = await enrich_from_source_url(source_url)
    except Exception as exc:
        logger.warning("enrich_job_row %s failed: %s", job_id, exc)
        supabase.table("jobs").update(patch).eq("id", job_id).execute()
        return False

    updated = False
    if result.apply_email and not row.get("apply_email"):
        patch["apply_email"] = result.apply_email
        patch["apply_source"] = "enriched"
        updated = True
    elif result.apply_url and not row.get("apply_url"):
        patch["apply_url"] = result.apply_url
        patch["apply_source"] = "enriched"
        updated = True

    supabase.table("jobs").update(patch).eq("id", job_id).execute()
    return updated


def schedule_deep_link_enrichment(supabase: Any, job_id: str, row: dict) -> None:
    """Fire-and-forget enrichment after ingest (non-blocking)."""
    if not job_needs_enrichment(row):
        return

    async def _run() -> None:
        try:
            await enrich_job_row(supabase, job_id, row)
        except Exception:
            logger.warning(
                "background deep_link enrichment failed for %s",
                job_id,
                exc_info=True,
            )

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run())
    except RuntimeError:
        asyncio.run(_run())
