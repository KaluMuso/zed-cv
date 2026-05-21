"""Extract closing_date from job descriptions via OpenRouter (Gemini Flash)."""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from functools import lru_cache
from typing import Optional

from openai import APIError, OpenAI
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_ISO_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")


class DeadlineExtraction(BaseModel):
    closing_date: Optional[str] = Field(
        None,
        description="ISO date YYYY-MM-DD or null if no deadline stated",
    )


DEADLINE_SYSTEM = """Extract the application closing date from a job posting.

Return ONLY JSON: {"closing_date": "YYYY-MM-DD"} or {"closing_date": null}

Look for phrases like: closes, deadline, apply by, submission deadline, expires, closing date.
Use the stated calendar date; if only relative ("in two weeks") return null.
Do not guess. Zambia timezone context only affects interpretation of ambiguous dates — prefer ISO output."""


@lru_cache
def _client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )


def parse_closing_date(value: str | None) -> Optional[date]:
    if not value:
        return None
    text = str(value).strip()
    match = _ISO_DATE_RE.search(text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        return None


def extract_deadline_from_text_regex(description: str) -> Optional[date]:
    """Cheap regex pass before LLM (e.g. 2026-05-30 embedded in text)."""
    if not description:
        return None
    match = _ISO_DATE_RE.search(description)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


async def extract_closing_date_llm(
    description: str,
    title: str = "",
    company: str = "",
) -> Optional[date]:
    """LLM extraction; returns None on refusal, parse error, or missing API key."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        return extract_deadline_from_text_regex(description)

    snippet = (description or "")[:8000]
    user = f"Title: {title}\nCompany: {company}\n\nDescription:\n{snippet}"

    try:
        resp = _client().chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": DEADLINE_SYSTEM},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=128,
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        parsed = DeadlineExtraction.model_validate(data)
        return parse_closing_date(parsed.closing_date)
    except (APIError, json.JSONDecodeError, ValueError) as exc:
        logger.info("deadline LLM extract failed: %s", exc)
        return extract_deadline_from_text_regex(description)
