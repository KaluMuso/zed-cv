"""Employer apply URL / email / phone extraction from aggregator listing HTML."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from app.services.deep_link_parsers import (
    ApplyContact,
    parse_with_registry,
    should_update_apply_url,
)
from app.services.deep_link_parsers.base import (
    AGGREGATOR_DOMAINS,
    is_aggregator_site_root,
    is_aggregator_url,
    normalize_hostname,
    sanitize_listing_source_url,
)

logger = logging.getLogger(__name__)

# Re-export for scripts/tests that import from this module.
AGGREGATOR_DOMAINS = AGGREGATOR_DOMAINS


def is_aggregator(url: str) -> bool:
    """True when URL hostname is a known Zambian job-board aggregator."""
    return is_aggregator_url(url)


@dataclass(frozen=True)
class ApplyContacts:
    apply_url: str | None = None
    apply_email: str | None = None
    contact_phone: str | None = None
    parser_confidence: float = 0.0
    parser_name: str | None = None


def _contact_to_apply_contacts(contact) -> ApplyContacts:
    return ApplyContacts(
        apply_url=contact.apply_url,
        apply_email=contact.apply_email,
        contact_phone=contact.contact_phone,
        parser_confidence=contact.parser_confidence,
        parser_name=contact.parser_name,
    )


def extract_apply_contacts_from_page(html: str, source_url: str) -> ApplyContacts:
    """Registry-first v2 parse, with generic fallback inside parse_with_registry."""
    if not (html or "").strip():
        return ApplyContacts()

    if not is_aggregator(source_url):
        from app.services.deep_link_parsers.generic_fallback import parse as generic_parse

        return _contact_to_apply_contacts(generic_parse(html, source_url))

    contact = parse_with_registry(html, source_url)
    return _contact_to_apply_contacts(contact)


def extract_real_apply_url(page_html: str, source_url: str) -> str | None:
    return extract_apply_contacts_from_page(page_html, source_url).apply_url


async def resolve_apply_contacts_from_aggregator_url(apply_url: str) -> ApplyContacts:
    url = sanitize_listing_source_url((apply_url or "").strip()) or ""
    if not url.startswith(("http://", "https://")) or not is_aggregator(url):
        return ApplyContacts()
    if is_aggregator_site_root(url):
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

    contact = parse_with_registry(body, url)
    if contact.redirect_url and (
        not contact.apply_url or is_aggregator(contact.apply_url or "")
    ):
        contact = await _follow_redirect_parse(contact.redirect_url, contact)
    return _contact_to_apply_contacts(contact)


async def _follow_redirect_parse(redirect_url: str, prior) -> object:
    from app.services.deep_link_enricher import fetch_page
    from app.services.deep_link_parsers import ApplyContact
    from app.services.deep_link_parsers.base import is_aggregator_url
    from app.services.deep_link_parsers.generic_fallback import parse as generic_parse

    try:
        status, ctype, body = await fetch_page(redirect_url)
    except Exception as exc:
        logger.info("redirect follow failed for %s: %s", redirect_url, exc)
        return prior
    if status >= 400 or not body:
        return prior
    if "html" not in ctype.lower() and "<html" not in body[:500].lower():
        return prior

    second = generic_parse(body, redirect_url)
    apply_url = second.apply_url
    if apply_url and is_aggregator_url(apply_url):
        apply_url = None
    merged_url = apply_url or prior.apply_url
    merged_email = prior.apply_email or second.apply_email
    merged_phone = prior.contact_phone or second.contact_phone
    confidence = max(prior.parser_confidence, second.parser_confidence)
    if merged_url and not is_aggregator_url(merged_url):
        confidence = max(confidence, 0.85)
    return ApplyContact(
        apply_url=merged_url,
        apply_email=merged_email,
        contact_phone=merged_phone,
        parser_confidence=confidence,
        parser_name=prior.parser_name,
    )


def merge_resolved_apply_contacts(
    job_data: dict,
    contacts: ApplyContacts,
    *,
    original_apply_url: str,
) -> None:
    contact = ApplyContact(
        apply_url=contacts.apply_url,
        apply_email=contacts.apply_email,
        contact_phone=contacts.contact_phone,
        parser_confidence=contacts.parser_confidence,
        parser_name=contacts.parser_name,
    )
    if contacts.apply_url and should_update_apply_url(
        contact, original_url=original_apply_url
    ):
        job_data["apply_url"] = contacts.apply_url
        job_data["apply_source"] = "enriched"
    elif contacts.apply_url and not is_aggregator(contacts.apply_url):
        job_data["apply_url"] = contacts.apply_url
        job_data["apply_source"] = "enriched"
    if contacts.apply_email and not job_data.get("apply_email"):
        job_data["apply_email"] = contacts.apply_email
    if contacts.contact_phone and not job_data.get("contact_phone"):
        job_data["contact_phone"] = contacts.contact_phone
    if not job_data.get("apply_url"):
        job_data.setdefault("apply_url", original_apply_url)
