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

JOB_ENRICH_SYSTEM_PROMPT = """You extract structured job metadata from job postings for the Zambian job market.

Return ONLY valid JSON matching this exact shape:
{
  "skills": ["skill1", "skill2"],
  "employment_type": "full_time" | "part_time" | "contract" | "freelance" | "internship" | "temporary" | null,
  "work_arrangement": "on_site" | "remote" | "hybrid" | null
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
- work_arrangement must be one of: on_site, remote, hybrid."""


class JobEnrichment(BaseModel):
    skills: list[str] = Field(default_factory=list, max_length=25)
    employment_type: Optional[EmploymentTypeLiteral] = None
    work_arrangement: Optional[WorkArrangementLiteral] = None

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
                max_tokens=512,
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
            return JobEnrichment.model_validate(data)
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
