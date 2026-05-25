"""Bwana Interview — mock interview LLM via OpenRouter (google/gemini-2.0-flash-001)."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

from app.core.config import get_settings
from app.lib.retry import DEGRADED_LLM_USER_MESSAGE, circuit_is_open
from app.services.llm import FEATURE_APTITUDE, LlmLogContext
from app.services.openrouter_helpers import (
    create_chat_completion_with_retries,
    get_completion_content,
)

logger = logging.getLogger(__name__)

MOCK_QUESTION_COUNT = 7
BWANA_INTERVIEW_MODEL = "google/gemini-2.0-flash-001"

_APTITUDE_BENCHMARK_MEAN = 50.0
_APTITUDE_BENCHMARK_STDDEV = 15.0

PACK_TIME_LIMITS: dict[str, int] = {
    "numerical": 20 * 60,
    "verbal": 20 * 60,
    "abstract": 15 * 60,
}


def _system_prompt(role: str) -> str:
    return (
        f"You are Bwana Interview, a professional career coach interviewing a "
        f"candidate for the role of {role}. Ask STAR-method behavioural questions "
        f"and role-specific technical questions. After each answer, score 0-10 on "
        f"STAR completeness and give one-sentence constructive feedback. After "
        f"{MOCK_QUESTION_COUNT} questions total, write a final summary: overall_score "
        f"(0-100), 3 strengths, 3 improvements, 3 suggested practice areas. "
        f"Keep all responses under 100 words."
    )


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    raw = _strip_json_fences(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Bwana Interview returned an invalid response.") from exc
    if not isinstance(data, dict):
        raise ValueError("Bwana Interview returned an invalid response.")
    return data


def aptitude_percentile(score: float) -> float:
    """Percentile vs placeholder Zambian benchmark (mean=50, stddev=15)."""
    import math

    z = (score - _APTITUDE_BENCHMARK_MEAN) / _APTITUDE_BENCHMARK_STDDEV
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return round(max(0.0, min(100.0, cdf * 100.0)), 1)


async def _call_openrouter(
    *,
    role: str,
    messages: list[dict[str, str]],
    max_tokens: int = 350,
    user_id: str | None = None,
    route: str = "POST /api/v1/interview/mock",
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("Bwana Interview is temporarily unavailable.")
    if circuit_is_open():
        return {"degraded": True, "message": DEGRADED_LLM_USER_MESSAGE}

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    payload_messages: list[dict[str, str]] = [
        {"role": "system", "content": _system_prompt(role)},
        *messages,
    ]

    def _sync_call() -> dict[str, Any]:
        try:
            response = create_chat_completion_with_retries(
                client,
                log_prefix="bwana_interview",
                log_context=LlmLogContext(
                    feature=FEATURE_APTITUDE,
                    route=route,
                    user_id=user_id,
                ),
                model=BWANA_INTERVIEW_MODEL,
                max_tokens=max_tokens,
                temperature=0.4,
                messages=payload_messages,
            )
            content = get_completion_content(response, default="")
            if not content or not str(content).strip():
                raise ValueError("Empty response from Bwana Interview")
            return _parse_json_object(str(content))
        except AuthenticationError:
            logger.error("OpenRouter key invalid for Bwana Interview")
            raise ValueError("Bwana Interview is not configured.")
        except RateLimitError:
            logger.warning("OpenRouter rate limit for Bwana Interview")
            raise ValueError("Bwana Interview is busy — try again shortly.")
        except APIError as exc:
            logger.error("OpenRouter error for Bwana Interview: %s", exc)
            raise ValueError("Bwana Interview is temporarily unavailable.")

    return await asyncio.to_thread(_sync_call)


async def generate_first_question(role: str, *, user_id: str | None = None) -> str:
    data = await _call_openrouter(
        role=role,
        user_id=user_id,
        messages=[
            {
                "role": "user",
                "content": (
                    'Return JSON only: {"question": "<first interview question>"}. '
                    "Mix behavioural STAR and role-specific technical."
                ),
            },
        ],
    )
    question = str(data.get("question") or "").strip()
    if not question:
        raise ValueError("Bwana Interview did not return a question.")
    return question


async def score_answer(
    *,
    role: str,
    question: str,
    answer: str,
    question_number: int,
    prior_turns: list[dict[str, str]],
    user_id: str | None = None,
) -> dict[str, Any]:
    """Score one answer on STAR completeness."""
    history = list(prior_turns)
    history.append(
        {
            "role": "user",
            "content": (
                f'Candidate answer to Q{question_number} "{question}":\n{answer}\n\n'
                "Return JSON only with keys: star_score (0-10 number), feedback "
                "(one sentence string)."
            ),
        },
    )
    data = await _call_openrouter(role=role, messages=history, user_id=user_id)
    return {
        "star_score": float(data.get("star_score") or 0),
        "feedback": str(data.get("feedback") or "").strip()
        or "Good effort — add more detail.",
    }


async def generate_next_question(
    *,
    role: str,
    question_number: int,
    prior_turns: list[dict[str, str]],
    user_id: str | None = None,
) -> str:
    history = list(prior_turns)
    history.append(
        {
            "role": "user",
            "content": (
                f"Ask interview question {question_number} of {MOCK_QUESTION_COUNT}. "
                'Return JSON only: {"question": "<text>"}.'
            ),
        },
    )
    data = await _call_openrouter(role=role, messages=history, user_id=user_id)
    next_q = str(data.get("question") or data.get("next_question") or "").strip()
    if not next_q:
        raise ValueError("Bwana Interview did not return the next question.")
    return next_q


async def generate_final_summary(
    *,
    role: str,
    transcript: list[dict[str, Any]],
    user_id: str | None = None,
) -> dict[str, Any]:
    lines = []
    for i, row in enumerate(transcript, start=1):
        lines.append(
            f"Q{i}: {row.get('question')}\nA: {row.get('user_answer')}\n"
            f"STAR: {row.get('star_score')}/10 — {row.get('feedback')}"
        )
    data = await _call_openrouter(
        role=role,
        user_id=user_id,
        messages=[
            {
                "role": "user",
                "content": (
                    "Interview transcript:\n"
                    + "\n\n".join(lines)
                    + "\n\nReturn JSON only: overall_score (0-100), strengths "
                    "(3 strings), improvements (3 strings), practice_areas (3 strings)."
                ),
            },
        ],
        max_tokens=400,
    )
    return {
        "overall_score": float(data.get("overall_score") or 0),
        "strengths": list(data.get("strengths") or [])[:3],
        "improvements": list(data.get("improvements") or [])[:3],
        "practice_areas": list(data.get("practice_areas") or [])[:3],
    }
