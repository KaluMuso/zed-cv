"""Deep-enrich pipeline: fetch source_url, LLM extract, split, HTML render."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import date, datetime, timezone
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.services.deep_link_parsers.base import sanitize_listing_source_url
from app.services.job_activation import apply_review_state_to_row, compute_review_state
from app.services.job_page_text_extractor import extract_page_text_for_description
from app.services.skill_resolver import resolve_skill_ids
from app.core.config import get_settings
from app.services.description_body_extractor import merge_description_extraction
from app.services.html_render import render_job_description_html
from app.services.job_publication import apply_contact_activation
from app.services.job_quality import (
    apply_ingest_quality_to_job_data,
    extract_sections,
    normalize_contact_phone,
    normalize_description_markdown,
    parent_listing_signature,
)
from app.services.embedding import generate_embedding
from app.services.openrouter_helpers import (
    create_chat_completion_with_retries,
    get_completion_content,
)
logger = logging.getLogger(__name__)


def _fingerprint(title: str, company: str | None, description: str) -> str:
    return hashlib.sha256(
        f"{title}|{company or ''}|{description[:200]}".lower().encode()
    ).hexdigest()


async def _attach_job_skills(supabase: Any, job_id: str, skill_names: list[str]) -> None:
    skill_ids = await resolve_skill_ids(
        skill_names,
        supabase=supabase,
        source="deep_enrich",
    )
    for skill_id in skill_ids:
        try:
            supabase.table("job_skills").insert(
                {"job_id": job_id, "skill_id": skill_id}
            ).execute()
        except Exception:
            pass


_FETCH_TIMEOUT = 15.0
_HTTP_SCHEMES = ("http://", "https://")

DEEP_ENRICH_LLM_PROMPT = """
Read this job posting page and extract a high-fidelity job spec.
If multiple distinct roles are listed (e.g. "Bricklayer AND Carpenter AND Plumber"),
return them as separate items. Each item must include:

- title (clean role name)
- company
- location (normalized to Zambian city or null)
- description_md (FULL job description in markdown, at least 400 characters when
  the page supports it — do not summarize away duties or requirements. Keep section
  headers like "## Responsibilities", "## Requirements", "## Qualifications",
  "## Benefits", "## How to apply", "## About the company". Use blank lines between
  sections. Use bullet lists for duties. Use *italics* for emphasis and **bold**
  for key terms only sparingly)
- requirements (array of explicit requirements)
- skills_required (array of named technical/professional skills — at minimum 5
  if the description supports it; max 15)
- apply_url (real employer URL if visible; null if only an aggregator URL)
- apply_email
- contact_phone (Zambian E.164 format only: +260[95|96|97|76|77|75]XXXXXXX
  or +260 211 XXXXXX landline; otherwise null)
- closing_date (ISO date)
- salary_min / salary_max (integers in ZMW; null if unspecified)

Return as JSON: {"jobs": [...]}

Skip if not a real Zambian job posting. Return {"jobs": []} only if truly empty.
""".strip()

def _deep_enrich_model() -> str:
    return get_settings().llm_model


class DeepEnrichRole(BaseModel):
    title: str = Field(..., min_length=2, max_length=500)
    company: str | None = None
    location: str | None = None
    description_md: str = Field(..., min_length=20)
    requirements: list[str] = Field(default_factory=list)
    skills_required: list[str] = Field(default_factory=list)
    apply_url: str | None = None
    apply_email: str | None = None
    contact_phone: str | None = None
    closing_date: date | None = None
    salary_min: int | None = Field(None, ge=0)
    salary_max: int | None = Field(None, ge=0)

    @field_validator("requirements", "skills_required", mode="before")
    @classmethod
    def _coerce_lists(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        if not isinstance(v, list):
            return []
        return [str(x).strip() for x in v if str(x).strip()]


def _http_url(url: str | None) -> bool:
    if not url:
        return False
    lower = url.strip().lower()
    return lower.startswith(_HTTP_SCHEMES)


def _resolve_fetch_url(row: dict[str, Any]) -> str | None:
    source = sanitize_listing_source_url((row.get("source_url") or "").strip() or None)
    if source and _http_url(source):
        return source
    apply_url = sanitize_listing_source_url((row.get("apply_url") or "").strip() or None)
    if apply_url and _http_url(apply_url):
        host = (urlparse(apply_url).netloc or "").lower()
        aggregator_hints = (
            "jobwebzambia",
            "gozambiajobs",
            "jobsearchzambia",
            "everjobs",
            "linkedin.com",
            "indeed.com",
        )
        if host and not any(h in host for h in aggregator_hints):
            return apply_url
    return None


def _zmw_to_ngwee(value: int | None) -> int | None:
    if value is None:
        return None
    return int(value) * 100


def _strip_json_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def fetch_source_page(url: str) -> tuple[int, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ZedApplyBot/1.0; +https://zedapply.com)",
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(
        timeout=_FETCH_TIMEOUT,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url, headers=headers)
        return resp.status_code, resp.text


def _call_deep_enrich_llm(page_text: str, llm_client: Any) -> list[DeepEnrichRole]:
    settings = get_settings()
    response = create_chat_completion_with_retries(
        llm_client,
        log_prefix="deep_enrich",
        model=_deep_enrich_model(),
        max_tokens=8192,
        messages=[
            {"role": "system", "content": DEEP_ENRICH_LLM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Extract job posting(s) from this page text:\n\n"
                    f"{page_text[:12000]}"
                ),
            },
        ],
        response_format={"type": "json_object"},
    )
    raw = get_completion_content(response, default='{"jobs": []}')
    if raw is None:
        raise ValueError("empty LLM response")
    parsed = json.loads(_strip_json_fences(raw))
    if isinstance(parsed, list):
        jobs_raw = parsed
    else:
        jobs_raw = parsed.get("jobs") if isinstance(parsed, dict) else []
    if not isinstance(jobs_raw, list):
        raise ValueError("expected jobs array")
    return [DeepEnrichRole.model_validate(item) for item in jobs_raw]


def _role_to_job_patch(
    role: DeepEnrichRole,
    parent: dict[str, Any],
    *,
    parent_sig: str | None = None,
) -> dict[str, Any]:
    description = normalize_description_markdown(role.description_md)
    patch: dict[str, Any] = {
        "title": role.title[:500],
        "company": role.company or parent.get("company"),
        "location": role.location or parent.get("location"),
        "description": description,
        "description_markdown": description,
        "requirements": role.requirements[:50],
        "skills_required": role.skills_required[:15],
        "apply_url": role.apply_url or parent.get("apply_url"),
        "apply_email": role.apply_email or parent.get("apply_email"),
        "contact_phone": normalize_contact_phone(role.contact_phone)
        or parent.get("contact_phone"),
        "source_url": sanitize_listing_source_url(
            str(parent.get("source_url") or "") or None
        ),
        "source": parent.get("source") or "scraper",
        "posted_at": parent.get("posted_at"),
        "closing_date": (
            role.closing_date.isoformat()
            if role.closing_date
            else parent.get("closing_date")
        ),
        "salary_min": _zmw_to_ngwee(role.salary_min) or parent.get("salary_min"),
        "salary_max": _zmw_to_ngwee(role.salary_max) or parent.get("salary_max"),
        "deep_enriched_at": datetime.now(timezone.utc).isoformat(),
    }
    if parent_sig:
        patch["parent_listing_signature"] = parent_sig
    patch.update(extract_sections(description))
    merge_description_extraction(patch, description)
    apply_ingest_quality_to_job_data(
        patch,
        original_contact_phone=role.contact_phone,
    )
    description_html, section_html = render_job_description_html(
        description,
        {
            "section_responsibilities": patch.get("section_responsibilities"),
            "section_requirements": patch.get("section_requirements"),
            "section_benefits": patch.get("section_benefits"),
            "section_how_to_apply": patch.get("section_how_to_apply"),
            "section_about": patch.get("section_about"),
        },
    )
    patch["description_html"] = description_html or None
    patch["section_html"] = section_html or None
    review = compute_review_state(
        apply_url=patch.get("apply_url"),
        apply_email=patch.get("apply_email"),
        contact_phone=patch.get("contact_phone"),
        closing_date=patch.get("closing_date"),
    )
    apply_review_state_to_row(patch, review)
    apply_contact_activation(patch)
    return patch


def _log_enrich(
    supabase: Any,
    *,
    job_id: str,
    outcome: str,
    detail: str | None = None,
    dry_run: bool = False,
) -> None:
    payload = {
        "job_id": job_id,
        "parser_name": "deep_enrich",
        "outcome": outcome,
        "detail": (detail or "")[:2000] or None,
        "dry_run": dry_run,
    }
    try:
        supabase.table("apply_url_backfill_log").insert(payload).execute()
    except Exception as exc:
        logger.warning("deep_enrich log insert failed %s: %s", job_id, exc)


async def _insert_child_job(
    supabase: Any,
    parent: dict[str, Any],
    role: DeepEnrichRole,
    *,
    parent_sig: str,
) -> str | None:
    patch = _role_to_job_patch(role, parent, parent_sig=parent_sig)
    description = str(patch.get("description") or "")
    try:
        embedding = await generate_embedding(
            f"{patch['title']} {patch.get('company') or ''} {description[:4000]}"
        )
    except Exception as exc:
        logger.warning("deep_enrich child embedding failed: %s", exc)
        return None
    patch["embedding"] = embedding
    skills = patch.pop("skills_required", [])
    fp = _fingerprint(patch["title"], patch.get("company"), description)
    existing = (
        supabase.table("job_fingerprints")
        .select("job_id")
        .eq("fingerprint", fp)
        .limit(1)
        .execute()
    )
    if existing.data:
        row0 = existing.data[0]
        return str(row0.get("job_id") or row0.get("id"))
    result = supabase.table("jobs").insert(patch).execute()
    if not result.data:
        return None
    job_id = str(result.data[0]["id"])
    supabase.table("job_fingerprints").insert(
        {"fingerprint": fp, "job_id": job_id}
    ).execute()
    await _attach_job_skills(supabase, job_id, skills)
    return job_id


async def enrich_job_deep(
    supabase: Any,
    row: dict[str, Any],
    *,
    llm_client: Any | None = None,
    dry_run: bool = False,
) -> Literal["enriched", "split", "failed", "skipped"]:
    """Run deep-enrich on one job row. Returns outcome category."""
    job_id = str(row["id"])
    fetch_url = _resolve_fetch_url(row)
    if not fetch_url:
        _log_enrich(
            supabase,
            job_id=job_id,
            outcome="failed_no_url",
            detail="no source_url or employer apply_url",
            dry_run=dry_run,
        )
        return "failed"

    if dry_run:
        _log_enrich(
            supabase,
            job_id=job_id,
            outcome="dry_run",
            detail=f"would fetch {fetch_url}",
            dry_run=True,
        )
        return "enriched"

    try:
        status, body = await fetch_source_page(fetch_url)
    except Exception as exc:
        _log_enrich(
            supabase,
            job_id=job_id,
            outcome="failed_fetch",
            detail=str(exc)[:500],
        )
        return "failed"

    if status >= 400 or not body:
        _log_enrich(
            supabase,
            job_id=job_id,
            outcome="failed_fetch",
            detail=f"HTTP {status}",
        )
        return "failed"

    page_text = extract_page_text_for_description(body, fetch_url)
    if len(page_text) < 80:
        _log_enrich(
            supabase,
            job_id=job_id,
            outcome="failed_fetch",
            detail="page text too short after strip",
        )
        return "failed"

    if llm_client is None:
        settings = get_settings()
        if not settings.openrouter_api_key:
            _log_enrich(
                supabase,
                job_id=job_id,
                outcome="failed",
                detail="OPENROUTER_API_KEY not set",
            )
            return "failed"
        llm_client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

    try:
        roles = await asyncio.to_thread(_call_deep_enrich_llm, page_text, llm_client)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        _log_enrich(
            supabase,
            job_id=job_id,
            outcome="failed",
            detail=f"llm: {exc}",
        )
        return "failed"

    if not roles:
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("jobs").update({"deep_enriched_at": now}).eq("id", job_id).execute()
        _log_enrich(supabase, job_id=job_id, outcome="skipped", detail="empty jobs array")
        return "skipped"

    if len(roles) > 1:
        sig = parent_listing_signature(
            str(row.get("title") or ""),
            row.get("company"),
        )
        child_ids: list[str] = []
        for role in roles:
            child_id = await _insert_child_job(supabase, row, role, parent_sig=sig)
            if child_id:
                child_ids.append(child_id)
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("jobs").update(
            {
                "is_active": False,
                "deactivation_reason": "split_into_children",
                "closure_reason": "Replaced by separate role listings",
                "closed_at": now,
                "deep_enriched_at": now,
            }
        ).eq("id", job_id).execute()
        _log_enrich(
            supabase,
            job_id=job_id,
            outcome="split",
            detail=f"children={','.join(child_ids)}",
        )
        return "split"

    role = roles[0]
    patch = _role_to_job_patch(role, row)
    skills = patch.pop("skills_required", [])
    description = str(patch.get("description") or "")
    try:
        embedding = await generate_embedding(
            f"{patch['title']} {patch.get('company') or ''} {description[:4000]}"
        )
        patch["embedding"] = embedding
    except Exception as exc:
        logger.warning("deep_enrich embedding failed %s: %s", job_id, exc)

    supabase.table("jobs").update(patch).eq("id", job_id).execute()
    await _attach_job_skills(supabase, job_id, skills)
    _log_enrich(supabase, job_id=job_id, outcome="enriched", detail=fetch_url)
    return "enriched"


def _needs_deep_enrich(row: dict[str, Any]) -> bool:
    enriched_at = row.get("deep_enriched_at")
    created_at = row.get("created_at")
    if enriched_at is None:
        return True
    if not created_at:
        return False
    try:
        enriched_dt = datetime.fromisoformat(str(enriched_at).replace("Z", "+00:00"))
        created_dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        return enriched_dt < created_dt
    except ValueError:
        return True


async def run_deep_enrich_tick(
    supabase: Any,
    *,
    limit: int = 25,
    dry_run: bool = False,
) -> dict[str, int]:
    """Process up to `limit` jobs pending deep enrichment."""
    result = (
        supabase.table("jobs")
        .select(
            "id, title, company, location, description, source_url, apply_url, "
            "apply_email, contact_phone, source, posted_at, closing_date, "
            "created_at, deep_enriched_at, salary_min, salary_max, is_active"
        )
        .eq("is_active", True)
        .order("created_at", desc=True)
        .limit(limit * 3)
        .execute()
    )
    rows = [
        r
        for r in (result.data or [])
        if _needs_deep_enrich(r) and (_resolve_fetch_url(r) is not None)
    ][:limit]

    stats = {"enriched": 0, "split": 0, "failed": 0, "skipped": 0}
    for row in rows:
        outcome = await enrich_job_deep(supabase, row, dry_run=dry_run)
        if outcome == "enriched":
            stats["enriched"] += 1
        elif outcome == "split":
            stats["split"] += 1
        elif outcome == "skipped":
            stats["skipped"] += 1
        else:
            stats["failed"] += 1
    return stats
