"""Extract a structured Job from a free-form WhatsApp channel message.

Slice F. The "Job Updates And Advertising Zm" channel posts roles as
human-formatted messages (no markdown, mixed with emoji, sometimes
multiple roles in one post). This service runs the message body through
Gemini Flash via OpenRouter with a JSON-response prompt, validates the
output against `ExtractedJob`, and returns it ready to be fed into the
`_ingest_one_job` pipeline in `apps/backend/app/api/v1/jobs.py`.

Cost control: each call is keyed in `ai_cache` by SHA-256 of the raw
message body. Channels often re-broadcast the same post; the dedup at
the fingerprint layer catches re-posts after Gemini, but the cache layer
prevents us from paying Gemini for the same message twice. Cache type
`job_extract` was added to `db_enums.CacheType` for this slice.

Returns None (NOT a raise) for messages the model classifies as
non-job-posts (greetings, chitchat, "next batch coming Friday" filler).
That lets the webhook handler return a quiet 200 without filling the
`errors` array — channel traffic is mostly non-job content.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from functools import lru_cache
from typing import Any, Optional

from openai import OpenAI, AuthenticationError, RateLimitError, APIError
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import get_settings
from app.services.openrouter_helpers import get_completion_content
from app.schemas.db_enums import CacheType

logger = logging.getLogger(__name__)


# Confidence floor below which we drop the extraction. Pinned high
# enough that the model only emits a JobCreate-ready payload when it's
# actually looking at a job post — not "Good morning everyone", not
# "Reminder: typing tutorial Saturday".
_MIN_EXTRACTION_CONFIDENCE = 60


class ExtractedJob(BaseModel):
    """Validated shape of the LLM's structured output.

    Field constraints loosely mirror `JobCreate` so a successful extraction
    can be passed directly to it without a second validation pass. The one
    deliberate divergence: `closing_date` arrives as a string here (the
    LLM is bad at strict ISO 8601 and the JobCreate validator already
    runs `_tolerant_parse_date`).
    """

    title: str = Field(..., min_length=3, max_length=500)
    company: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    description: str = Field(..., min_length=20)
    apply_url: Optional[str] = Field(None, max_length=2000)
    apply_email: Optional[str] = Field(None, max_length=255)
    closing_date: Optional[str] = Field(None, max_length=64)
    skills_required: list[str] = Field(default_factory=list)
    # 0-100 confidence the source message actually describes a job
    # posting. Below _MIN_EXTRACTION_CONFIDENCE we drop the extraction.
    confidence: int = Field(0, ge=0, le=100)

    # ── task #60: richer job ad shape ─────────────────────────────────
    # All optional — channel posts are noisy and rarely contain ALL
    # the structured fields. The LLM is instructed to omit (null) rather
    # than invent. JobCreate caps these strictly; we mirror those caps
    # here so an out-of-bounds field is rejected as part of the same
    # validation pass, not later at the ingest boundary.
    employment_type: Optional[str] = Field(None, max_length=32)
    work_arrangement: Optional[str] = Field(None, max_length=32)
    hybrid_days_per_week: Optional[int] = Field(None, ge=1, le=5)
    benefits: list[str] = Field(default_factory=list)
    application_instructions: Optional[str] = Field(None, max_length=2000)
    reporting_structure: Optional[str] = Field(None, max_length=500)
    manages_others: Optional[int] = Field(None, ge=0, le=10000)
    interview_process: Optional[str] = Field(None, max_length=1000)
    tools_tech_stack: list[str] = Field(default_factory=list)
    success_metrics: Optional[str] = Field(None, max_length=1000)
    company_description: Optional[str] = Field(None, max_length=2000)
    reference_number: Optional[str] = Field(None, max_length=100)
    currency: Optional[str] = Field(None, max_length=8)
    pay_frequency: Optional[str] = Field(None, max_length=16)
    bonus_structure: Optional[str] = Field(None, max_length=500)
    equity_offered: Optional[bool] = None
    # Free-text salary string the extractor can emit when it can't
    # confidently split into ngwee. The ingest pipeline parses this via
    # _parse_salary_to_ngwee. Never stored.
    salary_text: Optional[str] = Field(None, max_length=500)

    @field_validator("skills_required", "benefits", "tools_tech_stack", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        """LLM sometimes returns a single comma-separated string, sometimes
        list-of-dicts; coerce to list[str] without crashing.

        Shared across skills_required, benefits, and tools_tech_stack —
        all three are arrays-of-short-strings on the wire and the LLM
        has been observed flattening any of them into a comma-line.
        """
        if v is None:
            return []
        if isinstance(v, str):
            v = [s.strip() for s in v.split(",")]
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for item in v:
            if isinstance(item, str):
                s = item.strip()
            elif isinstance(item, dict):
                s = str(item.get("name") or item.get("skill") or "").strip()
            else:
                s = str(item or "").strip()
            if s:
                out.append(s.lower())
        return out

    @field_validator(
        "apply_url", "apply_email", "closing_date", "company", "location",
        "employment_type", "work_arrangement", "application_instructions",
        "reporting_structure", "interview_process", "success_metrics",
        "company_description", "reference_number", "currency",
        "pay_frequency", "bonus_structure", "salary_text",
        mode="before",
    )
    @classmethod
    def _empty_to_none(cls, v: Any) -> Any:
        """LLM frequently emits "" or "N/A" instead of null; normalize so
        downstream optional-vs-empty checks behave consistently."""
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            if not s or s.upper() in ("N/A", "NA", "NONE", "NULL", "-"):
                return None
            return s
        return v


_SYSTEM_PROMPT = """You extract a single job posting from a WhatsApp channel message.

The channel is a Zambian job board; posts are unstructured plain text and may include emoji, multiple links, and irrelevant lines (channel branding, ads).

Extract these fields and return ONLY valid JSON:
{
  "title":            "<role name, no company prefix>",
  "company":          "<employer name, null if not stated>",
  "location":         "<city or 'Remote', null if unclear; prefer Zambian cities>",
  "description":      "<plain-text body, 1-3 short paragraphs; do not include emoji or contact lines>",
  "apply_url":        "<https URL if present, else null>",
  "apply_email":      "<email if present, else null>",
  "closing_date":     "<YYYY-MM-DD if a deadline is stated, else null>",
  "skills_required":  ["short", "lowercase", "skill", "tokens"],

  "employment_type":  "<one of: full_time | part_time | contract | freelance | internship | temporary; null if unclear>",
  "work_arrangement": "<one of: remote | hybrid | on_site; null if unclear>",
  "hybrid_days_per_week": <int 1-5 if work_arrangement=hybrid and stated, else null>,
  "benefits":         ["short", "bullet", "items", "(max 20, each <= 200 chars)"],
  "application_instructions": "<step-by-step apply directions; null if not given>",
  "reporting_structure": "<who the role reports to; null if unclear>",
  "manages_others":   <int count of direct reports, null if not a management role or unclear>,
  "interview_process": "<steps in the hiring process; null if not described>",
  "tools_tech_stack": ["short", "lowercase", "tool", "names", "(max 30, each <= 80 chars)"],
  "success_metrics":  "<how success is measured; null if not stated>",
  "company_description": "<background about the hiring company; null if absent>",
  "reference_number": "<requisition / ref number if stated, else null>",
  "currency":         "<3-letter ISO like ZMW, USD, GBP; null if unclear>",
  "pay_frequency":    "<one of: monthly | annual | hourly | daily; null if unclear>",
  "bonus_structure":  "<freeform bonus / commission description; null if absent>",
  "equity_offered":   <true | false | null>,
  "salary_text":      "<the raw salary string from the message if present (e.g. 'K15,000 - K20,000'), else null>",

  "confidence":       <0-100; how sure you are this message is a real job post>
}

Rules:
  - If the message is not a job posting (greetings, ads, reminders, polls), set confidence < 30 and return whatever fields you can — the caller will drop it.
  - If the message contains MULTIPLE jobs, extract the FIRST one only and set confidence in 50-70 range so the caller can decide.
  - apply_url must start with http:// or https://. Channel/chat links like https://chat.whatsapp.com/... are NOT apply URLs — set apply_url to null.
  - Phone numbers are NOT apply_email.
  - For ALL the new structured fields (employment_type, work_arrangement, benefits, tools_tech_stack, application_instructions, reporting_structure, manages_others, interview_process, success_metrics, company_description, reference_number, currency, pay_frequency, bonus_structure, equity_offered, salary_text): emit null/empty when the message DOES NOT explicitly state the information. DO NOT invent or guess. Better to omit than to fabricate.
  - For salary: if the message gives a numeric salary, put the raw string in salary_text and leave it to downstream parsing. Do not attempt currency conversion or unit splits yourself.
  - Zambian context: ZICA, UNZA, CBU, ZRA, ZESCO, ZANACO, MTN, Airtel are legitimate entities, not noise. Professional bodies (EIZ, LAZ, HPCZ) are also valid.
  - Description must be at least 20 characters or you should set confidence below 30."""


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def _strip_fences(text: str) -> str:
    """OpenRouter sometimes wraps JSON in ```json fences despite the
    response_format={"type":"json_object"} hint. Strip them."""
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0]
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0]
    return text


def _cache_get(supabase, cache_key: str) -> Optional[dict]:
    """Look up an extracted-job payload from ai_cache. Best-effort —
    any error falls through to a real Gemini call."""
    try:
        rows = (
            supabase.table("ai_cache")
            .select("result")
            .eq("cache_key", cache_key)
            .limit(1)
            .execute()
        )
        if rows.data:
            return rows.data[0].get("result")
    except Exception:
        return None
    return None


def _cache_put(supabase, cache_key: str, input_hash: str, result: dict, model: str) -> None:
    """Store a successful extraction so re-broadcasts don't re-bill Gemini.
    Swallows duplicate-key errors silently — cache plumbing must never
    crash the webhook path."""
    from app.schemas.db_enums import validate_cache_type
    try:
        supabase.table("ai_cache").insert({
            "cache_key": cache_key,
            "cache_type": validate_cache_type(CacheType.job_extract.value),
            "input_hash": input_hash,
            "result": result,
            "model": model,
        }).execute()
    except Exception:
        pass


async def extract_job_from_message(
    message_body: str,
    supabase=None,
) -> Optional[ExtractedJob]:
    """Try to extract a job from a free-form channel message.

    - Returns ExtractedJob on success when confidence >= _MIN_EXTRACTION_CONFIDENCE.
    - Returns None when the model says "not a job" or confidence is below
      the floor. The webhook should treat None as "quietly ignore this
      message" (no error, no ingest call).
    - Raises ValueError for hard infra failures (auth, rate limit) so the
      webhook can log + 503; channel messages don't trigger user-facing
      errors so this is mostly for ops visibility.

    `supabase` is optional. When provided, ai_cache is consulted and
    written. When None (test/script paths), the cache is skipped and
    every call hits the LLM.
    """
    text = (message_body or "").strip()
    if not text or len(text) < 30:
        # Below 30 chars there's nothing useful to extract — short circuit
        # before we burn a Gemini call.
        return None

    settings = get_settings()
    body_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    cache_key = f"job_extract:{settings.llm_model}:{body_hash}"

    cached = _cache_get(supabase, cache_key) if supabase is not None else None
    if cached is not None:
        try:
            extracted = ExtractedJob(**cached)
            if extracted.confidence >= _MIN_EXTRACTION_CONFIDENCE:
                return extracted
            return None
        except ValidationError:
            # Stale/garbage cache row — fall through to a real call.
            logger.warning("job_extractor: cached row failed validation; re-extracting")

    client = _client()

    def _call() -> Optional[ExtractedJob]:
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                # 2048 to accommodate the richer structured output added
                # in task #60. 1024 occasionally truncated mid-JSON on
                # the longer prompts.
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"Extract from this channel message:\n\n{text[:4000]}"},
                ],
                response_format={"type": "json_object"},
            )
            raw = get_completion_content(response, default="")
            if raw is None:
                logger.warning("job_extractor_skip: bad response: empty choices")
                return None
            data = json.loads(_strip_fences(raw).strip())
            try:
                extracted = ExtractedJob(**data)
            except ValidationError as ve:
                logger.warning(
                    "job_extractor: invalid LLM output. errors=%s preview=%r",
                    ve.errors(), raw[:200],
                )
                return None
            return extracted
        except AuthenticationError:
            logger.error("OpenRouter key invalid for job_extractor")
            raise ValueError("Job extractor is not configured. Set OPENROUTER_API_KEY.")
        except RateLimitError:
            logger.warning("OpenRouter rate limit hit during job extraction")
            raise ValueError("Job extractor is temporarily busy.")
        except APIError as e:
            logger.error("OpenRouter API error during job extraction: %s", e)
            raise ValueError("Job extractor is temporarily unavailable.")
        except json.JSONDecodeError:
            logger.warning("job_extractor: model returned non-JSON")
            return None

    extracted = await asyncio.to_thread(_call)
    if extracted is None:
        return None

    # Write through to cache only on a syntactically-valid extraction
    # (any confidence). A "confidence: 10, not-a-job" result is still
    # worth caching so the next re-broadcast is free.
    if supabase is not None:
        _cache_put(
            supabase,
            cache_key,
            body_hash,
            extracted.model_dump(),
            settings.llm_model,
        )

    if extracted.confidence < _MIN_EXTRACTION_CONFIDENCE:
        logger.info(
            "job_extractor: confidence %d below floor %d — dropping (title=%r)",
            extracted.confidence, _MIN_EXTRACTION_CONFIDENCE, extracted.title,
        )
        return None
    return extracted
