"""Classify WhatsApp channel messages as job postings (text + image)."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Literal, Optional

from openai import APIError, AuthenticationError, OpenAI, RateLimitError
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import get_settings
from app.schemas.db_enums import CacheType, validate_cache_type
from app.services.seniority import normalize_qualifications, normalize_seniority_level
from app.services.whatsapp_classifier_prefilter import promo_prefilter_rejects

logger = logging.getLogger(__name__)

_CLASSIFY_CACHE_DAYS = 30

ClassifierDecision = Literal[
    "accepted_as_job",
    "rejected_as_promo",
    "rejected_as_other",
]

class WhatsappJobClassification(BaseModel):
    is_job: bool = False
    is_multi_job: bool = False
    title: Optional[str] = Field(None, max_length=500)
    company: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    apply_url: Optional[str] = Field(None, max_length=2000)
    apply_email: Optional[str] = Field(None, max_length=255)
    employment_type: Optional[str] = Field(None, max_length=32)
    work_arrangement: Optional[str] = Field(None, max_length=32)
    experience_min_years: Optional[int] = Field(None, ge=0, le=50)
    seniority_level: Optional[str] = Field(None, max_length=32)
    qualifications_required: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    ocr_text: Optional[str] = Field(
        None,
        description="For image posts: raw OCR transcript returned by the vision model.",
    )

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


_TEXT_SYSTEM = """You classify WhatsApp messages from Zambian job channels.

Return JSON only:
{
  "is_job": true|false,
  "is_multi_job": true|false,
  "title": string|null,
  "company": string|null,
  "location": string|null,
  "description": string|null,
  "apply_url": string|null,
  "apply_email": string|null,
  "employment_type": string|null,
  "work_arrangement": string|null,
  "experience_min_years": integer|null,
  "seniority_level": "intern"|"entry"|"mid"|"senior"|"lead"|"executive"|null,
  "qualifications_required": [string],
  "skills": [string],
  "ocr_text": null
}

Return is_job=true ONLY if the message describes a SPECIFIC role being filled by a
SPECIFIC employer, with at least one of: a job title, a company name, or application
instructions (email, URL, phone, or office address).

Return is_job=false for:
- CV writing services ('Get your CV done for K50', 'Professional CV writing')
- Recruitment agency promotions ('We help job seekers find work', 'Inbox us for job tips')
- Generic motivational content ('Don't give up on your dreams')
- WhatsApp group promotions ('Join our paid group for daily jobs')
- Affiliate/referral programs ('Refer 3 friends and earn')
- Sale of services unrelated to a specific job ('Need a website? Contact...')
- Mobile-money scams ('Send K50 to register')
- Bulk message promotions starting with 'Take advantage of', '🎉 Promotion 🎉', or similar
- Greetings, memes, channel rules, unrelated chatter

If unsure, lean toward is_job=false to keep the platform clean.

- is_multi_job=true when the message lists 2+ distinct roles.
- Zambian context: MTN, Airtel, ZANACO, ZESCO, Lusaka, Kitwe are normal.
- apply_url must be http(s). WhatsApp chat links are NOT apply URLs.
- Do not invent salary or requirements; omit when not stated.
- skills: lowercase short tokens (e.g. python, django).
- description must be >= 20 chars when is_job=true."""

_VISION_SYSTEM = """You classify images of job posters from Zambian WhatsApp job channels.

First OCR all visible text into ocr_text, then decide if it is a job posting.

Return is_job=true ONLY for a SPECIFIC role at a SPECIFIC employer with at least one of:
job title, company name, or application instructions (email, URL, phone, office address).

Return is_job=false for CV-writing ads, recruitment-agency promos, motivational posts,
paid-group promos, affiliate schemes, unrelated service sales, mobile-money scams, and
bulk promotions ('Take advantage of', '🎉 Promotion 🎉'). If unsure, use is_job=false.

Return JSON only with the same schema as text classification, including ocr_text."""


def _classifier_decision(result: WhatsappJobClassification) -> ClassifierDecision:
    if result.is_job:
        return "accepted_as_job"
    return "rejected_as_other"


def _metadata_payload(
    *,
    decision: ClassifierDecision,
    took_ms: int,
    llm_response: str | None = None,
) -> dict[str, Any]:
    return {
        "classifier_decision": decision,
        "llm_response": llm_response,
        "took_ms": took_ms,
    }


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
    metadata: dict[str, Any] | None = None,
) -> None:
    expires = datetime.now(timezone.utc) + timedelta(days=_CLASSIFY_CACHE_DAYS)
    row: dict[str, Any] = {
        "cache_key": cache_key,
        "cache_type": validate_cache_type(CacheType.whatsapp_classify.value),
        "input_hash": input_hash,
        "result": result,
        "model": model,
        "expires_at": expires.isoformat(),
    }
    if metadata is not None:
        row["metadata"] = metadata
    try:
        supabase.table("ai_cache").insert(row).execute()
    except Exception:
        pass


def _parse_response(raw: str) -> WhatsappJobClassification:
    data = json.loads(_strip_fences(raw))
    return WhatsappJobClassification.model_validate(data)


async def _store_classification(
    supabase: Any | None,
    *,
    cache_key: str,
    input_hash: str,
    result: WhatsappJobClassification,
    model: str,
    metadata: dict[str, Any],
) -> WhatsappJobClassification:
    if supabase is not None:
        _cache_put(
            supabase,
            cache_key=cache_key,
            input_hash=input_hash,
            result=result.model_dump(mode="json"),
            model=model,
            metadata=metadata,
        )
    return result


async def classify_whatsapp_text(
    message_body: str,
    *,
    supabase: Any | None = None,
) -> WhatsappJobClassification:
    """Classify a text channel message."""
    started = time.perf_counter()
    text = (message_body or "").strip()
    if len(text) < 10:
        return WhatsappJobClassification(is_job=False)

    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    body_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    model = settings.llm_model
    cache_key = f"wa_classify_text:{model}:{body_hash}"

    if supabase is not None:
        cached = _cache_get(supabase, cache_key)
        if cached is not None:
            try:
                return WhatsappJobClassification.model_validate(cached)
            except ValidationError:
                pass

    if promo_prefilter_rejects(text):
        took_ms = int((time.perf_counter() - started) * 1000)
        result = WhatsappJobClassification(is_job=False)
        return await _store_classification(
            supabase,
            cache_key=cache_key,
            input_hash=body_hash,
            result=result,
            model=model,
            metadata=_metadata_payload(
                decision="rejected_as_promo",
                took_ms=took_ms,
                llm_response=None,
            ),
        )

    client = _client()

    def _call() -> tuple[WhatsappJobClassification, str]:
        response = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": _TEXT_SYSTEM},
                {"role": "user", "content": text[:6000]},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return _parse_response(raw), raw

    try:
        result, raw = await asyncio.to_thread(_call)
    except (AuthenticationError, RateLimitError) as exc:
        raise ValueError(f"Classifier unavailable: {exc}") from exc
    except (APIError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning("whatsapp text classify failed: %s", exc)
        result = WhatsappJobClassification(is_job=False)
        raw = None

    took_ms = int((time.perf_counter() - started) * 1000)
    return await _store_classification(
        supabase,
        cache_key=cache_key,
        input_hash=body_hash,
        result=result,
        model=model,
        metadata=_metadata_payload(
            decision=_classifier_decision(result),
            took_ms=took_ms,
            llm_response=raw,
        ),
    )


async def classify_whatsapp_image(
    image_bytes: bytes,
    *,
    mime_type: str = "image/jpeg",
    caption: str = "",
    supabase: Any | None = None,
) -> WhatsappJobClassification:
    """OCR + classify a job poster image via Gemini Vision."""
    started = time.perf_counter()
    if not image_bytes:
        return WhatsappJobClassification(is_job=False)

    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    cap = (caption or "").strip()
    if cap and promo_prefilter_rejects(cap):
        took_ms = int((time.perf_counter() - started) * 1000)
        img_hash = hashlib.sha256(image_bytes).hexdigest()
        cap_hash = hashlib.sha256(cap.encode()).hexdigest()[:16]
        model = settings.openrouter_vision_model
        cache_key = f"wa_classify_img:{model}:{img_hash}:{cap_hash}"
        result = WhatsappJobClassification(is_job=False)
        return await _store_classification(
            supabase,
            cache_key=cache_key,
            input_hash=img_hash,
            result=result,
            model=model,
            metadata=_metadata_payload(
                decision="rejected_as_promo",
                took_ms=took_ms,
                llm_response=None,
            ),
        )

    img_hash = hashlib.sha256(image_bytes).hexdigest()
    cap_hash = hashlib.sha256(cap.encode()).hexdigest()[:16]
    model = settings.openrouter_vision_model
    cache_key = f"wa_classify_img:{model}:{img_hash}:{cap_hash}"

    if supabase is not None:
        cached = _cache_get(supabase, cache_key)
        if cached is not None:
            try:
                return WhatsappJobClassification.model_validate(cached)
            except ValidationError:
                pass

    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"
    user_parts: list[dict] = [
        {
            "type": "image_url",
            "image_url": {"url": data_url},
        },
    ]
    if cap:
        user_parts.append({"type": "text", "text": f"Caption: {cap[:500]}"})

    client = _client()

    def _call() -> tuple[WhatsappJobClassification, str]:
        response = client.chat.completions.create(
            model=model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": _VISION_SYSTEM},
                {"role": "user", "content": user_parts},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return _parse_response(raw), raw

    try:
        result, raw = await asyncio.to_thread(_call)
    except (AuthenticationError, RateLimitError) as exc:
        raise ValueError(f"Vision classifier unavailable: {exc}") from exc
    except (APIError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning("whatsapp image classify failed: %s", exc)
        result = WhatsappJobClassification(is_job=False)
        raw = None

    took_ms = int((time.perf_counter() - started) * 1000)
    return await _store_classification(
        supabase,
        cache_key=cache_key,
        input_hash=img_hash,
        result=result,
        model=model,
        metadata=_metadata_payload(
            decision=_classifier_decision(result),
            took_ms=took_ms,
            llm_response=raw,
        ),
    )
