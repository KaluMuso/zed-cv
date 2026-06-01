"""Shared types and helpers for per-aggregator apply-contact parsers."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

AGGREGATOR_DOMAINS: frozenset[str] = frozenset(
    {
        "jobwebzambia.com",
        "gozambiajobs.com",
        "jobsearchzambia.com",
        "jobsearchzm.com",
        "careersinafrica.com",
        "everjobs.com.zm",
    }
)

CONFIDENCE_UPDATE_THRESHOLD = 0.7

_EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
)
_EMAIL_LABEL_RE = re.compile(
    r"Email\s*:?\s*([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
    re.IGNORECASE,
)

_NON_APPLY_HOST_FRAGMENTS: tuple[str, ...] = (
    "facebook.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "api.whatsapp.com",
    "wa.me",
    "t.me",
)


@dataclass(frozen=True)
class ApplyContact:
    apply_url: str | None = None
    apply_email: str | None = None
    contact_phone: str | None = None
    parser_confidence: float = 0.0
    parser_name: str | None = None
    redirect_url: str | None = None


ParserFn = Callable[[str, str], ApplyContact]


def normalize_hostname(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        return host[4:]
    return host


def is_aggregator_url(url: str) -> bool:
    if not (url or "").strip():
        return False
    host = normalize_hostname(url)
    if not host:
        return False
    if host in AGGREGATOR_DOMAINS:
        return True
    return any(host.endswith(f".{domain}") for domain in AGGREGATOR_DOMAINS)


# Index paths on aggregator sites — not usable as per-job listing URLs.
_AGGREGATOR_ROOT_PATHS = frozenset(
    {
        "",
        "jobs",
        "job",
        "vacancies",
        "careers",
        "index.php",
        "index.html",
    }
)


def is_aggregator_site_root(url: str) -> bool:
    """True when URL is an aggregator domain homepage or jobs index (no listing slug)."""
    if not (url or "").strip():
        return False
    if not is_aggregator_url(url):
        return False
    parsed = urlparse(url.strip())
    path = (parsed.path or "").strip("/")
    if not path:
        return True
    segments = [s for s in path.split("/") if s]
    if len(segments) == 1 and segments[0].lower() in _AGGREGATOR_ROOT_PATHS:
        return True
    return False


def sanitize_listing_source_url(url: str | None) -> str | None:
    """Drop aggregator homepages; keep per-job listing URLs for deep-link fetch."""
    if not url:
        return None
    cleaned = url.strip()
    lower = cleaned.lower()
    if not (lower.startswith("http://") or lower.startswith("https://")):
        return None
    if is_aggregator_site_root(cleaned):
        return None
    return cleaned


def is_non_apply_url(url: str) -> bool:
    host = normalize_hostname(url)
    if not host:
        return True
    lower = url.lower()
    if any(fragment in host for fragment in _NON_APPLY_HOST_FRAGMENTS):
        return True
    if "sharer" in lower or "share-offsite" in lower or "/send?text=" in lower:
        return True
    return False


def normalize_http_url(href: str, base_url: str) -> str | None:
    href = (href or "").strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    return absolute[:2000]


def dedupe_emails(emails: list[str]) -> list[str]:
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


def emails_from_scope(scope: Tag | BeautifulSoup, raw_html: str) -> list[str]:
    emails: list[str] = []
    for anchor in scope.find_all("a", href=True):
        href = str(anchor.get("href") or "")
        if href.lower().startswith("mailto:"):
            addr = href.split(":", 1)[-1].split("?")[0].strip()
            if addr:
                emails.append(addr)
    text = scope.get_text(" ", strip=True)
    emails.extend(_EMAIL_LABEL_RE.findall(text))
    emails.extend(_EMAIL_RE.findall(text))
    return dedupe_emails(emails)


def links_from_scope(scope: Tag | BeautifulSoup, page_url: str) -> list[str]:
    links: list[str] = []
    for anchor in scope.find_all("a", href=True):
        href = str(anchor.get("href") or "")
        normalized = normalize_http_url(href, page_url)
        if normalized:
            links.append(normalized)
    for form in scope.find_all("form"):
        action = form.get("action")
        if action:
            normalized = normalize_http_url(str(action), page_url)
            if normalized:
                links.append(normalized)
    return links


def pick_external_apply_url(
    links: list[str],
    page_url: str,
    *,
    prefer_keywords: bool = True,
) -> str | None:
    page_host = normalize_hostname(page_url)
    external = [
        url
        for url in links
        if not is_aggregator_url(url)
        and normalize_hostname(url) != page_host
        and not is_non_apply_url(url)
    ]
    if not external:
        return None
    if prefer_keywords:
        keywords = ("apply", "career", "vacanc", "job", "recruit", "submit", "workday")
        for url in external:
            lower = url.lower()
            if any(k in lower for k in keywords):
                return url
    return external[0]


def score_confidence(
    *,
    apply_url: str | None,
    apply_email: str | None,
    page_url: str,
    found_in_target_section: bool,
) -> float:
    """High when mailto or non-aggregator URL; low for aggregator-only links."""
    if apply_email:
        return 0.85 if found_in_target_section else 0.75
    if not apply_url:
        return 0.0
    if is_aggregator_url(apply_url):
        return 0.35
    host = normalize_hostname(apply_url)
    page_host = normalize_hostname(page_url)
    if host and host != page_host:
        base = 0.9 if found_in_target_section else 0.8
        lower = apply_url.lower()
        if any(k in lower for k in ("apply", "career", "vacanc", "recruit", "workday")):
            return min(0.95, base + 0.05)
        return base
    return 0.4


def build_contact(
    *,
    parser_name: str,
    page_url: str,
    emails: list[str],
    links: list[str],
    phones: list[str],
    found_in_target_section: bool,
    redirect_url: str | None = None,
) -> ApplyContact:
    apply_email = emails[0] if emails else None
    apply_url = pick_external_apply_url(links, page_url)
    contact_phone = phones[0] if phones else None
    confidence = score_confidence(
        apply_url=apply_url,
        apply_email=apply_email,
        page_url=page_url,
        found_in_target_section=found_in_target_section,
    )
    if redirect_url and not apply_url and confidence < CONFIDENCE_UPDATE_THRESHOLD:
        confidence = max(confidence, 0.55)
    return ApplyContact(
        apply_url=apply_url,
        apply_email=apply_email,
        contact_phone=contact_phone,
        parser_confidence=confidence,
        parser_name=parser_name,
        redirect_url=redirect_url,
    )
