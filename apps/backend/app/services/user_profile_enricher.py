"""LLM extraction of career profile fields from CV text (Track 4a-extend)."""
from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from typing import Optional

from openai import APIError, AuthenticationError, OpenAI, RateLimitError
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import get_settings
from app.services.seniority import (
    SeniorityLevelLiteral,
    normalize_experience_years,
    normalize_qualifications,
    normalize_seniority_level,
)

logger = logging.getLogger(__name__)

USER_PROFILE_ENRICH_SYSTEM_PROMPT = """You extract structured career profile metadata from CV/resume text for the Zambian job market.

Return ONLY valid JSON matching this exact shape:
{
  "years_experience": <integer or null>,
  "seniority_level": "intern" | "entry" | "mid" | "senior" | "lead" | "executive" | null,
  "highest_qualification": <string or null>,
  "qualifications": ["Bachelor's in Engineering", "ACCA", ...]
}

Rules:
- years_experience: total relevant professional years (integer 0-50). Estimate from work history dates when not stated explicitly. Use null only if the CV has no work history at all.
- seniority_level: overall career band implied by the most recent roles. Use null when unclear.
- highest_qualification: the single highest degree/diploma/cert (verbatim, max 200 chars), or null.
- qualifications: all degrees, diplomas, and professional certs mentioned (verbatim, max 20 items). Empty array if none.
- Do NOT invent credentials or employers not present in the text."""


class UserProfileEnrichment(BaseModel):
    years_experience: Optional[int] = Field(None, ge=0, le=50)
    seniority_level: Optional[SeniorityLevelLiteral] = None
    highest_qualification: Optional[str] = Field(None, max_length=200)
    qualifications: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("qualifications", mode="before")
    @classmethod
    def _normalize_qualifications(cls, v: object) -> list[str]:
        return normalize_qualifications(v)

    @field_validator("highest_qualification", mode="before")
    @classmethod
    def _normalize_highest(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            return None
        s = v.strip()
        return s if 1 <= len(s) <= 200 else None


def parse_user_profile_payload(data: object) -> UserProfileEnrichment:
    if isinstance(data, list):
        data = data[0] if data and isinstance(data[0], dict) else {}
    if not isinstance(data, dict):
        return UserProfileEnrichment()

    payload = dict(data)
    payload["years_experience"] = normalize_experience_years(
        payload.get("years_experience")
    )
    payload["seniority_level"] = normalize_seniority_level(
        payload.get("seniority_level")
    )
    payload["qualifications"] = normalize_qualifications(payload.get("qualifications"))
    payload["highest_qualification"] = UserProfileEnrichment._normalize_highest(
        payload.get("highest_qualification")
    )

    try:
        return UserProfileEnrichment.model_validate(payload)
    except ValidationError:
        return UserProfileEnrichment(
            years_experience=payload.get("years_experience")
            if isinstance(payload.get("years_experience"), int)
            else None,
            qualifications=payload.get("qualifications")
            if isinstance(payload.get("qualifications"), list)
            else [],
        )


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        max_retries=2,
    )


def _strip_fences(text: str) -> str:
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0]
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0]
    return text


async def enrich_user_profile(*, cv_text: str) -> UserProfileEnrichment:
    """Call Gemini Flash via OpenRouter; return empty enrichment on failure."""
    settings = get_settings()
    client = _client()
    user_prompt = f"CV text:\n{cv_text[:12000]}"

    def _call() -> UserProfileEnrichment:
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=512,
                messages=[
                    {"role": "system", "content": USER_PROFILE_ENRICH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            raw = (response.choices[0].message.content or "").strip()
            if not raw:
                return UserProfileEnrichment()
            data = json.loads(_strip_fences(raw).strip())
            return parse_user_profile_payload(data)
        except ValidationError as exc:
            logger.warning(
                "user profile enrich validation failed: %s", exc.errors()[:3]
            )
            return UserProfileEnrichment()
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("user profile enrich returned non-JSON")
            return UserProfileEnrichment()
        except AuthenticationError:
            logger.error("OpenRouter API key invalid for user profile enrichment")
            return UserProfileEnrichment()
        except RateLimitError:
            logger.warning("OpenRouter rate limit during user profile enrichment")
            return UserProfileEnrichment()
        except APIError as exc:
            logger.error("OpenRouter API error during user profile enrichment: %s", exc)
            return UserProfileEnrichment()
        except Exception as exc:
            logger.error(
                "Unexpected error during user profile enrichment: %s",
                exc,
                exc_info=True,
            )
            return UserProfileEnrichment()

    return await asyncio.to_thread(_call)


def build_user_profile_patch(
    enrichment: UserProfileEnrichment,
    *,
    user_row: dict,
) -> dict[str, object]:
    """NULL-only updates for profile fields already set on the user row."""
    patch: dict[str, object] = {}
    if enrichment.years_experience is not None:
        current = user_row.get("years_experience")
        if current is None or current == 0:
            patch["years_experience"] = enrichment.years_experience
    if user_row.get("seniority_level") is None and enrichment.seniority_level:
        patch["seniority_level"] = enrichment.seniority_level
    if user_row.get("highest_qualification") is None and enrichment.highest_qualification:
        patch["highest_qualification"] = enrichment.highest_qualification
    existing_quals = user_row.get("qualifications") or []
    if not existing_quals and enrichment.qualifications:
        patch["qualifications"] = enrichment.qualifications
    return patch
