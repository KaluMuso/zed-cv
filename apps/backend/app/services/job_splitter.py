"""Split multi-role WhatsApp / scraper messages into separate JobCreate rows."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Optional

from openai import APIError, AuthenticationError, OpenAI, RateLimitError
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import get_settings
from app.schemas.db_enums import CacheType, validate_cache_type
from app.schemas.jobs import JobCreate
from app.services.seniority import normalize_qualifications, normalize_seniority_level
from app.services.whatsapp_classifier import WhatsappJobClassification

logger = logging.getLogger(__name__)

_SPLIT_CACHE_DAYS = 30

_NUMBERED_ROLE_RE = re.compile(
    r"(?:^|\n)\s*(?:"
    r"\d+[\).:]\s+"
    r"|Job\s*\d+[\):.]?\s+"
    r"|\(\d+\)\s+"
    r")",
    re.IGNORECASE | re.MULTILINE,
)
_CAPS_TITLE_LINE_RE = re.compile(
    r"(?:^|\n)\s*([A-Z][A-Z0-9\s/&\-]{8,60})\s*(?:\n|$)"
)
_APPLY_LINE_RE = re.compile(
    r"(?:^|\n)\s*(?:apply|how to apply|send cv|submit)[:\s]",
    re.IGNORECASE | re.MULTILINE,
)


class SplitJobItem(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=20)
    skills: list[str] = Field(default_factory=list)
    experience_min_years: Optional[int] = Field(None, ge=0, le=50)
    seniority_level: Optional[str] = Field(None, max_length=32)
    qualifications_required: list[str] = Field(default_factory=list)

    @field_validator("skills", "qualifications_required", mode="before")
    @classmethod
    def _coerce_str_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            v = [s.strip() for s in v.split(",")]
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for item in v:
            s = str(item or "").strip().lower()
            if s:
                out.append(s[:100])
        return out

    @field_validator("seniority_level", mode="before")
    @classmethod
    def _seniority(cls, v: Any) -> Optional[str]:
        return normalize_seniority_level(v)

    @field_validator("qualifications_required", mode="after")
    @classmethod
    def _quals(cls, v: list[str]) -> list[str]:
        return normalize_qualifications(v, max_items=20)


class SplitJobsResult(BaseModel):
    jobs: list[SplitJobItem] = Field(default_factory=list)


_SPLIT_SYSTEM = """You split a single WhatsApp job-board message that lists MULTIPLE distinct roles.

Return JSON only:
{
  "jobs": [
    {
      "title": string,
      "description": string (>= 20 chars, role-specific),
      "skills": [string],
      "experience_min_years": integer|null,
      "seniority_level": "intern"|"entry"|"mid"|"senior"|"lead"|"executive"|null,
      "qualifications_required": [string]
    }
  ]
}

Rules:
- Each job must have a distinct title and description (do not merge roles).
- Shared apply contact from the message applies to all roles — do not duplicate apply lines per job.
- skills: lowercase short tokens.
- Zambian context is normal (Lusaka, MTN, ZANACO).
- If the message is truly a single role, return exactly one job."""


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def _strip_fences(text: str) -> str:
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0]
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0]
    return text


def _cache_get(supabase: Any, cache_key: str) -> Optional[dict]:
    try:
        now = datetime.now(timezone.utc).isoformat()
        rows = (
            supabase.table("ai_cache")
            .select("result, expires_at")
            .eq("cache_key", cache_key)
            .limit(1)
            .execute()
        )
        if not rows.data:
            return None
        row = rows.data[0]
        expires = row.get("expires_at")
        if expires and str(expires) < now:
            return None
        result = row.get("result")
        return result if isinstance(result, dict) else None
    except Exception:
        return None


def _cache_put(
    supabase: Any,
    *,
    cache_key: str,
    input_hash: str,
    result: dict,
    model: str,
) -> None:
    expires = datetime.now(timezone.utc) + timedelta(days=_SPLIT_CACHE_DAYS)
    try:
        supabase.table("ai_cache").insert({
            "cache_key": cache_key,
            "cache_type": validate_cache_type(CacheType.whatsapp_split.value),
            "input_hash": input_hash,
            "result": result,
            "model": model,
            "expires_at": expires.isoformat(),
        }).execute()
    except Exception:
        pass


def heuristic_is_multi_job(message_body: str) -> bool:
    """Fast pre-check before LLM split."""
    text = (message_body or "").strip()
    if len(text) < 40:
        return False
    numbered = _NUMBERED_ROLE_RE.findall(text)
    if len(numbered) >= 2:
        return True
    apply_lines = _APPLY_LINE_RE.findall(text)
    if len(apply_lines) >= 2:
        return True
    caps_titles = _CAPS_TITLE_LINE_RE.findall(text)
    if len(caps_titles) >= 2:
        return True
    return False


def should_split_message(
    message_body: str,
    classification: WhatsappJobClassification,
) -> bool:
    """True when ingest should fan out into multiple JobCreate rows."""
    if getattr(classification, "is_multi_job", False):
        return True
    return heuristic_is_multi_job(message_body)


async def split_message_with_llm(
    message_body: str,
    classification: WhatsappJobClassification,
    *,
    supabase: Any | None = None,
) -> list[SplitJobItem]:
    """LLM split via OpenRouter Gemini 2.0 Flash (cached 30 days)."""
    text = (message_body or "").strip()
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    ctx = json.dumps(
        {
            "message": text[:6000],
            "classified_title": classification.title,
            "classified_company": classification.company,
            "classified_skills": classification.skills,
        },
        sort_keys=True,
    )
    body_hash = hashlib.sha256(ctx.encode("utf-8")).hexdigest()
    model = settings.llm_model
    cache_key = f"wa_split:{model}:{body_hash}"

    if supabase is not None:
        cached = _cache_get(supabase, cache_key)
        if cached is not None:
            try:
                return SplitJobsResult.model_validate(cached).jobs
            except ValidationError:
                pass

    client = _client()
    user_blob = (
        f"Message:\n{text[:6000]}\n\n"
        f"Classifier hint — company: {classification.company or 'unknown'}, "
        f"location: {classification.location or 'unknown'}, "
        f"apply_url: {classification.apply_url or 'null'}, "
        f"apply_email: {classification.apply_email or 'null'}"
    )

    def _call() -> SplitJobsResult:
        response = client.chat.completions.create(
            model=model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": _SPLIT_SYSTEM},
                {"role": "user", "content": user_blob},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return SplitJobsResult.model_validate(json.loads(_strip_fences(raw)))

    try:
        result = await asyncio.to_thread(_call)
    except (AuthenticationError, RateLimitError) as exc:
        raise ValueError(f"Job splitter unavailable: {exc}") from exc
    except (APIError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning("whatsapp job split failed: %s", exc)
        return []

    if supabase is not None and result.jobs:
        _cache_put(
            supabase,
            cache_key=cache_key,
            input_hash=body_hash,
            result=result.model_dump(mode="json"),
            model=model,
        )
    return result.jobs


def split_items_to_job_creates(
    items: list[SplitJobItem],
    base: JobCreate,
    *,
    message_id: str,
) -> list[JobCreate]:
    """Map split items onto shared ingest metadata."""
    out: list[JobCreate] = []
    for idx, item in enumerate(items):
        wa_id = f"{message_id}:split:{idx}" if len(items) > 1 else message_id
        payload = base.model_dump()
        payload.update({
            "title": item.title[:500],
            "description": item.description[:8000],
            "skills_required": item.skills,
            "experience_min_years": item.experience_min_years,
            "qualifications_required": item.qualifications_required,
            "whatsapp_message_id": wa_id,
        })
        if item.seniority_level:
            payload["seniority_level"] = item.seniority_level
        out.append(JobCreate.model_validate(payload))
    return out


async def split_classification_to_jobs(
    message_body: str,
    classification: WhatsappJobClassification,
    base_job: JobCreate,
    *,
    message_id: str,
    supabase: Any | None = None,
    force_llm: bool = False,
) -> list[JobCreate]:
    """Return one or more JobCreate rows for ingest."""
    if not should_split_message(message_body, classification) and not force_llm:
        return [base_job]

    items = await split_message_with_llm(
        message_body, classification, supabase=supabase
    )
    if len(items) < 2:
        return [base_job]
    return split_items_to_job_creates(items, base_job, message_id=message_id)
