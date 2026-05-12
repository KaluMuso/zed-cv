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
from app.services.cv_parser import extract_text_from_file, parse_cv_with_llm
from app.services.cv_generator import analyze_cv, generate_cv
from app.services.embedding import generate_embedding
from app.services.email import send_welcome_email

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
    content: str
    word_count: int
    job_title: str
    company: Optional[str] = None


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
    """Store a cache entry. Swallows duplicate-key errors silently."""
    try:
        supabase.table("ai_cache").insert({
            "cache_key": cache_key,
            "cache_type": cache_type,
            "input_hash": input_hash,
            "result": result,
            "model": model,
        }).execute()
    except Exception:
        pass


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

    parsed = _cache_get(supabase, parse_cache_key)
    if parsed is None:
        try:
            parsed = await parse_cv_with_llm(raw_text)
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))
        _cache_put(supabase, parse_cache_key, "cv_parse", text_hash, parsed, settings.llm_model)

    embedding = _cache_get(supabase, embed_cache_key)
    if embedding is None:
        try:
            embedding = await generate_embedding(raw_text)
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))
        _cache_put(supabase, embed_cache_key, "embedding", text_hash, embedding, settings.embedding_model)

    storage_path = f"cvs/{user_id}/{_safe_filename(file.filename or '')}"
    supabase.storage.from_("documents").upload(storage_path, file_bytes, {"content-type": content_type})

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

    for skill_name in parsed.get("skills", []):
        skill_result = supabase.table("skills").select("id").eq("name", skill_name.lower()).limit(1).execute()
        skill_id = skill_result.data[0]["id"] if skill_result.data else None
        if not skill_id:
            alias = supabase.table("skill_aliases").select("skill_id").eq("alias", skill_name.lower()).limit(1).execute()
            skill_id = alias.data[0]["skill_id"] if alias.data else None
        if skill_id:
            supabase.table("user_skills").upsert({"user_id": user_id, "skill_id": skill_id, "source": "cv_parse"}, on_conflict="user_id,skill_id").execute()

    profile_update = {}
    for field in ["full_name", "email", "location"]:
        if parsed.get(field):
            profile_update[field] = parsed[field]
    if parsed.get("years_experience") is not None:
        profile_update["years_experience"] = parsed["years_experience"]
    if profile_update:
        supabase.table("users").update(profile_update).eq("id", user_id).execute()

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

    supabase.table("ai_cache").insert({
        "cache_key": cache_key,
        "cache_type": "cv_analysis",
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
        result = await generate_cv(
            cv_text=cv["raw_text"],
            job_title=job_title,
            company=company,
            job_description=job_description,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    insert_res = supabase.table("cv_generations").insert({
        "user_id": user_id,
        "cv_id": cv["id"],
        "job_title": job_title,
        "company": company,
        "content": result["content"],
        "word_count": result["word_count"],
        "metadata": {"job_id": body.job_id} if body.job_id else {},
    }).execute()

    gen_id = insert_res.data[0]["id"] if insert_res.data else "unknown"
    return CVGenerateResponse(
        cv_generation_id=gen_id,
        content=result["content"],
        word_count=result["word_count"],
        job_title=job_title,
        company=company,
    )
