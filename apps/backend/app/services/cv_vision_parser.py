"""Vision-based CV parsing for image-scanned PDFs (Gemini Flash via OpenRouter)."""
from __future__ import annotations

import asyncio
import base64
import io
import logging
from typing import Any

from openai import APIError, AuthenticationError, RateLimitError
from pdf2image import convert_from_bytes
from PIL import Image
from pydantic import ValidationError

from app.core.config import get_settings
from app.lib.llm_json import (
    build_json_schema_response_format,
    is_response_format_rejected,
    repair_llm_json,
)
from app.services.cv_parser import (
    CV_PARSE_SYSTEM_PROMPT,
    CVParseResult,
    _add_cv_parse_breadcrumb,
    _get_openrouter_client,
    validate_cv_parse_raw,
)
from app.services.llm import (
    FEATURE_CV_PARSING,
    LlmLogContext,
    estimate_openrouter_cost_usd,
    extract_usage_from_completion,
)
from app.services.openrouter_helpers import (
    create_chat_completion_with_retries,
    get_completion_content,
)
from app.services.prompt_safety import augment_system_prompt

logger = logging.getLogger(__name__)

MAX_VISION_PAGES = 5
# Ballpark vision tokens per 150 DPI page (image tiles + overhead).
TOKENS_PER_VISION_PAGE_EST = 800

CV_VISION_USER_PROMPT = (
    "These images are pages from a CV/resume PDF (possibly a phone photo or scan). "
    "Extract structured information and return ONLY valid JSON matching the schema."
)


def _page_to_png_bytes(pil_image: Image.Image) -> bytes:
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return buf.getvalue()


def _estimate_vision_input_tokens(page_count: int) -> int:
    prompt_est = len(CV_VISION_USER_PROMPT) // 4
    return page_count * TOKENS_PER_VISION_PAGE_EST + prompt_est


def is_vision_parse_empty(parsed: dict[str, Any]) -> bool:
    """True when vision produced no usable CV fields."""
    name = (parsed.get("full_name") or "").strip()
    skills = parsed.get("skills") or []
    summary = (parsed.get("experience_summary") or "").strip()
    if len(name) >= 2:
        return False
    if skills:
        return False
    if len(summary) >= 20:
        return False
    return True


def vision_parsed_to_raw_text(parsed: dict[str, Any]) -> str:
    """Synthesize embeddable plain text from structured vision output."""
    parts: list[str] = []
    if parsed.get("full_name"):
        parts.append(str(parsed["full_name"]))
    if parsed.get("email"):
        parts.append(str(parsed["email"]))
    if parsed.get("phone"):
        parts.append(str(parsed["phone"]))
    if parsed.get("location"):
        parts.append(str(parsed["location"]))
    if parsed.get("experience_summary"):
        parts.append(str(parsed["experience_summary"]))
    skills = parsed.get("skills") or []
    if skills:
        parts.append("Skills: " + ", ".join(str(s) for s in skills))
    education = parsed.get("education") or []
    if education:
        parts.append("Education: " + "; ".join(str(e) for e in education))
    return "\n".join(parts).strip()


def _vision_response_formats() -> list[dict[str, Any] | None]:
    schema = CVParseResult.model_json_schema()
    return [
        build_json_schema_response_format(
            name="cv_parse_result",
            schema=schema,
            strict=False,
        ),
        {"type": "json_object"},
        None,
    ]


def _record_vision_cost_telemetry(
    *,
    page_count: int,
    pages_sent: int,
    response: Any,
    model: str,
) -> None:
    prompt_tokens, completion_tokens, _ = extract_usage_from_completion(response)
    if prompt_tokens == 0:
        prompt_tokens = _estimate_vision_input_tokens(pages_sent)
    if completion_tokens == 0:
        completion_tokens = 512
    cost_usd = estimate_openrouter_cost_usd(model, prompt_tokens, completion_tokens)
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            category="cv.parse",
            message="cv_vision_parse",
            level="info",
            data={
                "page_count": page_count,
                "pages_sent": pages_sent,
                "estimated_tokens_in": prompt_tokens,
                "estimated_tokens_out": completion_tokens,
                "cost_usd_est": round(cost_usd, 6),
                "model": model,
            },
        )
    except Exception:
        logger.debug("Sentry breadcrumb skipped for CV vision", exc_info=True)


async def parse_cv_via_vision(pdf_bytes: bytes) -> dict[str, Any]:
    """Parse image-scanned PDF pages with Gemini vision. Returns model_dump()."""
    settings = get_settings()
    if not settings.cv_vision_ocr_enabled:
        raise ValueError("CV vision OCR is disabled")

    pages: list[Image.Image] = await asyncio.to_thread(
        convert_from_bytes,
        pdf_bytes,
        dpi=150,
        fmt="png",
    )
    page_count = len(pages)
    capped = pages[:MAX_VISION_PAGES]
    images_b64 = [
        base64.b64encode(_page_to_png_bytes(page)).decode("ascii")
        for page in capped
    ]

    if not images_b64:
        raise ValueError("PDF has no renderable pages")

    client = _get_openrouter_client()
    messages = [
        {"role": "system", "content": augment_system_prompt(CV_PARSE_SYSTEM_PROMPT)},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": CV_VISION_USER_PROMPT},
                *[
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    }
                    for b64 in images_b64
                ],
            ],
        },
    ]

    def _call() -> dict[str, Any]:
        log_ctx = LlmLogContext(
            feature=FEATURE_CV_PARSING,
            route="POST /api/v1/cv/upload",
        )
        response = None
        text = ""
        last_format_error: APIError | None = None

        try:
            for response_format in _vision_response_formats():
                kwargs: dict[str, Any] = {
                    "client": client,
                    "log_prefix": "cv_vision_parser",
                    "log_context": log_ctx,
                    "model": settings.llm_model,
                    "max_tokens": 4096,
                    "messages": messages,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format
                try:
                    response = create_chat_completion_with_retries(**kwargs)
                    break
                except APIError as fmt_exc:
                    if response_format is not None and is_response_format_rejected(fmt_exc):
                        last_format_error = fmt_exc
                        logger.warning(
                            "cv_vision_parser: response_format rejected (%s); retrying",
                            fmt_exc,
                        )
                        continue
                    raise

            if response is None:
                raise last_format_error or ValueError("Vision CV parse returned no response")

            _record_vision_cost_telemetry(
                page_count=page_count,
                pages_sent=len(images_b64),
                response=response,
                model=settings.llm_model,
            )

            text = get_completion_content(response, default="") or ""
            if not text.strip():
                raise ValueError("Vision CV parse returned empty content")

            raw = repair_llm_json(text)
            if raw is None:
                _add_cv_parse_breadcrumb(
                    "cv_vision_json_decode_failed",
                    extra={"response_preview": text[:200], "page_count": page_count},
                )
                raise ValueError("Vision CV parse returned invalid JSON")

            try:
                validated = validate_cv_parse_raw(raw)
            except ValidationError as ve:
                _add_cv_parse_breadcrumb(
                    "cv_vision_pydantic_validation_failed",
                    extra={
                        "validation_errors": ve.errors()[:5],
                        "page_count": page_count,
                    },
                )
                raise ValueError("Vision CV parse failed validation") from ve

            return validated.model_dump()

        except AuthenticationError:
            logger.error("OpenRouter API key is invalid for CV vision")
            raise ValueError("CV parsing service is not configured.")
        except RateLimitError:
            logger.warning("OpenRouter rate limit during CV vision parse")
            raise ValueError("CV parsing is temporarily busy. Please try again in a minute.")
        except APIError as e:
            logger.error("OpenRouter API error during CV vision: %s", e)
            raise ValueError("CV vision parsing is temporarily unavailable.") from e

    return await asyncio.to_thread(_call)
