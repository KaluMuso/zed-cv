"""Match-scoped cover letter generation, versioning, and save."""
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.deps import get_current_user, get_supabase, is_superadmin
from app.core.rate_limit import limiter
from app.core.tier_gating import FEATURE_COVER_LETTER, verify_tier_access
from app.services.cover_letter import generate_cover_letter
from app.services.cover_letter_versions import (
    assert_match_owned,
    list_cover_letter_versions,
    save_cover_letter_version,
)

router = APIRouter(prefix="/matches", tags=["Matching"])

_WORD_SOFT_LIMIT = 600


class CoverLetterVersionSummary(BaseModel):
    id: str
    version_number: int
    parent_version_id: Optional[str] = None
    generated_by: Literal["ai", "user_edit"]
    created_at: str
    label: str


class CoverLetterVersionDetail(CoverLetterVersionSummary):
    content_md: str


class CoverLetterVersionsResponse(BaseModel):
    versions: list[CoverLetterVersionDetail]
    latest: Optional[CoverLetterVersionDetail] = None


class CoverLetterSaveRequest(BaseModel):
    content_md: str = Field(..., min_length=1, max_length=50000)
    parent_version_id: Optional[str] = None
    source: Literal["ai", "user_edit"] = "user_edit"


class CoverLetterSaveResponse(BaseModel):
    id: str
    version_number: int
    generated_by: Literal["ai", "user_edit"]
    created_at: str
    word_count: int


class MatchCoverLetterGenerateResponse(BaseModel):
    content: str
    word_count: int
    version_id: str
    version_number: int


def _format_version_label(row: dict) -> str:
    created = row.get("created_at") or ""
    try:
        dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        stamp = dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        stamp = str(created)[:16]
    kind = "AI" if row.get("generated_by") == "ai" else "edited"
    return f"v{row['version_number']} — {stamp} ({kind})"


def _word_count(text: str) -> int:
    return len(text.split())


def _enforce_soft_word_limit(content_md: str) -> None:
    if _word_count(content_md) > _WORD_SOFT_LIMIT:
        raise HTTPException(
            status_code=422,
            detail=f"Cover letter exceeds {_WORD_SOFT_LIMIT} words. Shorten before saving.",
        )


@router.get(
    "/{match_id}/cover-letter/versions",
    response_model=CoverLetterVersionsResponse,
)
async def get_cover_letter_versions(
    match_id: str,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """List saved cover letter versions for a match (Professional+ editor)."""
    user_id = current_user["id"]
    await verify_tier_access(
        FEATURE_COVER_LETTER,
        user_id,
        supabase,
        is_superadmin=is_superadmin(current_user),
    )
    assert_match_owned(user_id, match_id, supabase)

    rows = list_cover_letter_versions(user_id, match_id, supabase)
    details = [
        CoverLetterVersionDetail(
            id=str(r["id"]),
            version_number=int(r["version_number"]),
            parent_version_id=(
                str(r["parent_version_id"]) if r.get("parent_version_id") else None
            ),
            generated_by=r["generated_by"],
            created_at=str(r.get("created_at") or ""),
            label=_format_version_label(r),
            content_md=r.get("content_md") or "",
        )
        for r in rows
    ]
    latest_detail = details[0] if details else None
    return CoverLetterVersionsResponse(versions=details, latest=latest_detail)


@router.post(
    "/{match_id}/cover-letter/save",
    response_model=CoverLetterSaveResponse,
)
@limiter.limit("30/minute")
async def save_cover_letter(
    request: Request,
    match_id: str,
    body: CoverLetterSaveRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """Save a new cover letter version (user edit or post-generate AI draft)."""
    user_id = current_user["id"]
    await verify_tier_access(
        FEATURE_COVER_LETTER,
        user_id,
        supabase,
        is_superadmin=is_superadmin(current_user),
    )
    assert_match_owned(user_id, match_id, supabase)
    _enforce_soft_word_limit(body.content_md)

    row = save_cover_letter_version(
        user_id=user_id,
        match_id=match_id,
        content_md=body.content_md,
        generated_by=body.source,
        parent_version_id=body.parent_version_id,
        supabase=supabase,
    )
    content = row.get("content_md") or ""
    return CoverLetterSaveResponse(
        id=str(row["id"]),
        version_number=int(row["version_number"]),
        generated_by=row["generated_by"],
        created_at=str(row.get("created_at") or ""),
        word_count=_word_count(content),
    )


@router.post(
    "/{match_id}/cover-letter/generate",
    response_model=MatchCoverLetterGenerateResponse,
)
@limiter.limit("5/minute")
async def generate_cover_letter_for_match(
    request: Request,
    match_id: str,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """Generate a tailored cover letter and persist as a new AI version."""
    user_id = current_user["id"]
    await verify_tier_access(
        FEATURE_COVER_LETTER,
        user_id,
        supabase,
        is_superadmin=is_superadmin(current_user),
    )

    match_row = assert_match_owned(user_id, match_id, supabase)
    job_id = match_row.get("job_id")
    if not job_id:
        raise HTTPException(status_code=404, detail="Job not found for this match")

    job_res = (
        supabase.table("jobs")
        .select("title, company, description")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    if not job_res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    job = job_res.data[0]

    cv_res = (
        supabase.table("cvs")
        .select("raw_text")
        .eq("user_id", user_id)
        .eq("is_primary", True)
        .limit(1)
        .execute()
    )
    if not cv_res.data or not cv_res.data[0].get("raw_text"):
        raise HTTPException(
            status_code=422,
            detail="Upload a CV first. We need your CV text to generate a cover letter.",
        )
    cv_text = cv_res.data[0]["raw_text"]

    try:
        result = await generate_cover_letter(
            user_cv_text=cv_text,
            job_title=job["title"],
            job_description=job.get("description") or "",
            company=job.get("company"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    content = (result.get("letter") or "").strip()
    if not content:
        raise HTTPException(status_code=503, detail="Cover letter generation returned empty content")

    existing = list_cover_letter_versions(user_id, match_id, supabase)
    parent_id = str(existing[0]["id"]) if existing else None

    version_row = save_cover_letter_version(
        user_id=user_id,
        match_id=match_id,
        content_md=content,
        generated_by="ai",
        parent_version_id=parent_id,
        supabase=supabase,
    )

    return MatchCoverLetterGenerateResponse(
        content=content,
        word_count=int(result.get("word_count") or _word_count(content)),
        version_id=str(version_row["id"]),
        version_number=int(version_row["version_number"]),
    )
