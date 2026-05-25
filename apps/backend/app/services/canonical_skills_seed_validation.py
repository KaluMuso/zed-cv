"""Reject job-requirement sentences before they become canonical_skills rows."""
from __future__ import annotations

import logging
import re
from functools import lru_cache

from app.services.canonical_skills_seed_data import (
    ACRONYMS,
    CURATED_RAW_TOP_100,
    DISPLAY_OVERRIDES,
    EXTRA_ALIASES,
)
from app.services.skill_resolver import SKILL_ALIASES

logger = logging.getLogger(__name__)

MAX_SKILL_CHARS = 60
MIN_SKILL_CHARS = 3
MAX_SKILL_WORDS = 5
SENTENCE_END_CHARS = ".:;"

QUALIFICATION_RE = re.compile(
    r"\b("
    r"years?|experience|minimum|must|should|required|"
    r"bachelor'?s?|degree|diploma|certificate|membership|"
    r"knowledge\s+of|ability\s+to"
    r")\b",
    re.IGNORECASE,
)

KNOWN_TYPO_TOKENS: frozenset[str] = frozenset(
    {
        "lincence",
        "lisence",
        "licene",
        "experiance",
        "managment",
        "adminstration",
    }
)

_EXTRA_VOCAB: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "or",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "the",
        "with",
        "without",
        "using",
        "based",
        "related",
        "course",
        "valid",
        "driver",
        "drivers",
        "license",
        "licence",
        "licensing",
        "practical",
        "reputable",
        "environment",
        "abattoir",
        "sales",
        "marketing",
        "business",
        "administration",
        "any",
        "related",
    }
)


def _word_tokens(text: str) -> list[str]:
    return [m.group(0) for m in re.finditer(r"[a-z']+", text.lower())]


@lru_cache(maxsize=1)
def _skill_vocabulary() -> frozenset[str]:
    words: set[str] = set(_EXTRA_VOCAB)
    words.update(ACRONYMS)
    for raw in CURATED_RAW_TOP_100:
        words.update(_word_tokens(raw))
    for mapping in (SKILL_ALIASES, EXTRA_ALIASES, DISPLAY_OVERRIDES):
        for key, value in mapping.items():
            words.update(_word_tokens(key))
            if isinstance(value, str):
                words.update(_word_tokens(value))
    return frozenset(words)


def reject_seed_candidate(text: str) -> str | None:
    """Return a short rejection reason, or None if the string may be seeded."""
    stripped = text.strip()
    if not stripped:
        return "empty"

    if len(stripped) < MIN_SKILL_CHARS:
        return "too short"

    if len(stripped) > MAX_SKILL_CHARS:
        return "too long"

    trimmed_end = stripped.rstrip()
    if trimmed_end and trimmed_end[-1] in SENTENCE_END_CHARS:
        return "ends in punctuation"

    if QUALIFICATION_RE.search(stripped):
        return "qualification phrase"

    words = _word_tokens(stripped)
    if len(words) > MAX_SKILL_WORDS:
        return "too many words"

    vocab = _skill_vocabulary()
    for token in words:
        bare = token.strip("'")
        if bare in KNOWN_TYPO_TOKENS:
            return f"known typo: {bare}"
        if len(bare) < 4:
            continue
        if bare in vocab or bare in ACRONYMS:
            continue
        return f"unknown word: {bare}"

    return None


def log_skipped_candidate(raw: str, reason: str) -> None:
    preview = raw.strip()
    if len(preview) > 80:
        preview = preview[:77] + "..."
    logger.info("skipped: %s — %r", reason, preview)
