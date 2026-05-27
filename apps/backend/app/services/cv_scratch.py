"""LLM helpers for the manual CV wizard (summary + achievement bullets)."""
from __future__ import annotations

import asyncio
import json
import logging

from openai import APIError, AuthenticationError, OpenAI, RateLimitError
from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings
from app.lib.retry import circuit_is_open, degraded_llm_result
from app.services.cv_generator import _strip_fences
from app.services.openrouter_helpers import (
    create_chat_completion_with_retries,
    get_completion_content,
)

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM = """You are an expert CV writer for the Zambian job market.
Write a 2-4 sentence professional summary from the candidate's top strengths.
Use Zambian English. No markdown. Return ONLY valid JSON: {"summary": "..."}"""

BULLETS_SYSTEM = """You are an expert CV writer for the Zambian job market.
Suggest 3-5 achievement bullet points for a work experience entry.
Each bullet starts with a strong action verb and is one line. Do not invent
employer-specific facts beyond reasonable inference from role and company.
Return ONLY valid JSON: {"bullets": ["...", "..."]}"""


class _SummaryOut(BaseModel):
    summary: str = Field(..., min_length=40, max_length=2000)


class _BulletsOut(BaseModel):
    bullets: list[str] = Field(..., min_length=1, max_length=8)


def _client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )


async def suggest_professional_summary(
    *,
    strengths: list[str],
    headline: str = "",
    full_name: str = "",
) -> dict:
    if circuit_is_open():
        joined = ". ".join(strengths[:3])
        return degraded_llm_result(
            summary=f"Experienced professional with strengths in {joined}."
        )

    settings = get_settings()
    client = _client()
    strength_lines = "\n".join(f"- {s}" for s in strengths[:3])
    user = (
        f"Candidate: {full_name or 'Unknown'}\n"
        f"Headline: {headline or 'Not provided'}\n"
        f"Top strengths:\n{strength_lines}"
    )

    def _call():
        try:
            response = create_chat_completion_with_retries(
                client,
                log_prefix="cv_scratch_summary",
                model=settings.llm_model,
                max_tokens=512,
                messages=[
                    {"role": "system", "content": SUMMARY_SYSTEM},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            raw = get_completion_content(response, default="")
            if not raw:
                raise ValueError("Empty response from summary generator")
            data = json.loads(_strip_fences(raw).strip())
            validated = _SummaryOut.model_validate(data)
            return {"summary": validated.summary}
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("cv_scratch_summary parse failed: %s", exc)
            raise ValueError("Could not generate summary. Try editing manually.") from exc
        except AuthenticationError:
            raise ValueError("CV assistant is not configured. Please contact support.")
        except RateLimitError:
            raise ValueError("CV assistant is temporarily busy. Please try again shortly.")
        except APIError as exc:
            logger.error("cv_scratch_summary API error: %s", exc)
            raise ValueError("CV assistant is temporarily unavailable.") from exc

    return await asyncio.to_thread(_call)


async def suggest_role_bullets(
    *,
    title: str,
    company: str,
    context: str = "",
) -> dict:
    if circuit_is_open():
        return degraded_llm_result(
            bullets=[
                f"Delivered key outcomes as {title} at {company}.",
                "Collaborated with cross-functional teams to meet targets.",
                "Applied problem-solving skills to improve day-to-day operations.",
            ]
        )

    settings = get_settings()
    client = _client()
    user = f"Role: {title}\nCompany: {company}\nExtra context: {context or 'None'}"

    def _call():
        try:
            response = create_chat_completion_with_retries(
                client,
                log_prefix="cv_scratch_bullets",
                model=settings.llm_model,
                max_tokens=768,
                messages=[
                    {"role": "system", "content": BULLETS_SYSTEM},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            raw = get_completion_content(response, default="")
            if not raw:
                raise ValueError("Empty response from bullet generator")
            data = json.loads(_strip_fences(raw).strip())
            validated = _BulletsOut.model_validate(data)
            return {"bullets": validated.bullets[:8]}
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("cv_scratch_bullets parse failed: %s", exc)
            raise ValueError("Could not suggest bullets. Try writing your own.") from exc
        except AuthenticationError:
            raise ValueError("CV assistant is not configured. Please contact support.")
        except RateLimitError:
            raise ValueError("CV assistant is temporarily busy. Please try again shortly.")
        except APIError as exc:
            logger.error("cv_scratch_bullets API error: %s", exc)
            raise ValueError("CV assistant is temporarily unavailable.") from exc

    return await asyncio.to_thread(_call)
