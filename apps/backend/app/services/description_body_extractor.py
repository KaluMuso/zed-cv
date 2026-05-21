"""Extract apply_email / apply_url / contact_phone from job description plain text."""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from app.services.deep_link_enricher import EnrichmentResult

_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
# +260 97 123 4567 | +260971234567 | 097-123-4567 | 0971234567
_PHONE_RE = re.compile(
    r"(?:"
    r"\+260[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{4}"
    r"|\+260\d{9}"
    r"|0[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{4}"
    r"|0\d{9}"
    r")",
    re.IGNORECASE,
)

_RECRUITMENT_HINTS = ("recruit", "career", "jobs", "apply", "hr", "talent", "hiring")
_GENERIC_LOCAL = frozenset(
    {"info", "hello", "contact", "admin", "support", "enquiries", "enquiry", "office"}
)

_ZEDAPPLY_HOSTS = ("zedapply.com", "zedcv.com", "zed-cv.vercel.app")


def _is_generic_email(email: str) -> bool:
    local = email.split("@", 1)[0].lower()
    return local in _GENERIC_LOCAL


def _is_recruitment_flavored(email: str) -> bool:
    blob = email.lower()
    return any(h in blob for h in _RECRUITMENT_HINTS)


def _pick_email(candidates: list[str]) -> Optional[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in candidates:
        addr = raw.strip().lower()
        if not addr or addr in seen:
            continue
        seen.add(addr)
        ordered.append(addr)

    recruitment = [e for e in ordered if _is_recruitment_flavored(e) and not _is_generic_email(e)]
    if recruitment:
        return recruitment[0]

    non_generic = [e for e in ordered if not _is_generic_email(e)]
    if non_generic:
        return non_generic[0]

    return ordered[0] if ordered else None


def _is_blocked_url(url: str) -> bool:
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:
        return True
    return any(z in host for z in _ZEDAPPLY_HOSTS)


def _pick_url(urls: list[str]) -> Optional[str]:
    for url in urls:
        cleaned = url.rstrip(".,;)")
        if cleaned and not _is_blocked_url(cleaned):
            return cleaned[:2000]
    return None


def normalize_zambian_phone(raw: str) -> Optional[str]:
    """Normalize a matched phone string to E.164 +260XXXXXXXXX."""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("260") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+260{digits[1:]}"
    return None


def extract_phone_from_description(description: str | None) -> Optional[str]:
    """Return the first valid Zambian mobile number in description text."""
    text = (description or "").strip()
    if not text:
        return None
    for match in _PHONE_RE.finditer(text):
        normalized = normalize_zambian_phone(match.group(0))
        if normalized:
            return normalized
    return None


def extract_apply_from_description(description: str | None) -> EnrichmentResult:
    """Scan description body for emails and URLs when apply fields are empty."""
    text = (description or "").strip()
    if not text:
        return EnrichmentResult()

    emails = _EMAIL_RE.findall(text)
    urls = _URL_RE.findall(text)

    apply_email = _pick_email(emails)
    apply_url = _pick_url(urls)
    contact_phone = extract_phone_from_description(text)

    if apply_email and apply_url:
        return EnrichmentResult(
            apply_email=apply_email,
            apply_url=apply_url,
            apply_source="description_email",
            contact_phone=contact_phone,
        )
    if apply_email:
        return EnrichmentResult(
            apply_email=apply_email,
            apply_source="description_email",
            contact_phone=contact_phone,
        )
    if apply_url:
        return EnrichmentResult(
            apply_url=apply_url,
            apply_source="description_url",
            contact_phone=contact_phone,
        )
    if contact_phone:
        return EnrichmentResult(contact_phone=contact_phone)
    return EnrichmentResult()


def merge_description_extraction(
    row: dict,
    description: str | None,
) -> dict:
    """Apply description extraction into a job row dict in-place."""
    needs_apply = not (row.get("apply_url") and row.get("apply_email"))
    needs_phone = not row.get("contact_phone")
    if not needs_apply and not needs_phone:
        return row
    result = extract_apply_from_description(description)
    if needs_apply:
        if result.apply_email and not row.get("apply_email"):
            row["apply_email"] = result.apply_email
            row["apply_source"] = result.apply_source or "description_email"
        elif result.apply_url and not row.get("apply_url"):
            row["apply_url"] = result.apply_url
            row["apply_source"] = result.apply_source or "description_url"
    if needs_phone and result.contact_phone:
        row["contact_phone"] = result.contact_phone
    return row
