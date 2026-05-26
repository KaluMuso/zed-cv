"""Employer apply URL / email / phone extraction from aggregator listing HTML."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

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

_NON_APPLY_HOST_FRAGMENTS: tuple[str, ...] = (
    "facebook.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "api.whatsapp.com",
    "wa.me",
    "t.me",
)

_LINK_TEXT_KEYWORDS: tuple[str, ...] = (
    "company website",
    "company site",
    "apply on company",
    "submit your cv",
    "submit cv",
    "submit your application",
    "click here",
    "apply now",
    "apply online",
    "apply here",
    "apply",
)

_APPLICATION_HEADING_RE = re.compile(
    r"method\s+of\s+application|how\s+to\s+apply|application\s+instructions",
    re.IGNORECASE,
)

_EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
)

_URL_PATH_KEYWORDS: tuple[str, ...] = (
    "apply",
    "career",
    "vacanc",
    "recruit",
    "job",
    "workday",
    "myworkday",
)


def _normalize_hostname(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        return host[4:]
    return host


def is_aggregator(url: str) -> bool:
    """True when URL hostname is a known Zambian job-board aggregator."""
    if not (url or "").strip():
        return False
    host = _normalize_hostname(url)
    if not host:
        return False
    if host in AGGREGATOR_DOMAINS:
        return True
    return any(host.endswith(f".{domain}") for domain in AGGREGATOR_DOMAINS)


def _is_non_apply_url(url: str) -> bool:
    host = _normalize_hostname(url)
    if not host:
        return True
    lower = url.lower()
    if any(fragment in host for fragment in _NON_APPLY_HOST_FRAGMENTS):
        return True
    if "sharer" in lower or "share-offsite" in lower or "/send?text=" in lower:
        return True
    return False


def _normalize_http_url(href: str, base_url: str) -> str | None:
    href = (href or "").strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    return absolute[:2000]


@dataclass(frozen=True)
class ApplyContacts:
    apply_url: str | None = None
    apply_email: str | None = None
    contact_phone: str | None = None


def _score_apply_anchor(
    link_text: str,
    target_url: str,
    aggregator_host: str,
    *,
    in_application_section: bool = False,
) -> int:
    host = _normalize_hostname(target_url)
    if (
        not host
        or host == aggregator_host
        or is_aggregator(target_url)
        or _is_non_apply_url(target_url)
    ):
        return -1
    score = 0
    lower_text = link_text.lower()
    lower_url = target_url.lower()
    if "company website" in lower_text or "company site" in lower_text:
        score += 30
    if any(kw in lower_text for kw in _LINK_TEXT_KEYWORDS):
        score += 15
    if any(kw in lower_url for kw in _URL_PATH_KEYWORDS):
        score += 8
    if lower_text.strip() in ("apply", "apply now", "apply here"):
        score += 5
    if in_application_section and "click here" in lower_text:
        score += 12
    if in_application_section and score == 0:
        score = 3
    return score


def _nodes_in_application_section(heading) -> list:
    nodes: list = [heading]
    for sib in heading.next_siblings:
        if getattr(sib, "name", None) in ("h1", "h2", "h3", "h4"):
            break
        nodes.append(sib)
    return nodes


def _application_section_nodes(soup: BeautifulSoup) -> list[list]:
    sections: list[list] = []
    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        title = heading.get_text(" ", strip=True) or ""
        if not _APPLICATION_HEADING_RE.search(title):
            continue
        sections.append(_nodes_in_application_section(heading))
    legacy = soup.select_one(".job-application, section.job-application")
    if legacy is not None:
        sections.append([legacy])
    return sections


def _first_email_in_text(text: str) -> str | None:
    for match in _EMAIL_RE.finditer(text):
        addr = match.group(0).strip().lower()
        if addr and not addr.endswith((".png", ".jpg", ".gif")):
            return addr
    return None


def _extract_contacts_from_application_sections(
    html: str, page_url: str
) -> ApplyContacts:
    soup = BeautifulSoup(html, "html.parser")
    aggregator_host = _normalize_hostname(page_url)
    from app.services.deep_link_phone import extract_phones_from_text

    best_url: str | None = None
    best_score = -1
    apply_email: str | None = None
    contact_phone: str | None = None
    section_text_parts: list[str] = []

    for nodes in _application_section_nodes(soup):
        for node in nodes:
            if not hasattr(node, "find_all"):
                text = str(node).strip()
                if text:
                    section_text_parts.append(text)
                continue
            section_text_parts.append(node.get_text(" ", strip=True))
            for anchor in node.find_all("a", href=True):
                href = str(anchor.get("href") or "")
                lower_href = href.lower()
                text = anchor.get_text(" ", strip=True) or ""
                if lower_href.startswith("mailto:"):
                    addr = href.split(":", 1)[-1].split("?")[0].strip().lower()
                    if addr and not apply_email:
                        apply_email = addr
                    continue
                if lower_href.startswith("tel:"):
                    phones = extract_phones_from_text(href.split(":", 1)[-1].strip())
                    if phones and not contact_phone:
                        contact_phone = phones[0]
                    continue
                normalized = _normalize_http_url(href, page_url)
                if not normalized:
                    continue
                score = _score_apply_anchor(
                    text, normalized, aggregator_host, in_application_section=True
                )
                if score > best_score:
                    best_score = score
                    best_url = normalized

    combined = " ".join(section_text_parts)
    if not apply_email:
        apply_email = _first_email_in_text(combined)
    if not contact_phone:
        phones = extract_phones_from_text(combined)
        if phones:
            contact_phone = phones[0]

    if best_url and best_score >= 0:
        return ApplyContacts(
            apply_url=best_url,
            apply_email=apply_email,
            contact_phone=contact_phone,
        )
    return ApplyContacts(apply_email=apply_email, contact_phone=contact_phone)


def _heuristic_external_apply_url(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    aggregator_host = _normalize_hostname(page_url)
    best_url: str | None = None
    best_score = -1
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "")
        normalized = _normalize_http_url(href, page_url)
        if not normalized:
            continue
        text = anchor.get_text(" ", strip=True) or ""
        score = _score_apply_anchor(text, normalized, aggregator_host)
        if score > best_score:
            best_score = score
            best_url = normalized
    if best_url and best_score > 0:
        return best_url
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "")
        normalized = _normalize_http_url(href, page_url)
        if not normalized:
            continue
        host = _normalize_hostname(normalized)
        if (
            host
            and host != aggregator_host
            and not is_aggregator(normalized)
            and not _is_non_apply_url(normalized)
        ):
            lower = normalized.lower()
            if any(kw in lower for kw in _URL_PATH_KEYWORDS):
                return normalized
    return None


def extract_apply_contacts_from_page(html: str, source_url: str) -> ApplyContacts:
    if not (html or "").strip():
        return ApplyContacts()

    from app.services.deep_link_router import route_and_parse

    parsed = route_and_parse(html, source_url) if is_aggregator(source_url) else None
    section_contacts = (
        _extract_contacts_from_application_sections(html, source_url)
        if is_aggregator(source_url)
        else ApplyContacts()
    )
    heuristic_url = _heuristic_external_apply_url(html, source_url)

    apply_url = (
        section_contacts.apply_url
        or heuristic_url
        or (
            parsed.apply_url
            if parsed and parsed.apply_url and not is_aggregator(parsed.apply_url)
            else None
        )
    )
    apply_email = section_contacts.apply_email or (parsed.apply_email if parsed else None)
    contact_phone = section_contacts.contact_phone or (
        parsed.contact_phone if parsed else None
    )
    return ApplyContacts(
        apply_url=apply_url,
        apply_email=apply_email,
        contact_phone=contact_phone,
    )


def extract_real_apply_url(page_html: str, source_url: str) -> str | None:
    return extract_apply_contacts_from_page(page_html, source_url).apply_url


async def resolve_apply_contacts_from_aggregator_url(apply_url: str) -> ApplyContacts:
    url = (apply_url or "").strip()
    if not url.startswith(("http://", "https://")) or not is_aggregator(url):
        return ApplyContacts()

    from app.services.deep_link_enricher import fetch_page

    try:
        status, ctype, body = await fetch_page(url)
    except Exception as exc:
        logger.info("aggregator apply fetch failed for %s: %s", url, exc)
        return ApplyContacts()

    if status >= 400 or not body:
        return ApplyContacts()
    if "html" not in ctype.lower() and "<html" not in body[:500].lower():
        return ApplyContacts()
    return extract_apply_contacts_from_page(body, url)


def merge_resolved_apply_contacts(
    job_data: dict,
    contacts: ApplyContacts,
    *,
    original_apply_url: str,
) -> None:
    if contacts.apply_url:
        job_data["apply_url"] = contacts.apply_url
        job_data["apply_source"] = "enriched"
    if contacts.apply_email and not job_data.get("apply_email"):
        job_data["apply_email"] = contacts.apply_email
    if contacts.contact_phone and not job_data.get("contact_phone"):
        job_data["contact_phone"] = contacts.contact_phone
    if not contacts.apply_url:
        job_data.setdefault("apply_url", original_apply_url)
