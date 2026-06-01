"""Tolerant JSON parsing and OpenRouter structured-output helpers."""
from __future__ import annotations

import json
import re
from typing import Any

from openai import APIError


def repair_llm_json(raw: str) -> dict[str, Any] | None:
    """Best-effort parse of near-valid LLM JSON (markdown fences, trailing commas)."""
    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw.strip(),
        flags=re.MULTILINE,
    )
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        candidate = re.sub(r",(\s*[}\]])", r"\1", match.group(0))
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


def is_response_format_rejected(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "response_format" in msg or "json_object" in msg or "json_schema" in msg


def build_json_schema_response_format(
    *,
    name: str,
    schema: dict[str, Any],
    strict: bool = False,
) -> dict[str, Any]:
    """OpenRouter / Gemini-compatible structured JSON response_format."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": strict,
            "schema": schema,
        },
    }
