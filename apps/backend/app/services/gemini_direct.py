"""Direct Google AI Studio (Gemini) for batch/cron LLM workloads.

User-facing flows (CV parse, cover letter, CV generator) stay on OpenRouter.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

import sentry_sdk
from google import genai
from google.genai import types

from app.core.config import get_settings
from app.services.llm_provider_health import record_llm_provider_status

logger = logging.getLogger(__name__)

GEMINI_BATCH_MODEL = "gemini-2.0-flash"


class QuotaExhaustedError(Exception):
    """Gemini free-tier daily quota or rate limit exhausted."""


class GeminiDirectNotConfiguredError(Exception):
    """GEMINI_API_KEY missing or empty."""


def _is_quota_error(exc: BaseException) -> bool:
    text = str(exc)
    return (
        "RESOURCE_EXHAUSTED" in text
        or "429" in text
        or "quota" in text.lower()
        or ("rate" in text.lower() and "limit" in text.lower())
    )


def _is_server_error(exc: BaseException) -> bool:
    text = str(exc)
    return any(code in text for code in ("500", "502", "503", "504", "INTERNAL"))


def should_fallback_to_openrouter(exc: BaseException) -> bool:
    """True when a realtime caller should retry via OpenRouter."""
    return isinstance(exc, QuotaExhaustedError) or _is_quota_error(exc) or _is_server_error(exc)


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    settings = get_settings()
    key = settings.gemini_api_key.strip()
    if not key:
        raise GeminiDirectNotConfiguredError("GEMINI_API_KEY is not configured")
    return genai.Client(api_key=key)


def _tag_provider_gemini_direct() -> None:
    sentry_sdk.set_tag("provider", "gemini_direct")


def _parse_json_response(text: str | None) -> dict[str, Any]:
    if not text or not str(text).strip():
        raise ValueError("empty LLM response")
    raw = str(text).strip()
    if raw.startswith("```"):
        raw = raw.removeprefix("```json").removeprefix("```").strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("expected JSON object")
    return parsed


async def generate_json(
    prompt: str,
    *,
    schema: dict[str, Any] | None = None,
    max_tokens: int = 4096,
    feature: str = "unknown",
) -> dict[str, Any]:
    """Structured JSON via Gemini direct API."""
    settings = get_settings()
    if not settings.gemini_api_key.strip():
        record_llm_provider_status("gemini_direct", "not_configured")
        raise GeminiDirectNotConfiguredError("GEMINI_API_KEY is not configured")

    client = _get_client()
    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        response_mime_type="application/json",
    )
    if schema is not None:
        config.response_schema = schema

    _tag_provider_gemini_direct()
    try:
        response = await client.aio.models.generate_content(
            model=GEMINI_BATCH_MODEL,
            contents=prompt,
            config=config,
        )
        usage = response.usage_metadata
        token_count = (
            int(usage.total_token_count)
            if usage is not None and usage.total_token_count is not None
            else 0
        )
        sentry_sdk.add_breadcrumb(
            category="llm",
            message=f"gemini_direct.{feature}",
            level="info",
            data={"provider": "gemini_direct", "tokens": token_count},
        )
        record_llm_provider_status("gemini_direct", "ok")
        return _parse_json_response(response.text)
    except Exception as exc:
        if _is_quota_error(exc):
            record_llm_provider_status("gemini_direct", "quota_exhausted")
            raise QuotaExhaustedError(f"Gemini direct quota: {exc}") from exc
        record_llm_provider_status("gemini_direct", "error")
        logger.warning("gemini_direct.%s failed: %s", feature, exc)
        raise


async def generate_text(
    prompt: str,
    *,
    max_tokens: int = 1024,
    feature: str = "unknown",
) -> str:
    """Plain-text completion via Gemini direct (e.g. Bwana chat)."""
    if not get_settings().gemini_api_key.strip():
        record_llm_provider_status("gemini_direct", "not_configured")
        raise GeminiDirectNotConfiguredError("GEMINI_API_KEY is not configured")

    client = _get_client()
    config = types.GenerateContentConfig(max_output_tokens=max_tokens)
    _tag_provider_gemini_direct()
    try:
        response = await client.aio.models.generate_content(
            model=GEMINI_BATCH_MODEL,
            contents=prompt,
            config=config,
        )
        text = (response.text or "").strip()
        if not text:
            raise ValueError("empty LLM response")
        usage = response.usage_metadata
        token_count = (
            int(usage.total_token_count)
            if usage is not None and usage.total_token_count is not None
            else 0
        )
        sentry_sdk.add_breadcrumb(
            category="llm",
            message=f"gemini_direct.{feature}",
            level="info",
            data={"provider": "gemini_direct", "tokens": token_count},
        )
        record_llm_provider_status("gemini_direct", "ok")
        return text
    except Exception as exc:
        if _is_quota_error(exc):
            record_llm_provider_status("gemini_direct", "quota_exhausted")
            raise QuotaExhaustedError(f"Gemini direct quota: {exc}") from exc
        record_llm_provider_status("gemini_direct", "error")
        logger.warning("gemini_direct.%s failed: %s", feature, exc)
        raise
