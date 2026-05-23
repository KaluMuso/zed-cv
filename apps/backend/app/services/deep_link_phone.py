"""Zambian phone extraction for deep-link HTML parsers."""
from __future__ import annotations

import re
from typing import Optional

_PHONE_RE = re.compile(
    r"(?:\+260[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{4}|\+260\d{9}|0[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{4}|0\d{9})",
    re.IGNORECASE,
)


def normalize_zambian_phone(raw: str) -> Optional[str]:
    """Normalize a matched phone string to E.164 +260XXXXXXXXX."""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("260") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+260{digits[1:]}"
    return None


def _is_plausible_phone(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 9 or len(digits) > 13:
        return False
    if not (digits.startswith("260") or digits.startswith("0")):
        return False
    if len(digits) == 4 and digits.isdigit():
        year = int(digits)
        if 1900 <= year <= 2099:
            return False
    if len(digits) in (4, 5) and not digits.startswith(("0", "260")):
        return False
    return normalize_zambian_phone(raw) is not None


def extract_phones_from_text(text: str) -> list[str]:
    """Return normalized +260 phones, skipping years and bare price-like numbers."""
    found: list[str] = []
    seen: set[str] = set()
    for match in _PHONE_RE.finditer(text or ""):
        if not _is_plausible_phone(match.group(0)):
            continue
        normalized = normalize_zambian_phone(match.group(0))
        if normalized and normalized not in seen:
            seen.add(normalized)
            found.append(normalized)
    return found
