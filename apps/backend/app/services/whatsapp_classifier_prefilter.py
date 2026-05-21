"""Regex pre-filter for WhatsApp classifier — rejects obvious promos before LLM."""
from __future__ import annotations

import re

_RE_CV_WRITING = re.compile(r"CV\s*writing", re.I)
_RE_CV_SERVICE = re.compile(r"CV\s*service", re.I)
_RE_TAKE_ADVANTAGE = re.compile(r"take advantage of", re.I)
_RE_PROMOTION = re.compile(r"promotion", re.I)
_RE_INBOX_WHATSAPP = re.compile(r"inbox\s+us\s+on\s+whats\s*app", re.I)
_RE_PAID_CV_RATE = re.compile(
    r"(?:K|ZMW)\s*\d{2,4}\s*per\s*(?:week|day|month)",
    re.I,
)


def promo_prefilter_rejects(text: str) -> bool:
    """True when message matches obvious non-job ad patterns."""
    if not text or len(text.strip()) < 10:
        return False
    t = text
    if _RE_CV_WRITING.search(t) or _RE_CV_SERVICE.search(t):
        return True
    if _RE_TAKE_ADVANTAGE.search(t) and _RE_PROMOTION.search(t):
        return True
    if _RE_INBOX_WHATSAPP.search(t):
        return True
    if _RE_PAID_CV_RATE.search(t):
        return True
    return False
