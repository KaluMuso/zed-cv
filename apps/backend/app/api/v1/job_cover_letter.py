"""Job-scoped cover letter generation (OpenRouter via cover_letter service)."""
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.deps import get_current_user, get_supabase, is_superadmin
from app.core.rate_limit import limiter
from app.services.cover_letter import generate_cover_letter

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobCoverLetterResponse(BaseModel):
    content: str
    word_count: int
    document_id: str


@router.post(
    "/{job_id}/generate-cover-letter",
    response_model=JobCoverLetterResponse,
)
@limiter.limit("5/minute")
async def generate_job_cover_letter(
    request: Request,
    job_id: str,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """Generate a tailored 200–250 word cover letter for a specific job."""
    user_id = current_user["id"]

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
                detail=(
                    "Cover letter generation requires the Professional plan (K250/mo). "
                    "Upgrade at zedcv.com/pricing"
                ),
            )

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

    job_result = (
        supabase.table("jobs")
        .select("title, company, description")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    job = job_result.data[0]

    try:
        result = await generate_cover_letter(
            user_cv_text=cv_text,
            job_title=job["title"],
            job_description=job.get("description") or "",
            company=job.get("company"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    letter = (result.get("letter") or "").strip()
    if not letter:
        raise HTTPException(
            status_code=503,
            detail="Cover letter generation returned empty content",
        )

    doc_result = (
        supabase.table("generated_documents")
        .insert(
            {
                "user_id": user_id,
                "job_id": job_id,
                "doc_type": "cover_letter",
                "content": letter,
                "metadata": {
                    "word_count": result["word_count"],
                    "provider": "openrouter",
                    "role": job["title"],
                    "company": job.get("company"),
                },
            }
        )
        .execute()
    )

    doc_id = doc_result.data[0]["id"] if doc_result.data else "unknown"

    return JobCoverLetterResponse(
        content=letter,
        word_count=result["word_count"],
        document_id=doc_id,
    )
