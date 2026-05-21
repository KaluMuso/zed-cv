"""CV parsing via OpenRouter (google/gemini-flash-2.0).

OpenRouter exposes an OpenAI-compatible API, so we use the openai SDK
pointed at https://openrouter.ai/api/v1.
"""
import io
import json
import base64
import asyncio
import logging
from typing import Any, Optional
from functools import lru_cache

from openai import OpenAI, AuthenticationError, RateLimitError, APIError
from pydantic import BaseModel, Field, ValidationError, field_validator
from PyPDF2 import PdfReader
from docx import Document

from app.core.config import get_settings
from app.schemas.cv_sections import CVSections
from app.services.openrouter_helpers import get_completion_content

logger = logging.getLogger(__name__)


# Validation schema for LLM output.
# The LLM occasionally returns unexpected shapes - strings instead of arrays,
# arrays of nested objects when it was asked for strings, missing fields,
# or float strings instead of integers. Without validation, that garbage
# lands directly in cvs.parsed_data and downstream code (skills upsert,
# confidence display, matching) silently degrades or crashes much later.
class CVParseResult(BaseModel):
    full_name: str = Field("", max_length=500)
    email: str | None = Field(None, max_length=320)
    phone: str | None = Field(None, max_length=64)
    location: str | None = Field(None, max_length=200)
    years_experience: int = Field(0, ge=0, le=80)
    skills: list[str] = Field(default_factory=list)
    experience_summary: str = Field("", max_length=2000)
    education: list[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    # Richer structured shape (task #59). Optional so legacy LLM responses
    # without this key still validate cleanly. The flat fields above are
    # kept for backwards compat with existing parsed_data rows and code
    # that reads them directly (matching, /profile summary, etc.).
    sections: Optional[CVSections] = None

    @field_validator("sections", mode="before")
    @classmethod
    def _coerce_sections(cls, v: Any) -> Any:
        """Tolerate the LLM emitting {} for sections — treat as None.

        Pydantic will accept None or a dict-shaped object; an empty dict
        is technically valid (all section lists default empty) but it's
        wasteful storage, so we normalize to None.
        """
        if v is None or v == {} or v == "":
            return None
        return v

    @field_validator("skills", "education", mode="before")
    @classmethod
    def _coerce_string_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for item in v:
            if isinstance(item, str):
                s = item.strip()
            elif isinstance(item, dict):
                s = str(item.get("name") or item.get("skill") or item.get("title") or "").strip()
            elif item is None:
                continue
            else:
                s = str(item).strip()
            if s:
                out.append(s)
        return out

    @field_validator("skills", mode="after")
    @classmethod
    def _normalize_skill_case(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for s in v:
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(key)
        return normalized

    @field_validator("years_experience", mode="before")
    @classmethod
    def _coerce_years(cls, v: Any) -> int:
        if v is None or v == "":
            return 0
        if isinstance(v, int):
            return max(0, min(v, 80))
        if isinstance(v, float):
            return max(0, min(int(v), 80))
        if isinstance(v, str):
            import re as _re
            m = _re.search(r"\d+", v)
            if m:
                return max(0, min(int(m.group()), 80))
        return 0

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, v: Any) -> float:
        if v is None or v == "":
            return 0.0
        try:
            f = float(v)
        except (TypeError, ValueError):
            return 0.0
        if f > 1.0:
            f = f / 100.0
        return max(0.0, min(f, 1.0))


CV_PARSE_SYSTEM_PROMPT = """You are a CV/resume parser for the Zambian job market.
Extract structured information from CV text and return ONLY valid JSON.

Top-level fields (always emit):
- full_name (string)
- email (string or null)
- phone (string or null, format as +260XXXXXXXXX if Zambian)
- location (string or null, city/province in Zambia if applicable)
- years_experience (integer, estimate from work history dates)
- skills (array of lowercase strings, normalized - "javascript" not "JS", "microsoft office" not "MS Word")
- experience_summary (string, 1-2 sentences)
- education (array of strings, highest qualification first)
- confidence (float 0-1, how confident you are in the extraction)

Plus a richer "sections" object (omit any sub-section the CV doesn't have — do NOT invent entries):
- sections.header: {linkedin_url, portfolio_url, github_url} (all optional, full URLs only)
- sections.professional_summary: {text} (1-3 sentences elevator pitch)
- sections.work_experience: array of {title, company, location, start_date, end_date or null for current, achievements: [string]} (max 15 roles, max 20 achievements per role, achievements are impact statements not duties)
- sections.education: array of {degree, institution, location, start_date, end_date, gpa, thesis} (max 10)
- sections.certifications: array of {name, issuer, year, expiry} (max 25)
- sections.languages: array of {name, proficiency: "native"|"fluent"|"conversational"|"basic"} (max 10)
- sections.projects: array of {name, role, technologies: [string], outcome} (max 15)
- sections.achievements: array of {title, year} (max 20)
- sections.publications: array of {title, venue, year, url} (max 20)
- sections.memberships: array of {organisation, role, year_started, year_ended} (max 15)
- sections.volunteer_work: array of {organisation, role, start_date, end_date, description} (max 10)
- sections.references: array of {name, title, organisation, phone, email} (max 6)

Date format: prefer "YYYY-MM" when month is known, "YYYY" when only the year is, empty string when neither. Use null for end_date on current roles.

Zambia-specific rules:
- Recognize Zambian universities: UNZA, CBU, Mulungushi, Cavendish, ZCAS, DMI
- Recognize Zambian cities: Lusaka, Kitwe, Ndola, Livingstone, Kabwe, Chipata, Solwezi, Kasama
- Recognize Zambian professional bodies in memberships: EIZ, ZICA, LAZ, ZIM, HPCZ, ZIHRM, ZIPS
- Normalize phone numbers to +260 format
- Map local qualifications: Grade 12 = High School, Diploma, Advanced Diploma, Bachelor's, Master's, PhD"""

OCR_SYSTEM_PROMPT = """You are an OCR specialist for the Zambian job market.
Extract ALL text from images of CVs, resumes, or job postings.
Preserve structure: headings, bullet points, dates, contact info.
Return only the extracted text, nothing else."""


@lru_cache(maxsize=1)
def _get_openrouter_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )


async def extract_text_from_file(file_bytes: bytes, file_type: str) -> str:
    if file_type == "pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif file_type == "docx":
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs)
    elif file_type in ("jpg", "png", "jpeg"):
        return await _ocr_with_vision(file_bytes, file_type)
    raise ValueError(f"Unsupported file type: {file_type}")


async def parse_cv_with_llm(raw_text: str) -> dict[str, Any]:
    """Parse CV text into structured data using Gemini Flash via OpenRouter.

    The LLM's JSON output is validated through CVParseResult before being
    returned. Garbage shapes are coerced; truly unrecoverable garbage
    raises ValueError which the upload route maps to a clean error response.
    """
    settings = get_settings()
    client = _get_openrouter_client()

    def _call():
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                # 4096 to accommodate the structured "sections" object —
                # 12 nested arrays can easily exceed the old 1024 cap and
                # we were truncating mid-JSON for richer CVs (task #59).
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": CV_PARSE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Parse this CV and return JSON:\n\n{raw_text[:8000]}",
                    },
                ],
                response_format={"type": "json_object"},
            )

            text = get_completion_content(response, default="")
            if text is None:
                logger.warning("cv_parser_skip: bad response: empty choices")
                raise ValueError(
                    "Could not parse your CV. Please try uploading a clearer document."
                )
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            raw = json.loads(text.strip())

            try:
                validated = CVParseResult(**raw)
            except ValidationError as ve:
                logger.error(
                    "LLM returned malformed CV JSON. raw=%r errors=%s",
                    raw, ve.errors(),
                )
                raise ValueError(
                    "Could not understand the CV structure. "
                    "Please upload a clearer document or try a different format."
                )

            return validated.model_dump()

        except AuthenticationError:
            logger.error("OpenRouter API key is invalid or missing")
            raise ValueError("CV parsing service is not configured. Please contact support.")
        except RateLimitError:
            logger.warning("OpenRouter rate limit hit during CV parsing")
            raise ValueError("CV parsing is temporarily busy. Please try again in a minute.")
        except APIError as e:
            logger.error(f"OpenRouter API error during CV parsing: {e}")
            raise ValueError("CV parsing service is temporarily unavailable. Please try again later.")
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            raise ValueError("Could not parse your CV. Please try uploading a clearer document.")

    return await asyncio.to_thread(_call)


async def _ocr_with_vision(image_bytes: bytes, file_type: str) -> str:
    settings = get_settings()
    client = _get_openrouter_client()
    media_type = f"image/{'jpeg' if file_type in ('jpg', 'jpeg') else 'png'}"
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    def _call():
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": OCR_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{b64_image}"
                                },
                            },
                            {"type": "text", "text": "Extract ALL text from this image."},
                        ],
                    },
                ],
            )
            content = get_completion_content(response, default="")
            if content is None:
                logger.warning("cv_parser_ocr_skip: bad response: empty choices")
                raise ValueError("Image processing failed. Please try uploading a PDF or Word document instead.")
            return content

        except AuthenticationError:
            logger.error("OpenRouter API key is invalid for OCR")
            raise ValueError("Image processing service is not configured.")
        except APIError as e:
            logger.error(f"OpenRouter API error during OCR: {e}")
            raise ValueError("Image processing failed. Please try uploading a PDF or Word document instead.")

    return await asyncio.to_thread(_call)
