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
_APPLICATION_HEADING_RE = re.compile(
    r"method\s+of\s+application|how\s+to\s+apply|application\s+instructions",
    re.IGNORECASE,
)
_AGGREGATOR_HOSTS = frozenset(
    {
        "jobwebzambia.com",
        "gozambiajobs.com",
        "jobsearchzambia.com",
        "jobsearchzm.com",
        "careersinafrica.com",
        "everjobs.com.zm",
    }
)


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


def _link_host(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    return host[4:] if host.startswith("www.") else host


def _is_aggregator_url(url: str) -> bool:
    host = _link_host(url)
    if not host:
        return False
    if host in _AGGREGATOR_HOSTS:
        return True
    return any(host.endswith(f".{domain}") for domain in _AGGREGATOR_HOSTS)


def _is_non_apply_url(url: str) -> bool:
    lower = url.lower()
    host = _link_host(url)
    if any(
        frag in host
        for frag in (
            "facebook.com",
            "twitter.com",
            "x.com",
            "linkedin.com",
            "api.whatsapp.com",
            "wa.me",
        )
    ):
        return True
    return "sharer" in lower or "share-offsite" in lower or "/send?text=" in lower


def _pick_apply_url(links: list[str], page_url: str = "") -> Optional[str]:
    page_host = _link_host(page_url)
    external = [
        url
        for url in links
        if not _is_aggregator_url(url)
        and _link_host(url) != page_host
        and not _is_non_apply_url(url)
    ]
    keywords = ("apply", "career", "vacanc", "job", "recruit", "submit")
    for url in external:
        lower = url.lower()
        if any(k in lower for k in keywords):
            return url
    return external[0] if external else None


def _application_section_scopes(soup: BeautifulSoup) -> list[Tag | BeautifulSoup]:
    scopes: list[Tag | BeautifulSoup] = []
    legacy = soup.select_one(".job-application, section.job-application")
    if legacy is not None:
        scopes.append(legacy)
    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        title = heading.get_text(" ", strip=True) or ""
        if not _APPLICATION_HEADING_RE.search(title):
            continue
        block = soup.new_tag("div")
        block.append(heading)
        for sib in heading.next_siblings:
            if getattr(sib, "name", None) in ("h1", "h2", "h3", "h4"):
                break
            block.append(sib)
        scopes.append(block)
    return scopes


def _build_result(
    emails: list[str],
    links: list[str],
    phones: list[str],
    page_url: str,
    *,
    parser: str,
    redirect_url: Optional[str] = None,
) -> EnrichmentResult:
    apply_email = emails[0] if emails else None
    apply_url = _pick_apply_url(links, page_url)
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
    return _build_result(emails, links, phones, url, parser="gozambiajobs")


def parse_jobwebzambia(html: str, url: str) -> EnrichmentResult:
    """Parse jobwebzambia.com listing pages."""
    soup = BeautifulSoup(html, "html.parser")
    scopes = _application_section_scopes(soup)
    if not scopes:
        scopes = [soup]
    emails: list[str] = []
    links: list[str] = []
    phones: list[str] = []
    for scope in scopes:
        emails.extend(_emails_from_scope(scope, html))
        links.extend(_links_from_scope(scope, url))
        phones.extend(extract_phones_from_text(scope.get_text(" ", strip=True)))
    return _build_result(
        _dedupe_emails(emails),
        links,
        phones,
        url,
        parser="jobwebzambia",
    )


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
    return _build_result(_dedupe_emails(emails), links, phones, url, parser="jobsearchzm")


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
        url,
        parser="linkedin",
        redirect_url=redirect_url,
    )


def parse_generic(html: str, url: str) -> EnrichmentResult:
    """Fallback regex sweep across the whole document."""
    soup = BeautifulSoup(html, "html.parser")
    emails = _emails_from_scope(soup, html)
    links = _links_from_scope(soup, url)
    phones = extract_phones_from_text(soup.get_text(" ", strip=True))
    return _build_result(emails, links, phones, url, parser="generic")
