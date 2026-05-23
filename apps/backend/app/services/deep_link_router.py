"""Route source URLs to the correct deep-link HTML parser."""
from __future__ import annotations

from typing import Callable
from urllib.parse import urlparse

from app.services.deep_link_parsers import (
    EnrichmentResult,
    parse_generic,
    parse_gozambiajobs,
    parse_jobsearchzm,
    parse_jobwebzambia,
    parse_linkedin,
)

_AGGREGATOR_HOSTS: dict[str, str] = {
    "gozambiajobs.com": "gozambiajobs",
    "www.gozambiajobs.com": "gozambiajobs",
    "jobwebzambia.com": "jobwebzambia",
    "www.jobwebzambia.com": "jobwebzambia",
    "jobsearchzm.com": "jobsearchzm",
    "www.jobsearchzm.com": "jobsearchzm",
}


def detect_parser_name(url: str) -> str:
    """Map source URL hostname to a parser name."""
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host in _AGGREGATOR_HOSTS:
        return _AGGREGATOR_HOSTS[host]
    if "linkedin.com" in host:
        return "linkedin"
    return "generic"


_PARSERS: dict[str, Callable[[str, str], EnrichmentResult]] = {
    "gozambiajobs": parse_gozambiajobs,
    "jobwebzambia": parse_jobwebzambia,
    "jobsearchzm": parse_jobsearchzm,
    "linkedin": parse_linkedin,
    "generic": parse_generic,
}


def route_and_parse(html: str, url: str) -> EnrichmentResult:
    """Detect aggregator from URL hostname and run the matching parser."""
    parser_name = detect_parser_name(url)
    parser_fn = _PARSERS.get(parser_name, parse_generic)
    result = parser_fn(html, url)
    if result.parser is None:
        result.parser = parser_name
    if not (result.apply_email or result.apply_url or result.contact_phone):
        if parser_name != "generic":
            fallback = parse_generic(html, url)
            if fallback.apply_email or fallback.apply_url or fallback.contact_phone:
                fallback.parser = parser_name
                return fallback
    return result


def parser_outcome(result: EnrichmentResult) -> str:
    """Classify parser result for telemetry."""
    has_email = bool(result.apply_email)
    has_phone = bool(result.contact_phone)
    if has_email and has_phone:
        return "found_both"
    if has_email:
        return "found_email"
    if has_phone:
        return "found_phone"
    return "failed"
