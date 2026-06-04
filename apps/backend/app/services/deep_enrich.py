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
from openai import APIStatusError, OpenAI
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
    APPLY_PATH_DEACTIVATION_REASONS,
    has_valid_apply_path,
    apply_ingest_quality_to_job_data,
    extract_sections,
    normalize_contact_phone,
    normalize_description_markdown,
    parent_listing_signature,
)
from app.services.embedding import generate_embedding
from app.services.gemini_direct import QuotaExhaustedError, generate_json
from app.services.openrouter_helpers import (
    create_chat_completion_with_retries,
    get_completion_content,
)

logger = logging.getLogger(__name__)

# Gemini response_schema requires `items` on every array (see INVALID_ARGUMENT).
DEEP_ENRICH_JOB_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "company": {"type": "string"},
        "location": {"type": "string"},
        "description_md": {"type": "string"},
        "requirements": {"type": "array", "items": {"type": "string"}},
        "skills_required": {"type": "array", "items": {"type": "string"}},
        "apply_url": {"type": "string"},
        "apply_email": {"type": "string"},
        "contact_phone": {"type": "string"},
        "closing_date": {"type": "string"},
        "salary_min": {"type": "integer"},
        "salary_max": {"type": "integer"},
    },
    "required": ["title", "description_md"],
}

DEEP_ENRICH_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "jobs": {
            "type": "array",
            "items": DEEP_ENRICH_JOB_ITEM_SCHEMA,
        },
    },
    "required": ["jobs"],
}


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


def _deep_enrich_prompt(page_text: str) -> str:
    return (
        f"{DEEP_ENRICH_LLM_PROMPT}\n\n"
        "Extract job posting(s) from this page text:\n\n"
        f"{page_text[:12000]}"
    )


def _roles_from_enrich_payload(parsed: dict[str, Any] | list[Any]) -> list[DeepEnrichRole]:
    if isinstance(parsed, list):
        jobs_raw = parsed
    else:
        jobs_raw = parsed.get("jobs") if isinstance(parsed, dict) else []
    if not isinstance(jobs_raw, list):
        raise ValueError("expected jobs array")
    return [DeepEnrichRole.model_validate(item) for item in jobs_raw]


def _call_deep_enrich_llm_openrouter(page_text: str, llm_client: Any) -> list[DeepEnrichRole]:
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
    return _roles_from_enrich_payload(parsed)


async def _call_deep_enrich_llm(
    page_text: str,
    llm_client: Any | None = None,
) -> list[DeepEnrichRole]:
    """Gemini direct for batch enrich; OpenRouter when quota hit or configured."""
    import sentry_sdk

    settings = get_settings()
    prompt = _deep_enrich_prompt(page_text)
    use_gemini = (
        settings.llm_provider_batch == "gemini_direct"
        and bool(settings.gemini_api_key.strip())
    )

    if use_gemini:
        try:
            parsed = await generate_json(
                prompt,
                schema=DEEP_ENRICH_JSON_SCHEMA,
                max_tokens=8192,
                feature="deep_enrich",
            )
            return _roles_from_enrich_payload(parsed)
        except QuotaExhaustedError:
            sentry_sdk.add_breadcrumb(
                category="llm",
                message="deep_enrich.openrouter_fallback",
                level="warning",
                data={"provider": "openrouter", "reason": "quota"},
            )
        except Exception as exc:
            logger.warning("deep_enrich gemini_direct failed: %s", exc)
            raise ValueError(f"gemini_direct failed: {exc}") from exc

    if not settings.openrouter_api_key.strip():
        raise ValueError("No LLM provider available for deep_enrich")

    if llm_client is None:
        llm_client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    return await asyncio.to_thread(
        _call_deep_enrich_llm_openrouter, page_text, llm_client
    )


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
    if has_valid_apply_path(patch)[0]:
        reason = str(patch.get("deactivation_reason") or "")
        if reason in APPLY_PATH_DEACTIVATION_REASONS:
            patch["deactivation_reason"] = None
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

    settings = get_settings()
    has_llm = bool(settings.gemini_api_key.strip()) or bool(
        settings.openrouter_api_key.strip()
    )
    if not has_llm:
        _log_enrich(
            supabase,
            job_id=job_id,
            outcome="failed",
            detail="GEMINI_API_KEY and OPENROUTER_API_KEY not set",
        )
        return "failed"

    try:
        roles = await _call_deep_enrich_llm(page_text, llm_client)
    except (json.JSONDecodeError, ValidationError, ValueError, APIStatusError) as exc:
        _log_enrich(
            supabase,
            job_id=job_id,
            outcome="failed",
            detail=f"llm: {exc}",
        )
        return "failed"
    except Exception as exc:
        logger.exception("deep_enrich unexpected failure for %s", job_id)
        _log_enrich(
            supabase,
            job_id=job_id,
            outcome="failed",
            detail=f"llm: {type(exc).__name__}: {exc}"[:500],
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


_DEEP_ENRICH_SELECT = (
    "id, title, company, location, description, source_url, apply_url, "
    "apply_email, contact_phone, source, posted_at, closing_date, "
    "created_at, deep_enriched_at, salary_min, salary_max, is_active, "
    "is_review_required"
)


def filter_deep_enrich_candidates(
    rows: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Rows with fetchable source_url that still need a deep-enrich pass."""
    eligible = [
        r
        for r in rows
        if _needs_deep_enrich(r) and (_resolve_fetch_url(r) is not None)
    ]
    return eligible[:limit]


async def run_deep_enrich_tick(
    supabase: Any,
    *,
    limit: int = 25,
    dry_run: bool = False,
    include_review_queue: bool = True,
) -> dict[str, int]:
    """Process up to ``limit`` jobs pending deep enrichment.

    When ``include_review_queue`` is true (default), also selects rows with
    ``is_review_required=true`` so scraper ingest can clear the admin queue
    after fetching full listing pages (apply path + deadline).
    """
    query = (
        supabase.table("jobs")
        .select(_DEEP_ENRICH_SELECT)
        .order("created_at", desc=True)
        .limit(max(limit * 5, limit))
    )
    if include_review_queue:
        query = query.or_("is_active.eq.true,is_review_required.eq.true")
    else:
        query = query.eq("is_active", True)
    result = query.execute()
    rows = filter_deep_enrich_candidates(result.data or [], limit=limit)

    stats = {"enriched": 0, "split": 0, "failed": 0, "skipped": 0, "attempted": 0}
    delay = get_settings().deep_enrich_inter_job_delay_sec
    for idx, row in enumerate(rows):
        stats["attempted"] += 1
        outcome = await enrich_job_deep(supabase, row, dry_run=dry_run)
        if outcome == "enriched":
            stats["enriched"] += 1
        elif outcome == "split":
            stats["split"] += 1
        elif outcome == "skipped":
            stats["skipped"] += 1
        else:
            stats["failed"] += 1
        if delay > 0 and idx < len(rows) - 1:
            await asyncio.sleep(delay)
    return stats


async def schedule_post_ingest_deep_enrich(
    supabase: Any,
    *,
    ingested_count: int,
) -> dict[str, int]:
    """Fire-and-forget helper after bulk scraper ingest (budget-capped)."""
    empty = {"enriched": 0, "split": 0, "failed": 0, "skipped": 0, "attempted": 0}
    if ingested_count <= 0:
        return empty
    settings = get_settings()
    if not settings.post_ingest_deep_enrich_enabled:
        logger.info(
            "post_ingest deep_enrich skipped (POST_INGEST_DEEP_ENRICH_ENABLED=false)"
        )
        return empty
    cap = max(1, settings.post_ingest_deep_enrich_max_limit)
    limit = min(max(ingested_count, 1), cap)
    try:
        stats = await run_deep_enrich_tick(
            supabase,
            limit=limit,
            include_review_queue=True,
        )
        logger.info("post_ingest deep_enrich tick limit=%s stats=%s", limit, stats)
        return stats
    except Exception:
        logger.warning("post_ingest deep_enrich tick failed", exc_info=True)
        return empty
