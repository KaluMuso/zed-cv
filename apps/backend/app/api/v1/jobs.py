"""Job listing routes."""

import hashlib
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_supabase, get_current_user_id
from app.schemas.jobs import Job, JobCreate, JobList
from app.services.embedding import generate_embedding

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=JobList)
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    location: str | None = None,
    search: str | None = None,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """List active jobs with pagination and optional filters."""
    query = (
        supabase.table("jobs")
        .select("*", count="exact")
        .eq("is_active", True)
        .order("posted_at", desc=True)
    )

    if location:
        query = query.ilike("location", f"%{location}%")

    if search:
        query = query.or_(
            f"title.ilike.%{search}%,company.ilike.%{search}%,description.ilike.%{search}%"
        )

    # Pagination
    offset = (page - 1) * per_page
    query = query.range(offset, offset + per_page - 1)

    result = query.execute()

    return JobList(
        jobs=[Job(**j) for j in (result.data or [])],
        total=result.count or 0,
        page=page,
        per_page=per_page,
    )


@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Get a single job by ID."""
    result = (
        supabase.table("jobs")
        .select("*")
        .eq("id", job_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    return Job(**result.data)


@router.post("", response_model=Job, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: JobCreate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Ingest a new job listing. Deduplicates by content fingerprint."""
    # Generate fingerprint for deduplication
    fingerprint_input = f"{body.title}|{body.company or ''}|{body.description[:200]}"
    fingerprint = hashlib.sha256(fingerprint_input.lower().encode()).hexdigest()

    # Check for duplicate
    existing = (
        supabase.table("job_fingerprints")
        .select("job_id")
        .eq("fingerprint", fingerprint)
        .execute()
    )

    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate job listing detected",
        )

    # Generate embedding for the job
    embed_text = f"{body.title} {body.company or ''} {body.description}"
    embedding = await generate_embedding(embed_text)

    # Insert job
    job_data = body.model_dump(exclude_none=True)
    job_data["embedding"] = embedding
    # Convert skills_required to job_skills after insert
    skills_required = job_data.pop("skills_required", [])

    result = supabase.table("jobs").insert(job_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create job")

    job = result.data[0]

    # Store fingerprint
    supabase.table("job_fingerprints").insert(
        {"fingerprint": fingerprint, "job_id": job["id"]}
    ).execute()

    # Link skills (best-effort — skip unknown skills)
    for skill_name in skills_required:
        skill_result = (
            supabase.table("skills")
            .select("id")
            .eq("name", skill_name.lower())
            .limit(1)
            .execute()
        )
        if skill_result.data:
            supabase.table("job_skills").insert(
                {"job_id": job["id"], "skill_id": skill_result.data[0]["id"]}
            ).execute()
        else:
            # Check aliases
            alias_result = (
                supabase.table("skill_aliases")
                .select("skill_id")
                .eq("alias", skill_name.lower())
                .limit(1)
                .execute()
            )
            if alias_result.data:
                supabase.table("job_skills").insert(
                    {"job_id": job["id"], "skill_id": alias_result.data[0]["skill_id"]}
                ).execute()

    return Job(**job)
