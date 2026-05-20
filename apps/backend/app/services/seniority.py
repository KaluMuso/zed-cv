"""Shared seniority enum validation for job and user profile enrichers."""
from __future__ import annotations

from typing import Literal, Optional

SeniorityLevelLiteral = Literal[
    "intern",
    "entry",
    "mid",
    "senior",
    "lead",
    "executive",
]

_VALID_SENIORITY_LEVELS = frozenset(
    {"intern", "entry", "mid", "senior", "lead", "executive"}
)


def normalize_seniority_level(value: object) -> Optional[SeniorityLevelLiteral]:
    if value is None:
        return None
    norm = str(value).strip().lower()
    if norm in _VALID_SENIORITY_LEVELS:
        return norm  # type: ignore[return-value]
    return None


def normalize_qualifications(value: object, *, max_items: int = 20) -> list[str]:
    if not value:
        return []
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        s = item.strip()
        if 1 <= len(s) <= 200:
            out.append(s)
    return out[:max_items]


def normalize_experience_years(value: object) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        n = int(value)
    elif isinstance(value, str):
        digits = "".join(c for c in value if c.isdigit())
        if not digits:
            return None
        n = int(digits)
    else:
        return None
    if 0 <= n <= 50:
        return n
    return None
