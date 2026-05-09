"""Cover letter generation routes — Professional tier or superadmin."""
from typing import Literal, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.deps import get_supabase, get_current_user, is_superadmin
from app.core.rate_limit import limiter
from app.services.cover_letter import generate_cover_letter

router = APIRouter(prefix="/cover-letter", tags=["Cover Letter"])


class CoverLetterRequest(BaseModel):
    job_id: str
    tone: Optional[Literal["formal", "friendly", "confident"]] = "formal"


class CoverLetterResponse(BaseModel):
    letter: str
    word_count: int
    tone: str
    document_id: str


@router.post("/generate", response_model=CoverLetterResponse)
@limiter.limit("5/minute")
async def generate(
    request: Request,
    body: CoverLetterRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    user_id = current_user["id"]

    # Superadmin bypasses tier check
    if not is_superadmin(current_user):
        sub = (
            supabase.table("subscriptions")
            .select("tier, status")
            .eq("user_id", user_id)
            .eq("status", "active")
            .single()
            .execute()
        )
        if not sub.data or sub.data["tier"] not in ("professional", "super_standard"):
            raise HTTPException(
                status_code=403,
                detail="Cover letter generation requires the Professional plan (K250/mo). "
                       "Upgrade at zedcv.com/pricing",
            )

    # Get user's primary CV text
    cv_result = (
        supabase.table("cvs")
        .select("raw_text")
        .eq("user_id", user_id)
        .eq("is_primary", True)
        .limit(1)
        .execute()
    )
    if not cv_result.data or not cv_result.data[0].get("raw_text"):
        raise HTTPException(
            status_code=422,
            detail="Upload a CV first. We need your CV text to generate a cover letter.",
        )
    cv_text = cv_result.data[0]["raw_text"]

    # Get job details
    job_result = (
        supabase.table("jobs")
        .select("title, company, description")
        .eq("id", body.job_id)
        .single()
        .execute()
    )
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    job = job_result.data

    # Generate the cover letter
    try:
        result = await generate_cover_letter(
            user_cv_text=cv_text,
            job_title=job["title"],
            job_description=job["description"],
            company=job.get("company"),
            tone=body.tone or "formal",
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Store in generated_documents
    doc_result = supabase.table("generated_documents").insert({
        "user_id": user_id,
        "job_id": body.job_id,
        "doc_type": "cover_letter",
        "content": result["letter"],
        "metadata": {"tone": result["tone"], "word_count": result["word_count"]},
    }).execute()

    doc_id = doc_result.data[0]["id"] if doc_result.data else "unknown"

    return CoverLetterResponse(
        letter=result["letter"],
        word_count=result["word_count"],
        tone=result["tone"],
        document_id=doc_id,
    )
