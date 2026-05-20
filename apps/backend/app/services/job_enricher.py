"""LLM enrichment for scraped job listings via OpenRouter (Gemini Flash).

Extracts technical skills, employment_type, and work_arrangement from
job descriptions during ingest and backfill. Failures degrade to empty
skills so callers can keep existing scraper data.
"""
from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from typing import Literal, Optional

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

EmploymentTypeLiteral = Literal[
    "full_time",
    "part_time",
    "contract",
    "freelance",
    "internship",
    "temporary",
]
WorkArrangementLiteral = Literal["on_site", "remote", "hybrid"]

_VALID_EMPLOYMENT_TYPES = frozenset(
    {
        "full_time",
        "part_time",
        "contract",
        "freelance",
        "internship",
        "temporary",
    }
)
_VALID_WORK_ARRANGEMENTS = frozenset({"on_site", "remote", "hybrid"})

JOB_ENRICH_SYSTEM_PROMPT = """You extract structured job metadata from job postings for the Zambian job market.

Return ONLY valid JSON matching this exact shape:
{
  "skills": ["skill1", "skill2"],
  "employment_type": "full_time" | "part_time" | "contract" | "freelance" | "internship" | "temporary" | null,
  "work_arrangement": "on_site" | "remote" | "hybrid" | null,
  "experience_min_years": <integer or null>,
  "experience_max_years": <integer or null>,
  "seniority_level": "intern" | "entry" | "mid" | "senior" | "lead" | "executive" | null,
  "qualifications_required": ["Bachelor's in Engineering", "ACCA", ...]
}

Rules for skills:
- Lowercase only. Each skill 1-100 characters.
- Technical and professional competencies only (tools, frameworks, certifications, domain expertise).
- Do NOT include generic soft skills ("team player", "leadership", "communication") unless they are explicitly job-distinguishing requirements in the text.
- Use Zambian-context vocabulary when the posting mentions it (e.g. "zica", "eiz", "zra", "unza", "cbu").
- Maximum 25 skills. Prefer precision over breadth.

Rules for employment_type and work_arrangement:
- Use null when the description does not clearly state the value. Do NOT guess.
- employment_type must be one of: full_time, part_time, contract, freelance, internship, temporary.
- work_arrangement must be one of: on_site, remote, hybrid.

Rules for experience and seniority:
- experience_min_years / experience_max_years: integers 0-50, or null if not stated. Do NOT guess.
- If a range is given ("3-5 years"), set min=3 and max=5. If only a minimum ("5+ years"), set min=5 and max=null.
- seniority_level: infer only when the title or requirements clearly imply a band (e.g. "Graduate Trainee" → intern, "Manager" → lead). Use null when unclear.
- qualifications_required: degrees, diplomas, professional certs (ZICA, EIZ, ACCA, CIMA, etc.). Verbatim phrasing, max 20 items. Empty array if none stated.

Return ONE object only — never a JSON array, even if the posting lists multiple roles."""


class JobEnrichment(BaseModel):
    skills: list[str] = Field(default_factory=list, max_length=25)
    employment_type: Optional[EmploymentTypeLiteral] = None
    work_arrangement: Optional[WorkArrangementLiteral] = None
    experience_min_years: Optional[int] = Field(None, ge=0, le=50)
    experience_max_years: Optional[int] = Field(None, ge=0, le=50)
    seniority_level: Optional[SeniorityLevelLiteral] = None
    qualifications_required: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("skills", mode="before")
    @classmethod
    def _normalize_skills(cls, v: object) -> list[str]:
        if not v:
            return []
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for item in v:
            if not isinstance(item, str):
                continue
            s = item.strip().lower()
            if 1 <= len(s) <= 100:
                out.append(s)
        return out[:25]

    @field_validator("qualifications_required", mode="before")
    @classmethod
    def _normalize_qualifications(cls, v: object) -> list[str]:
        return normalize_qualifications(v)


def _make_client(*, max_retries: int) -> OpenAI:
    settings = get_settings()
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        max_retries=max_retries,
    )


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    return _make_client(max_retries=2)


@lru_cache(maxsize=1)
def _client_no_retry() -> OpenAI:
    return _make_client(max_retries=0)


def _strip_fences(text: str) -> str:
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0]
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0]
    return text


def parse_llm_enrichment_payload(data: object) -> JobEnrichment:
    """Lenient parse: multi-job arrays → first row; unknown enums → null."""
    if isinstance(data, list):
        data = data[0] if data and isinstance(data[0], dict) else {}
    if not isinstance(data, dict):
        return JobEnrichment()

    payload = dict(data)
    et = payload.get("employment_type")
    if et is not None:
        et_norm = str(et).strip().lower()
        payload["employment_type"] = (
            et_norm if et_norm in _VALID_EMPLOYMENT_TYPES else None
        )
    wa = payload.get("work_arrangement")
    if wa is not None:
        wa_norm = str(wa).strip().lower()
        payload["work_arrangement"] = (
            wa_norm if wa_norm in _VALID_WORK_ARRANGEMENTS else None
        )

    payload["experience_min_years"] = normalize_experience_years(
        payload.get("experience_min_years")
    )
    payload["experience_max_years"] = normalize_experience_years(
        payload.get("experience_max_years")
    )
    payload["seniority_level"] = normalize_seniority_level(
        payload.get("seniority_level")
    )
    payload["qualifications_required"] = normalize_qualifications(
        payload.get("qualifications_required")
    )
    emin = payload.get("experience_min_years")
    emax = payload.get("experience_max_years")
    if emin is not None and emax is not None and emax < emin:
        payload["experience_max_years"] = None

    try:
        return JobEnrichment.model_validate(payload)
    except ValidationError:
        skills_raw = payload.get("skills")
        if isinstance(skills_raw, list):
            return JobEnrichment.model_validate({"skills": skills_raw})
        return JobEnrichment()


async def enrich_job(
    *,
    title: str,
    company: str | None,
    description: str,
) -> JobEnrichment:
    """Call Gemini Flash via OpenRouter; return empty skills on any failure."""
    settings = get_settings()
    client = _client()

    company_line = f"Company: {company}\n" if company else ""
    user_prompt = (
        f"Title: {title}\n"
        f"{company_line}"
        f"Description:\n{description[:12000]}"
    )

    def _call() -> JobEnrichment:
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=768,
                messages=[
                    {"role": "system", "content": JOB_ENRICH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            raw = (response.choices[0].message.content or "").strip()
            if not raw:
                return JobEnrichment()
            data = json.loads(_strip_fences(raw).strip())
            return parse_llm_enrichment_payload(data)
        except ValidationError as exc:
            logger.warning("job enrich validation failed: %s", exc.errors()[:3])
            return JobEnrichment()
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("job enrich returned non-JSON")
            return JobEnrichment()
        except AuthenticationError:
            logger.error("OpenRouter API key invalid for job enrichment")
            return JobEnrichment()
        except RateLimitError:
            logger.warning("OpenRouter rate limit during job enrichment")
            return JobEnrichment()
        except APIError as exc:
            logger.error("OpenRouter API error during job enrichment: %s", exc)
            return JobEnrichment()
        except Exception as exc:
            logger.error(
                "Unexpected error during job enrichment: %s",
                exc,
                exc_info=True,
            )
            return JobEnrichment()

    return await asyncio.to_thread(_call)


class EnrichJobOutcome(BaseModel):
    """Backfill helper — distinguishes rate limits from empty LLM output."""

    enrichment: JobEnrichment = Field(default_factory=JobEnrichment)
    completed: bool = True
    """False when OpenRouter rate-limited; caller should not advance progress."""


async def enrich_job_for_backfill(
    *,
    title: str,
    company: str | None,
    description: str,
) -> EnrichJobOutcome:
    """Like enrich_job but no SDK retries and surfaces rate-limit for resume logic."""
    settings = get_settings()
    client = _client_no_retry()

    company_line = f"Company: {company}\n" if company else ""
    user_prompt = (
        f"Title: {title}\n"
        f"{company_line}"
        f"Description:\n{description[:12000]}"
    )

    def _call() -> EnrichJobOutcome:
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=768,
                messages=[
                    {"role": "system", "content": JOB_ENRICH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            raw = (response.choices[0].message.content or "").strip()
            if not raw:
                return EnrichJobOutcome()
            data = json.loads(_strip_fences(raw).strip())
            return EnrichJobOutcome(
                enrichment=parse_llm_enrichment_payload(data),
                completed=True,
            )
        except RateLimitError:
            logger.warning("OpenRouter rate limit during job enrichment (backfill)")
            return EnrichJobOutcome(completed=False)
        except ValidationError as exc:
            logger.warning("job enrich validation failed: %s", exc.errors()[:3])
            return EnrichJobOutcome()
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("job enrich returned non-JSON")
            return EnrichJobOutcome()
        except AuthenticationError:
            logger.error("OpenRouter API key invalid for job enrichment")
            return EnrichJobOutcome()
        except APIError as exc:
            logger.error("OpenRouter API error during job enrichment: %s", exc)
            return EnrichJobOutcome()
        except Exception as exc:
            logger.error(
                "Unexpected error during job enrichment: %s",
                exc,
                exc_info=True,
            )
            return EnrichJobOutcome()

    return await asyncio.to_thread(_call)
