"""Job ingest quality gates, markdown normalization, and multi-role splitting."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import get_settings
from app.lib.retry import circuit_is_open
from app.services.openrouter_helpers import (
    create_chat_completion_with_retries,
    get_completion_content,
)

logger = logging.getLogger(__name__)

AGGREGATOR_DOMAINS = {
    "jobwebzambia.com",
    "gozambiajobs.com",
    "jobsearchzambia.com",
    "careersinafrica.com",
    "everjobs.com.zm",
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
}

ZM_VALID_PHONE_PATTERNS = [
    re.compile(r"^\+260(95|96|97)\d{7}$"),
    re.compile(r"^\+260(76|77)\d{7}$"),
    re.compile(r"^\+260(75)\d{7}$"),
    re.compile(r"^\+260(211|212|214|215|216|217|218)\d{6,7}$"),
]

THIN_DESCRIPTION_THRESHOLD = 300

KNOWN_RECRUITING_PLATFORMS = {
    "oraclecloud.com",
    "myworkdayjobs.com",
    "greenhouse.io",
    "lever.co",
    "smartrecruiters.com",
    "workable.com",
    "linkedin.com/jobs",
}

SECTION_HEADER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^(?:JOB\s+)?(PURPOSE|DESCRIPTION|SUMMARY)\b", re.I), "## Job purpose"),
    (re.compile(r"^(?:JOB\s+)?(RESPONSIBILITIES|DUTIES|KEY DUTIES)\b", re.I), "## Responsibilities"),
    (re.compile(r"^(?:JOB\s+)?REQUIREMENTS\b", re.I), "## Requirements"),
    (re.compile(r"^(?:JOB\s+)?QUALIFICATIONS\b", re.I), "## Qualifications"),
    (re.compile(r"^(?:KEY\s+)?SKILLS\b", re.I), "## Skills"),
    (re.compile(r"^BENEFITS\b", re.I), "## Benefits"),
    (re.compile(r"^HOW TO APPLY\b", re.I), "## How to apply"),
    (re.compile(r"^CLOSING DATE\b", re.I), "## Closing date"),
    (re.compile(r"^ABOUT (?:THE\s+)?(COMPANY|ROLE|US)\b", re.I), "## About"),
]

SECTION_KEY_MAP = {
    "responsibilities": "section_responsibilities",
    "requirements": "section_requirements",
    "benefits": "section_benefits",
    "how to apply": "section_how_to_apply",
    "about": "section_about",
}

MULTI_ROLE_TITLE_PATTERNS = [
    re.compile(r"\b(and|,|/|\s&\s)\b.*\b(and|,|/|\s&\s)\b", re.I),
    re.compile(r"^(multiple|various)\s+(positions|vacancies|opportunities)", re.I),
]

NUMBERED_ROLE_BODY_PATTERN = re.compile(
    r"^\s*\d+\.\s*(?:JOB DESCRIPTION\s*[-–]\s*)?([A-Z][A-Z\s/]+)\b",
    re.MULTILINE,
)

_H2_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_BLANK_RUN_RE = re.compile(r"\n{3,}")

# Candidate-facing descriptions must not expose scraper provenance footers.
_SCRAPER_LINE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*first\s+posted\b", re.I),
    re.compile(r"^\s*scraped\s+from\b", re.I),
    re.compile(r"^\s*source\s*:\s*", re.I),
    re.compile(r"^\s*posted\s+via\b", re.I),
    re.compile(r"^\s*view\s+(the\s+)?original\s+(posting|job)\b", re.I),
    re.compile(r"^\s*see\s+original\s+(posting|job)\b", re.I),
    re.compile(r"linkedin\.com", re.I),
    re.compile(r"bestjobs\.co", re.I),
    re.compile(r"gozambiajobs", re.I),
    re.compile(r"jobwebzambia", re.I),
    re.compile(r"jobartis", re.I),
    re.compile(r"myjobmag", re.I),
    re.compile(r"reliefweb\.int", re.I),
]


def _is_scraper_metadata_line(line: str) -> bool:
    trimmed = line.strip()
    if not trimmed:
        return False
    return any(pattern.search(trimmed) for pattern in _SCRAPER_LINE_PATTERNS)


def strip_scraper_metadata(text: str) -> str:
    """Remove scraper/source footer lines from plain-text job descriptions."""
    if not text:
        return ""
    lines = [line for line in text.split("\n") if not _is_scraper_metadata_line(line)]
    cleaned = "\n".join(lines)
    return _BLANK_RUN_RE.sub("\n\n", cleaned).strip()


class LlmClient(Protocol):
    """Minimal OpenAI-compatible client for tests."""

    def chat(self) -> Any:
        ...


class SplitRoleItem(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=20)
    skills_required: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)

    @field_validator("skills_required", "requirements", mode="before")
    @classmethod
    def _coerce_lists(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            v = [s.strip() for s in v.split(",") if s.strip()]
        if not isinstance(v, list):
            return []
        return [str(x).strip() for x in v if str(x).strip()]


_SPLIT_SYSTEM = """You split a single job listing that contains MULTIPLE distinct roles from one company.

Return JSON only — an array of objects, each with:
- title (string, role name)
- description (string, >= 20 chars, that role only)
- skills_required (array of strings)
- requirements (array of strings)

If the listing is a single role, return a one-element array."""


def validate_source_url(
    source_url: str | None, apply_url: str | None
) -> tuple[bool, str | None]:
    """Returns (ok, reason_if_not_ok). source_url must be present and not an aggregator."""
    del apply_url  # reserved for future cross-checks
    if not source_url:
        return False, "missing_source_url"
    url_lower = source_url.lower()
    for domain in AGGREGATOR_DOMAINS:
        if domain in url_lower:
            return False, f"source_url_is_aggregator:{domain}"
    return True, None


def normalize_contact_phone(raw: str | None) -> str | None:
    """Returns valid Zambian E.164 number or None if invalid."""
    if not raw:
        return None
    digits = re.sub(r"[\s\-()]+", "", raw)
    if not digits.startswith("+"):
        return None
    for pattern in ZM_VALID_PHONE_PATTERNS:
        if pattern.match(digits):
            return digits
    return None


def description_quality_ok(
    description: str, apply_url: str | None
) -> tuple[bool, str | None]:
    """Reject thin descriptions that only deep-link to ATS pages."""
    if not description or len(description) >= THIN_DESCRIPTION_THRESHOLD:
        return True, None
    if apply_url:
        url_lower = apply_url.lower()
        for ats in KNOWN_RECRUITING_PLATFORMS:
            if ats in url_lower:
                return False, f"thin_description_with_ats_link:{ats}"
    return True, None


def _line_to_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    if stripped.startswith("## "):
        return stripped
    for pattern, heading in SECTION_HEADER_PATTERNS:
        if pattern.match(stripped):
            return heading
    return None


def normalize_description_markdown(text: str) -> str:
    """Insert blank lines around section headers and normalize to H2 markdown."""
    if not text:
        return ""

    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if out and out[-1] != "":
                out.append("")
            continue

        heading = _line_to_heading(line)
        if heading:
            if out and out[-1] != "":
                out.append("")
            out.append(heading)
            out.append("")
            continue

        out.append(line)

    normalized = "\n".join(out).strip()
    normalized = _BLANK_RUN_RE.sub("\n\n", normalized)
    return normalized


def extract_sections(description_md: str) -> dict[str, str]:
    """Parse H2 markdown sections into DB column keys."""
    if not description_md:
        return {}

    sections: dict[str, str] = {}
    matches = list(_H2_HEADER_RE.finditer(description_md))
    if not matches:
        return sections

    for idx, match in enumerate(matches):
        title_raw = match.group(1).strip()
        title_key = title_raw.lower()
        col = None
        for fragment, column in SECTION_KEY_MAP.items():
            if fragment in title_key:
                col = column
                break
        if not col:
            continue

        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(description_md)
        body = description_md[start:end].strip()
        if body:
            sections[col] = body

    return sections


def parent_listing_signature(title: str, company: str | None) -> str:
    raw = f"{title.strip()}|{(company or '').strip()}".lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _title_suggests_multi_role(title: str) -> bool:
    for pattern in MULTI_ROLE_TITLE_PATTERNS:
        if pattern.search(title):
            return True
    return False


def _body_suggests_multi_role(description: str) -> bool:
    if len(NUMBERED_ROLE_BODY_PATTERN.findall(description)) >= 2:
        return True
    return False


def _strip_json_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def _call_split_llm(description: str, llm_client: Any) -> list[SplitRoleItem]:
    settings = get_settings()
    if circuit_is_open():
        raise ValueError("LLM circuit open")

    def _call() -> list[SplitRoleItem]:
        response = create_chat_completion_with_retries(
            llm_client,
            log_prefix="job_quality_split",
            model=settings.llm_model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": _SPLIT_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        "The following job listing contains multiple distinct roles "
                        "from the same company. Split it into individual roles. For "
                        "each role, extract: title (clean role name), description "
                        "(just that role's section), skills_required (list), and "
                        "requirements (list). Return JSON array. Listing:\n\n"
                        f"{description[:8000]}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )
        raw = get_completion_content(response, default="[]")
        if raw is None:
            raise ValueError("empty LLM response")
        parsed = json.loads(_strip_json_fences(raw))
        if isinstance(parsed, dict) and "roles" in parsed:
            parsed = parsed["roles"]
        if isinstance(parsed, dict) and "jobs" in parsed:
            parsed = parsed["jobs"]
        if not isinstance(parsed, list):
            raise ValueError("expected JSON array")
        return [SplitRoleItem.model_validate(item) for item in parsed]

    return await asyncio.to_thread(_call)


async def split_multi_role_listing(
    job: dict[str, Any],
    llm_client: Any | None,
) -> list[dict[str, Any]]:
    """Detect multi-role listings and split via Gemini 2.0 Flash."""
    title = str(job.get("title") or "")
    description = str(job.get("description") or "")
    if not _title_suggests_multi_role(title) and not _body_suggests_multi_role(description):
        return [job]

    if llm_client is None:
        from openai import OpenAI

        settings = get_settings()
        if not settings.openrouter_api_key:
            logger.warning("split_multi_role_listing: no OPENROUTER_API_KEY")
            return [job]
        llm_client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

    try:
        items = await _call_split_llm(description, llm_client)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        logger.warning("split_multi_role_listing failed: %s", exc)
        return [job]

    if len(items) < 2:
        return [job]

    sig = parent_listing_signature(title, job.get("company"))
    shared_keys = (
        "company",
        "location",
        "apply_url",
        "apply_email",
        "contact_phone",
        "source_url",
        "source",
        "closing_date",
        "posted_at",
    )
    out: list[dict[str, Any]] = []
    for item in items:
        row = dict(job)
        row.update(
            {
                "title": item.title[:500],
                "description": item.description[:8000],
                "skills_required": item.skills_required,
                "requirements": item.requirements,
                "parent_listing_signature": sig,
            }
        )
        for key in shared_keys:
            if key in job:
                row[key] = job[key]
        out.append(row)
    return out


def apply_ingest_quality_to_job_data(
    job_data: dict[str, Any],
    *,
    original_contact_phone: str | None,
) -> None:
    """Mutate insert payload: quality gates, normalized description, sections."""
    source_url = job_data.get("source_url")
    apply_url = job_data.get("apply_url")
    description = str(job_data.get("description") or "")

    deactivation_reasons: list[str] = []

    ok, reason = validate_source_url(source_url, apply_url)
    if not ok and reason:
        deactivation_reasons.append(reason)

    normalized_phone = normalize_contact_phone(job_data.get("contact_phone"))
    if job_data.get("contact_phone") and not normalized_phone:
        logger.warning(
            "ingest: invalid contact_phone cleared: %r",
            original_contact_phone,
        )
    job_data["contact_phone"] = normalized_phone

    desc_ok, desc_reason = description_quality_ok(description, apply_url)
    if not desc_ok and desc_reason:
        deactivation_reasons.append(desc_reason)

    normalized_md = strip_scraper_metadata(
        normalize_description_markdown(description)
    )
    job_data["description"] = normalized_md
    job_data["description_markdown"] = normalized_md
    job_data.update(extract_sections(normalized_md))

    if deactivation_reasons:
        job_data["is_active"] = False
        job_data["deactivation_reason"] = ",".join(deactivation_reasons)
