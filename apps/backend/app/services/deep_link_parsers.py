"""Per-aggregator HTML parsers for deep-link apply contact discovery."""
from __future__ import annotations

import json
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel

from app.services.deep_link_phone import extract_phones_from_text


class EnrichmentResult(BaseModel):
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    apply_source: Optional[str] = None
    contact_phone: Optional[str] = None
    redirect_url: Optional[str] = None
    parser: Optional[str] = None

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
)
_EMAIL_LABEL_RE = re.compile(
    r"Email\s*:?\s*([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
    re.IGNORECASE,
)
_MAILTO_RE = re.compile(
    r"mailto:([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
    re.IGNORECASE,
)
_LINKEDIN_HOST_RE = re.compile(r"(^|\.)linkedin\.com$", re.IGNORECASE)


def _normalize_http_url(href: str, base_url: str) -> Optional[str]:
    href = (href or "").strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:")):
        return None
    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    return absolute[:2000]


def _dedupe_emails(emails: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in emails:
        addr = raw.strip().lower()
        if not addr or addr in seen:
            continue
        if not _EMAIL_RE.fullmatch(addr):
            continue
        seen.add(addr)
        ordered.append(addr)
    return ordered


def _emails_from_scope(scope: Tag | BeautifulSoup, raw_html: str) -> list[str]:
    emails: list[str] = []
    for a in scope.find_all("a", href=True):
        href = str(a.get("href") or "")
        if href.lower().startswith("mailto:"):
            addr = href.split(":", 1)[-1].split("?")[0].strip()
            if addr:
                emails.append(addr)
    text = scope.get_text(" ", strip=True)
    emails.extend(_EMAIL_LABEL_RE.findall(text))
    emails.extend(_EMAIL_RE.findall(text))
    for match in _MAILTO_RE.finditer(raw_html):
        emails.append(match.group(1))
    return _dedupe_emails(emails)


def _links_from_scope(scope: Tag | BeautifulSoup, page_url: str) -> list[str]:
    links: list[str] = []
    for a in scope.find_all("a", href=True):
        href = str(a.get("href") or "")
        normalized = _normalize_http_url(href, page_url)
        if normalized:
            links.append(normalized)
    for form in scope.find_all("form"):
        action = form.get("action")
        if action:
            normalized = _normalize_http_url(str(action), page_url)
            if normalized:
                links.append(normalized)
    return links


def _pick_apply_url(links: list[str]) -> Optional[str]:
    keywords = ("apply", "career", "vacanc", "job", "recruit", "submit")
    for url in links:
        lower = url.lower()
        if any(k in lower for k in keywords):
            return url
    return links[0] if links else None


def _build_result(
    emails: list[str],
    links: list[str],
    phones: list[str],
    *,
    parser: str,
    redirect_url: Optional[str] = None,
) -> EnrichmentResult:
    apply_email = emails[0] if emails else None
    apply_url = _pick_apply_url(links)
    contact_phone = phones[0] if phones else None

    if apply_email and apply_url:
        return EnrichmentResult(
            apply_email=apply_email,
            contact_phone=contact_phone,
            apply_source="enriched",
            parser=parser,
            redirect_url=redirect_url,
        )
    if apply_email:
        return EnrichmentResult(
            apply_email=apply_email,
            contact_phone=contact_phone,
            apply_source="enriched",
            parser=parser,
            redirect_url=redirect_url,
        )
    if apply_url:
        return EnrichmentResult(
            apply_url=apply_url,
            contact_phone=contact_phone,
            apply_source="enriched",
            parser=parser,
            redirect_url=redirect_url,
        )
    if contact_phone:
        return EnrichmentResult(
            contact_phone=contact_phone,
            parser=parser,
            redirect_url=redirect_url,
        )
    if redirect_url:
        return EnrichmentResult(parser=parser, redirect_url=redirect_url)
    return EnrichmentResult(parser=parser)


def parse_gozambiajobs(html: str, url: str) -> EnrichmentResult:
    """Parse gozambiajobs.com listing pages."""
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("motion.div.application-method, div.application-method")
    scope: Tag | BeautifulSoup = section if section else soup
    emails = _emails_from_scope(scope, html)
    links = _links_from_scope(scope, url)
    phones = extract_phones_from_text(scope.get_text(" ", strip=True))
    return _build_result(emails, links, phones, parser="gozambiajobs")


def parse_jobwebzambia(html: str, url: str) -> EnrichmentResult:
    """Parse jobwebzambia.com listing pages."""
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one(".job-application, section.job-application")
    scope: Tag | BeautifulSoup = section if section else soup
    emails = _emails_from_scope(scope, html)
    links = _links_from_scope(scope, url)
    phones = extract_phones_from_text(scope.get_text(" ", strip=True))
    return _build_result(emails, links, phones, parser="jobwebzambia")


def parse_jobsearchzm(html: str, url: str) -> EnrichmentResult:
    """Parse jobsearchzm.com listing pages."""
    soup = BeautifulSoup(html, "html.parser")
    emails: list[str] = []
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        label = (a.get_text(" ", strip=True) or "").lower()
        href = str(a.get("href") or "")
        if "apply" in label or "apply now" in label:
            if href.lower().startswith("mailto:"):
                addr = href.split(":", 1)[-1].split("?")[0].strip()
                if addr:
                    emails.append(addr)
            else:
                normalized = _normalize_http_url(href, url)
                if normalized:
                    links.append(normalized)
    emails.extend(_emails_from_scope(soup, html))
    links.extend(_links_from_scope(soup, url))
    phones = extract_phones_from_text(soup.get_text(" ", strip=True))
    return _build_result(_dedupe_emails(emails), links, phones, parser="jobsearchzm")


def _linkedin_employer_url(soup: BeautifulSoup) -> Optional[str]:
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        if prop in ("og:see_also", "og:url", "twitter:app:url:iphone"):
            content = (meta.get("content") or "").strip()
            if content and not _LINKEDIN_HOST_RE.search(urlparse(content).netloc or ""):
                return _normalize_http_url(content, content)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            org = item.get("hiringOrganization") or item.get("employer") or {}
            if isinstance(org, dict):
                site = org.get("sameAs") or org.get("url")
                if isinstance(site, str):
                    normalized = _normalize_http_url(site, site)
                    if normalized and not _LINKEDIN_HOST_RE.search(
                        urlparse(normalized).netloc or ""
                    ):
                        return normalized
    for a in soup.find_all("a", href=True):
        href = _normalize_http_url(str(a.get("href") or ""), "https://linkedin.com")
        if not href:
            continue
        host = (urlparse(href).netloc or "").lower()
        if host and not _LINKEDIN_HOST_RE.search(host):
            return href
    return None


def parse_linkedin(html: str, url: str) -> EnrichmentResult:
    """Parse LinkedIn job pages; surface employer site for second-pass fetch."""
    soup = BeautifulSoup(html, "html.parser")
    emails = _emails_from_scope(soup, html)
    redirect_url = _linkedin_employer_url(soup)
    phones = extract_phones_from_text(soup.get_text(" ", strip=True))
    return _build_result(
        emails,
        [],
        phones,
        parser="linkedin",
        redirect_url=redirect_url,
    )


def parse_generic(html: str, url: str) -> EnrichmentResult:
    """Fallback regex sweep across the whole document."""
    soup = BeautifulSoup(html, "html.parser")
    emails = _emails_from_scope(soup, html)
    links = _links_from_scope(soup, url)
    phones = extract_phones_from_text(soup.get_text(" ", strip=True))
    return _build_result(emails, links, phones, parser="generic")
