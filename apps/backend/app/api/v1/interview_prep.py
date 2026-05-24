"""Interview prep — Bwana Interview (Super Standard). Stub + job-scoped generate."""
import hashlib

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.deps import get_supabase, get_current_user, is_superadmin
from app.core.rate_limit import limiter
from app.services.interview_prep import generate_interview_prep

router = APIRouter(prefix="/interview-prep", tags=["Interview Prep"])

_INTERVIEW_PREP_SECTIONS = (
    "Quizzes",
    "Aptitude tests",
    "Dress code",
    "Skill build-ups",
)


class InterviewPrepSection(BaseModel):
    id: str
    title: str
    description: str
    status: str = "coming_soon"


class InterviewPrepOverview(BaseModel):
    product_name: str = "Bwana Interview"
    sections: list[InterviewPrepSection]
    message: str


class InterviewPrepStubRequest(BaseModel):
    section_id: str = Field(..., min_length=1, max_length=64)


class InterviewPrepStubResponse(BaseModel):
    section_id: str
    content: str
    placeholder: bool = True


def _require_super_standard(
    current_user: dict, supabase, *, user_id: str
) -> None:
    if is_superadmin(current_user):
        return
    sub = (
        supabase.table("subscriptions")
        .select("tier, status")
        .eq("user_id", user_id)
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    tier = (sub.data[0].get("tier") if sub.data else None) or "free"
    if tier != "super_standard":
        raise HTTPException(
            status_code=403,
            detail=(
                "Bwana Interview is included on the Super Standard plan (K500/mo). "
                "Upgrade at /pricing."
            ),
        )


@router.get("", response_model=InterviewPrepOverview)
async def interview_prep_overview(
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """Catalog of interview-prep modules (Super Standard)."""
    _require_super_standard(current_user, supabase, user_id=current_user["id"])
    sections = [
        InterviewPrepSection(
            id=s.lower().replace(" ", "-"),
            title=s,
            description=f"{s} content will be tailored to your CV and target roles.",
        )
        for s in _INTERVIEW_PREP_SECTIONS
    ]
    return InterviewPrepOverview(
        sections=sections,
        message="Full Bwana Interview experiences are rolling out soon.",
    )


@router.post("", response_model=InterviewPrepStubResponse)
@limiter.limit("10/minute")
async def interview_prep_placeholder(
    request: Request,
    body: InterviewPrepStubRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """Placeholder LLM response until the full Bwana Interview module ships."""
    del request
    _require_super_standard(current_user, supabase, user_id=current_user["id"])
    title = body.section_id.replace("-", " ").title()
    return InterviewPrepStubResponse(
        section_id=body.section_id,
        content=(
            f"[Bwana Interview — placeholder]\n\n"
            f"Your {title} module will include personalized guidance based on "
            "your CV and saved jobs. Check back after the next release."
        ),
    )


class InterviewPrepRequest(BaseModel):
    job_id: str


class InterviewPrepResponse(BaseModel):
    content: str
    word_count: int
    job_title: str
    company: str | None = None
    cached: bool = False
    degraded: bool = False


@router.post("/generate", response_model=InterviewPrepResponse)
@limiter.limit("5/minute")
async def generate(
    request: Request,
    body: InterviewPrepRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    user_id = current_user["id"]

    _require_super_standard(current_user, supabase, user_id=user_id)

    cv_res = (
        supabase.table("cvs")
        .select("id, raw_text")
        .eq("user_id", user_id)
        .eq("is_primary", True)
        .limit(1)
        .execute()
    )
    if not cv_res.data or not cv_res.data[0].get("raw_text"):
        raise HTTPException(
            status_code=422,
            detail="Upload a CV first. We need your CV to tailor the prep notes.",
        )
    cv = cv_res.data[0]

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

    cache_key = hashlib.sha256(
        f"interview_prep:{cv['id']}:{body.job_id}".encode()
    ).hexdigest()
    cached = (
        supabase.table("ai_cache")
        .select("result")
        .eq("cache_key", cache_key)
        .limit(1)
        .execute()
    )
    if cached.data:
        result = cached.data[0]["result"]
        return InterviewPrepResponse(
            cached=True,
            content=result["content"],
            word_count=result["word_count"],
            job_title=job["title"],
            company=job.get("company"),
        )

    try:
        result = await generate_interview_prep(
            cv_text=cv["raw_text"],
            job_title=job["title"],
            company=job.get("company"),
            job_description=job.get("description"),
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # cache_type validated via the enum (migration 013 dropped the SQL CHECK).
    from app.schemas.db_enums import CacheType
    supabase.table("ai_cache").insert({
        "cache_key": cache_key,
        "cache_type": CacheType.interview_prep.value,
        "input_hash": hashlib.sha256(
            (cv.get("raw_text") or "").encode() + body.job_id.encode()
        ).hexdigest(),
        "result": result,
        "model": "google/gemini-flash-2.0",
    }).execute()

    return InterviewPrepResponse(
        cached=False,
        content=result["content"],
        word_count=result["word_count"],
        job_title=job["title"],
        company=job.get("company"),
        degraded=bool(result.get("degraded")),
    )
