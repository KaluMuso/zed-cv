"""CV upload, analysis, and generation routes."""
import hashlib
import re
import uuid
from typing import Optional

from pydantic import BaseModel, Field, model_validator
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File

from app.core.deps import get_supabase, get_current_user, get_current_user_id, is_superadmin
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.schemas.cv_sections import CVSections
from app.services.cv_parser import extract_text_from_file, parse_cv_with_llm
from app.services.cv_generator import analyze_cv, generate_cv_structured
from app.services.embedding import generate_embedding
from app.services.email import send_welcome_email
from app.services.skill_resolver import resolve_skill_ids
from app.services.preferences_auto_populate import auto_populate_from_cv
from app.services.user_profile_enricher import (
    build_user_profile_patch,
    enrich_user_profile,
)

router = APIRouter(prefix="/cv", tags=["CV"])


class CVAnalysisResponse(BaseModel):
    overall: int
    skills: int
    format: int
    impact: int
    strengths: list[str]
    improvements: list[str]
    cached: bool = False


class CVGenerateBody(BaseModel):
    job_id: Optional[str] = None
    job_title: Optional[str] = Field(None, max_length=500)
    company: Optional[str] = Field(None, max_length=255)
    job_description: Optional[str] = Field(None, max_length=10000)

    @model_validator(mode="after")
    def _require_target(self):
        if not self.job_id and not self.job_title:
            raise ValueError("Provide either job_id or job_title")
        return self


class CVGenerateResponse(BaseModel):
    cv_generation_id: str
    content: str  # rendered plain text — kept for legacy clients / clipboard copy
    word_count: int
    job_title: str
    company: Optional[str] = None
    # Structured shape (task #59). Frontend templates consume this directly
    # to skip a free-text reparse. Optional in the response type because
    # the field is null on legacy cv_generations rows read from history.
    sections: Optional[CVSections] = None


class CVGenerationSummary(BaseModel):
    """One row in the user's generation history."""
    id: str
    job_title: str
    company: Optional[str] = None
    word_count: int = 0
    created_at: Optional[str] = None


class CVGenerationsListResponse(BaseModel):
    generations: list[CVGenerationSummary]


class CVGenerationDetail(BaseModel):
    """Full payload for re-loading a past generation into the editor."""
    id: str
    job_title: str
    company: Optional[str] = None
    content: str
    word_count: int = 0
    created_at: Optional[str] = None
    # Structured shape (task #59). Null on rows created before structured
    # generation shipped — frontend falls back to parseCv.ts on the
    # `content` text for those.
    sections: Optional[CVSections] = None


_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")


def _safe_filename(name: str) -> str:
    """Strip path traversal, control chars, and oddballs from an uploaded filename.

    Strips leading dots so a hostile name like "../../etc/passwd" or ".bashrc"
    can't escape the cvs/{user_id}/ prefix or land as a hidden file. Falls back
    to a uuid-based name when the input is empty after sanitization.
    """
    cleaned = _FILENAME_SAFE_RE.sub("_", name).lstrip(".")[:200]
    return cleaned or f"cv-{uuid.uuid4().hex}"


ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "image/jpeg": "jpg",
    "image/png": "png",
}

MAX_FILE_SIZE = 5 * 1024 * 1024


# ── task #77: libmagic-based content sniffing ───────────────────────────
# Set of MIME strings the LIBMAGIC sniffer might legitimately return for
# each accepted file kind. We match against this rather than the raw
# Content-Type header so a renamed .exe → .pdf is caught even though the
# browser/curl reports application/pdf. docx is a zip container — many
# libmagic builds report application/zip (or sometimes
# application/octet-stream) instead of the full OOXML MIME, so we
# accept both. Anything not in this map is rejected.
_SNIFFED_MIME_BY_TYPE: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        # Some older libmagic builds on minimal Linux images fall back
        # to a generic binary type for zip-based formats. Keep it in
        # the docx whitelist; the file_type is already gated by the
        # claimed Content-Type before we reach this check.
        "application/octet-stream",
    },
    "jpg": {"image/jpeg"},
    "png": {"image/png"},
}


def _sniff_mime(file_bytes: bytes) -> str:
    """Return the libmagic MIME for the first 4096 bytes of `file_bytes`.

    Isolated as a helper so tests can monkey-patch it without needing
    libmagic installed on the test host. Imports `magic` lazily so a
    missing libmagic shared library only blows up on actual uploads,
    not at module import time.
    """
    import magic
    return magic.from_buffer(file_bytes[:4096], mime=True)


def _verify_file_type(file_bytes: bytes, claimed_file_type: str) -> str | None:
    """Return None if `file_bytes` actually IS the claimed type; else a
    user-facing error string. The 400 error message intentionally names
    what we saw vs what was claimed so a developer hitting this in dev
    can diagnose without a stack trace."""
    expected = _SNIFFED_MIME_BY_TYPE.get(claimed_file_type)
    if not expected:
        return f"Unknown file type: {claimed_file_type}"
    try:
        sniffed = _sniff_mime(file_bytes)
    except Exception as exc:  # noqa: BLE001
        # libmagic missing or buggy on this host. Fail loud — we'd rather
        # block uploads than silently disable the sanitisation. A 500
        # would be confusing; a 503 communicates "infra problem, try
        # later" which matches reality.
        raise HTTPException(
            status_code=503,
            detail=f"File content verification is unavailable: {exc}",
        )
    if sniffed not in expected:
        return (
            f"File contents look like '{sniffed}', not '{claimed_file_type}'. "
            "This file appears to have been renamed; please upload the "
            "original document."
        )
    return None


# ai_cache helpers.
# The ai_cache table is keyed by SHA-256 of (operation:model:input).
# Lookups are best-effort - any failure (RLS, network, unknown column)
# falls back to a real API call. We never let cache plumbing crash
# a user's upload. cache_type CHECK was widened in migration 011 to
# include "cv_parse" and "embedding" so the INSERT here won't 23514.
def _cache_get(supabase, cache_key: str):
    """Return the cached result for this key, or None on miss/error."""
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


def _cache_put(supabase, cache_key: str, cache_type: str, input_hash: str, result, model: str) -> None:
    """Store a cache entry. Swallows duplicate-key errors silently.

    `cache_type` is validated via `validate_cache_type` — invalid values
    raise ValueError instead of silently writing bad data (migration 013
    dropped the SQL CHECK that used to catch this).
    """
    from app.schemas.db_enums import validate_cache_type
    try:
        supabase.table("ai_cache").insert({
            "cache_key": cache_key,
            "cache_type": validate_cache_type(cache_type),
            "input_hash": input_hash,
            "result": result,
            "model": model,
        }).execute()
    except Exception:
        pass


def _queue_for_later(
    *,
    supabase,
    user_id: str,
    content_type: str,
    file_type: str,
    file_bytes: bytes,
    file_filename: str | None,
    raw_text: str,
    reason: str,
    detail: str,
):
    """Graceful-degrade path for /cv/upload.

    Uploads the file to storage so the user's bytes aren't lost, inserts
    a row into cv_upload_queue, and returns a 202 with a friendly message.
    The drain endpoint (POST /admin/cv-queue/drain) processes the queue
    once Gemini quota resets (typically the next UTC day).

    Logs but never raises — the whole point is that this path absorbs the
    error gracefully. Failures here fall through to a 503 in the caller.
    """
    import logging
    storage_path = f"cvs/{user_id}/{_safe_filename(file_filename or '')}"
    try:
        # upsert='true' so a re-queue for the same filename doesn't 400
        # with Duplicate — same root cause as the 2026-05-13 /cv/upload
        # outage, see the comment on the corresponding upload call below.
        supabase.storage.from_("documents").upload(
            storage_path,
            file_bytes,
            {"content-type": content_type, "upsert": "true"},
        )
    except Exception as e:
        logging.error("cv_upload_queue: storage upload failed for %s: %s", user_id, e)
        # Fall through — better to error than silently lose the upload.
        raise HTTPException(
            status_code=503,
            detail=(
                "AI service is busy and the fallback queue couldn't accept "
                "your upload either. Please try again in a few hours."
            ),
        )

    # Queue status validated via the enum (migration 013 dropped the SQL CHECK).
    from app.schemas.db_enums import QueueStatus
    queue_row = supabase.table("cv_upload_queue").insert({
        "user_id": user_id,
        "file_path": storage_path,
        "file_type": file_type,
        "raw_text": raw_text[:10000],
        "status": QueueStatus.queued.value,
        "reason": reason,
    }).execute()
    if not queue_row.data:
        logging.error("cv_upload_queue: insert failed for user %s", user_id)
        raise HTTPException(
            status_code=503,
            detail="Could not queue your CV right now. Please try again later.",
        )

    logging.info(
        "cv_upload_queue: queued cv for user=%s reason=%s detail=%s",
        user_id, reason, detail[:120],
    )
    # 202 Accepted is the right status code for "received but not yet
    # processed". Frontend reads `queued: True` to swap the success
    # toast for a "we'll process this shortly" message.
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=202,
        content={
            "queued": True,
            "queue_id": queue_row.data[0]["id"],
            "message": (
                "AI service is at capacity right now. We've saved your CV "
                "and will process it within a few hours. You'll see your "
                "matches as soon as it's done."
            ),
        },
    )


@router.post("/upload")
@limiter.limit("5/minute")
async def upload_cv(request: Request, file: UploadFile = File(...), user_id: str = Depends(get_current_user_id), supabase=Depends(get_supabase)):
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported file type: {content_type}. Accepted: PDF, DOCX, JPG, PNG")
    file_type = ALLOWED_TYPES[content_type]

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="File too large. Maximum 5MB.")

    # task #77: don't trust the Content-Type header. Sniff the first 4096
    # bytes with libmagic and reject anything whose real content type
    # doesn't match the claimed extension — catches a .exe / .sh / etc.
    # renamed to .pdf, which the previous header-only check waved through.
    mime_err = _verify_file_type(file_bytes, file_type)
    if mime_err:
        raise HTTPException(status_code=400, detail=mime_err)

    try:
        raw_text = await extract_text_from_file(file_bytes, file_type)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not raw_text or len(raw_text.strip()) < 50:
        raise HTTPException(status_code=422, detail="Could not extract enough text. Please upload a clearer document.")

    # ai_cache lookup for parse + embedding.
    # Same CV text -> Gemini is deterministic enough to cache (temperature 0.1).
    # Hashing the first 10k chars mirrors what we store in cvs.raw_text so
    # cache keys are stable across re-uploads. Keyed by model so swapping
    # LLM_MODEL or EMBEDDING_MODEL invalidates cleanly.
    settings = get_settings()
    text_hash = hashlib.sha256(raw_text[:10000].encode("utf-8")).hexdigest()
    parse_cache_key = f"cv_parse:{settings.llm_model}:{text_hash}"
    embed_cache_key = f"embedding:{settings.embedding_model}:{settings.embedding_dimensions}:{text_hash}"

    # Try parse + embed normally. On rate-limit-shaped failures (Gemini
    # daily token cap exhausted), queue the upload via the cv_upload_queue
    # table instead of 503-ing. The user gets a 202 with an ETA message
    # and we drain the queue after midnight UTC when caps reset.
    # We also pre-upload the file to storage so the queued row references
    # something durable — file_bytes isn't kept anywhere otherwise.
    parsed = _cache_get(supabase, parse_cache_key)
    if parsed is None:
        try:
            parsed = await parse_cv_with_llm(raw_text)
        except ValueError as e:
            msg = str(e).lower()
            if "busy" in msg or "rate" in msg or "temporarily" in msg:
                return _queue_for_later(
                    supabase=supabase, user_id=user_id, content_type=content_type,
                    file_type=file_type, file_bytes=file_bytes, file_filename=file.filename,
                    raw_text=raw_text, reason="gemini_rate_limit_parse", detail=str(e),
                )
            raise HTTPException(status_code=503, detail=str(e))
        _cache_put(supabase, parse_cache_key, "cv_parse", text_hash, parsed, settings.llm_model)

    embedding = _cache_get(supabase, embed_cache_key)
    if embedding is None:
        try:
            embedding = await generate_embedding(raw_text)
        except ValueError as e:
            msg = str(e).lower()
            if "busy" in msg or "rate" in msg or "temporarily" in msg:
                return _queue_for_later(
                    supabase=supabase, user_id=user_id, content_type=content_type,
                    file_type=file_type, file_bytes=file_bytes, file_filename=file.filename,
                    raw_text=raw_text, reason="gemini_rate_limit_embed", detail=str(e),
                )
            raise HTTPException(status_code=503, detail=str(e))
        _cache_put(supabase, embed_cache_key, "embedding", text_hash, embedding, settings.embedding_model)

    storage_path = f"cvs/{user_id}/{_safe_filename(file.filename or '')}"
    # upsert='true' makes the upload overwrite an existing object at the same
    # path instead of raising StorageException(Duplicate). Without it, a user
    # replacing their CV with the same filename gets a 400 from storage that
    # bubbles up as an uvicorn 500 with text/plain body — which bypasses CORS
    # middleware and surfaces in the browser as a misleading CORS error.
    # See the 2026-05-13 outage on /cv/upload.
    supabase.storage.from_("documents").upload(
        storage_path,
        file_bytes,
        {"content-type": content_type, "upsert": "true"},
    )

    existing_cvs = supabase.table("cvs").select("id", count="exact").eq("user_id", user_id).limit(1).execute()
    is_first_upload = (existing_cvs.count or 0) == 0

    supabase.table("cvs").update({"is_primary": False}).eq("user_id", user_id).eq("is_primary", True).execute()

    result = supabase.table("cvs").insert({
        "user_id": user_id, "file_url": storage_path, "file_type": file_type,
        "raw_text": raw_text[:10000], "parsed_data": parsed, "embedding": embedding,
        "parsing_confidence": parsed.get("confidence", 0), "is_primary": True,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to store CV")
    cv_id = result.data[0]["id"]

    parsed_skills = parsed.get("skills", [])
    if parsed_skills:
        # Phase 2 Initiative #1: route every LLM-extracted skill through
        # the hybrid resolver (skill_resolver.py) instead of a raw
        # name-keyed upsert. The resolver canonicalizes via three passes
        # (exact -> trgm -> vector) and only auto-inserts when none of
        # them hit. canonical_of is followed transparently so a CV with
        # "Postgres" + "PostgreSQL" + "postgres" yields ONE user_skills
        # row, not three. Pre-resolver behaviour was to insert all three
        # names verbatim and end up with three user_skills rows.
        skill_ids = await resolve_skill_ids(
            parsed_skills,
            supabase=supabase,
            source="cv_upload",
            user_id=user_id,
        )
        if skill_ids:
            # ignore_duplicates preserves an existing user_skills row's
            # `source` — don't overwrite a manual entry with cv_parse.
            supabase.table("user_skills").upsert(
                [
                    {"user_id": user_id, "skill_id": sid, "source": "cv_parse"}
                    for sid in skill_ids
                ],
                on_conflict="user_id,skill_id",
                ignore_duplicates=True,
            ).execute()

    profile_update = {}
    for field in ["full_name", "email", "location"]:
        if parsed.get(field):
            profile_update[field] = parsed[field]
    if parsed.get("years_experience") is not None:
        profile_update["years_experience"] = parsed["years_experience"]

    try:
        user_row = (
            supabase.table("users")
            .select(
                "years_experience, seniority_level, highest_qualification, qualifications"
            )
            .eq("id", user_id)
            .single()
            .execute()
        )
        current_user = user_row.data if isinstance(user_row.data, dict) else {}
        if profile_update.get("years_experience") is not None:
            current_user = {**current_user, "years_experience": profile_update["years_experience"]}
        profile_enrichment = await enrich_user_profile(cv_text=raw_text)
        profile_update.update(
            build_user_profile_patch(profile_enrichment, user_row=current_user)
        )
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "user profile enrichment failed for user=%s", user_id, exc_info=True
        )

    if profile_update:
        supabase.table("users").update(profile_update).eq("id", user_id).execute()

    # Phase 2 Initiative #4 — auto-populate user_preferences from the
    # parsed CV. Isolated in its own try/except: an auto-populate
    # failure (DB hiccup, malformed parsed_data shape) must NOT cause
    # the whole upload to fail, because the upload's main job — store
    # the CV bytes + skill extraction — has already succeeded by this
    # point and rolling back would be worse than skipping the
    # preferences fill.
    try:
        await auto_populate_from_cv(user_id, parsed, supabase=supabase)
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "preferences auto-populate failed for user=%s cv=%s",
            user_id, cv_id, exc_info=True,
        )

    if is_first_upload:
        try:
            await send_welcome_email(user_id, supabase)
        except Exception:
            pass

    return {"cv_id": cv_id, "parsed_skills": parsed.get("skills", []), "experience_summary": parsed.get("experience_summary", ""), "parsing_confidence": parsed.get("confidence", 0)}


def _get_primary_cv(supabase, user_id: str) -> dict | None:
    res = (
        supabase.table("cvs")
        .select("id, raw_text")
        .eq("user_id", user_id)
        .eq("is_primary", True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    row = res.data[0]
    if not row.get("raw_text"):
        return None
    return row


@router.post("/analyze", response_model=CVAnalysisResponse)
@limiter.limit("10/minute")
async def analyze(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    cv = _get_primary_cv(supabase, user_id)
    if not cv:
        raise HTTPException(
            status_code=422,
            detail="Upload a CV first. We need your CV text to run analysis.",
        )

    cache_key = hashlib.sha256(f"cv_analysis:{cv['id']}".encode()).hexdigest()
    cached = (
        supabase.table("ai_cache")
        .select("result")
        .eq("cache_key", cache_key)
        .limit(1)
        .execute()
    )
    if cached.data:
        result = cached.data[0]["result"]
        return CVAnalysisResponse(cached=True, **result)

    try:
        result = await analyze_cv(cv["raw_text"])
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # cache_type validated via the enum (migration 013 dropped the SQL CHECK).
    from app.schemas.db_enums import CacheType
    supabase.table("ai_cache").insert({
        "cache_key": cache_key,
        "cache_type": CacheType.cv_analysis.value,
        "input_hash": hashlib.sha256((cv.get("raw_text") or "").encode()).hexdigest(),
        "result": result,
        "model": "google/gemini-flash-2.0",
    }).execute()

    return CVAnalysisResponse(cached=False, **result)


@router.post("/generate", response_model=CVGenerateResponse)
@limiter.limit("5/minute")
async def generate(
    request: Request,
    body: CVGenerateBody,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    user_id = current_user["id"]

    # Tier check: Starter or Professional. Superadmin bypasses.
    if not is_superadmin(current_user):
        sub = (
            supabase.table("subscriptions")
            .select("tier, status")
            .eq("user_id", user_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        tier = (sub.data[0].get("tier") if sub.data else None) or "free"
        if tier not in ("starter", "professional", "super_standard"):
            raise HTTPException(
                status_code=403,
                detail="Tailored CV generation requires the Starter or higher plan. "
                       "Upgrade at /pricing.",
            )

    cv = _get_primary_cv(supabase, user_id)
    if not cv:
        raise HTTPException(
            status_code=422,
            detail="Upload a CV first. We need your CV text to generate a tailored version.",
        )

    job_title = body.job_title
    company = body.company
    job_description = body.job_description

    if body.job_id and not job_title:
        job_res = (
            supabase.table("jobs")
            .select("title, company, description")
            .eq("id", body.job_id)
            .limit(1)
            .execute()
        )
        if not job_res.data:
            raise HTTPException(status_code=404, detail="Job not found")
        job = job_res.data[0]
        job_title = job["title"]
        company = company or job.get("company")
        job_description = job_description or job.get("description")

    try:
        result = await generate_cv_structured(
            cv_text=cv["raw_text"],
            job_title=job_title,
            company=company,
            job_description=job_description,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Store the structured shape alongside the rendered text in
    # cv_generations.metadata so a /generations/{id} re-open can return it
    # without re-running the LLM. The text content stays in the existing
    # `content` column for backwards compat (history list, clipboard copy).
    structured_sections: CVSections = result["sections"]
    metadata: dict = {"sections": structured_sections.model_dump(mode="json")}
    if body.job_id:
        metadata["job_id"] = body.job_id

    insert_res = supabase.table("cv_generations").insert({
        "user_id": user_id,
        "cv_id": cv["id"],
        "job_title": job_title,
        "company": company,
        "content": result["content"],
        "word_count": result["word_count"],
        "metadata": metadata,
    }).execute()

    gen_id = insert_res.data[0]["id"] if insert_res.data else "unknown"
    return CVGenerateResponse(
        cv_generation_id=gen_id,
        content=result["content"],
        word_count=result["word_count"],
        job_title=job_title,
        company=company,
        sections=structured_sections,
    )


# History endpoints. The redesigned /profile?tab=cv-generator UI keeps a
# history panel so users can re-open and re-export past generations without
# re-running the LLM (saves OpenRouter spend). RLS on cv_generations already
# scopes rows to auth.uid(), but we also filter by user_id for clarity.
@router.get("/generations", response_model=CVGenerationsListResponse)
async def list_generations(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
    limit: int = 50,
):
    limit = max(1, min(limit, 100))
    res = (
        supabase.table("cv_generations")
        .select("id, job_title, company, word_count, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    return CVGenerationsListResponse(
        generations=[
            CVGenerationSummary(
                id=str(r["id"]),
                job_title=r.get("job_title") or "",
                company=r.get("company"),
                word_count=r.get("word_count") or 0,
                created_at=r.get("created_at"),
            )
            for r in rows
        ]
    )


@router.get("/generations/{generation_id}", response_model=CVGenerationDetail)
async def get_generation(
    generation_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    res = (
        supabase.table("cv_generations")
        .select("id, job_title, company, content, word_count, created_at, metadata")
        .eq("id", generation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Generation not found")
    r = res.data[0]

    # Pre-task-#59 rows have no "sections" key in metadata; frontend falls
    # back to parseCv.ts on the content text for those. Malformed metadata
    # is logged and treated as null rather than 500-ing this endpoint.
    sections: Optional[CVSections] = None
    raw_meta = r.get("metadata") or {}
    if isinstance(raw_meta, dict) and raw_meta.get("sections"):
        try:
            sections = CVSections.model_validate(raw_meta["sections"])
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "cv_generations row %s has malformed sections metadata: %s",
                r["id"], e,
            )
            sections = None

    return CVGenerationDetail(
        id=str(r["id"]),
        job_title=r.get("job_title") or "",
        company=r.get("company"),
        content=r.get("content") or "",
        word_count=r.get("word_count") or 0,
        created_at=r.get("created_at"),
        sections=sections,
    )
