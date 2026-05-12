"""Job listing routes."""
import hashlib
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from app.core.config import Settings, get_settings
from app.core.deps import get_supabase, require_admin
from app.core.rate_limit import limiter
from app.schemas.jobs import (
    Job,
    JobCreate,
    JobList,
    JobIngestRequest,
    JobIngestResponse,
    JobIngestErrorItem,
)
from app.services.embedding import generate_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _fingerprint(title: str, company: str | None, description: str) -> str:
    """Stable dedupe key — lowercase, title + company + first 200 desc chars."""
    return hashlib.sha256(
        f"{title}|{company or ''}|{description[:200]}".lower().encode()
    ).hexdigest()


def _link_job_skills(supabase, job_id: str, skill_names: list[str]) -> None:
    """Resolve each skill name through skills.name then skill_aliases.alias
    and insert into job_skills. Silently skips unknown skills — n8n's AI
    parser can emit fuzzy strings, and that's preferable to 500-ing the
    whole job."""
    for raw in skill_names:
        key = (raw or "").strip().lower()
        if not key:
            continue
        skill_id: str | None = None
        sk = supabase.table("skills").select("id").eq("name", key).limit(1).execute()
        if sk.data:
            skill_id = sk.data[0]["id"]
        else:
            al = supabase.table("skill_aliases").select("skill_id").eq("alias", key).limit(1).execute()
            if al.data:
                skill_id = al.data[0]["skill_id"]
        if skill_id:
            supabase.table("job_skills").insert(
                {"job_id": job_id, "skill_id": skill_id}
            ).execute()


# Sort modes accepted by GET /jobs. "relevance" is anonymous-friendly: we
# don't have a viewer-personalised score here (that lives at /matches), so
# we fall back to recency. "closing" prioritises soonest deadline.
_ALLOWED_SORT = {"relevance", "recent", "closing"}


@router.get("", response_model=JobList)
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    location: str | None = None,
    search: str | None = None,
    sort: str = Query("recent"),
    skills: str | None = Query(
        None,
        description="Comma-separated skill names. Matches ANY (OR semantics).",
    ),
    source: str | None = Query(
        None,
        description="Comma-separated source values (manual,scraper,ocr,partner).",
    ),
    supabase=Depends(get_supabase),
):
    sort_mode = sort if sort in _ALLOWED_SORT else "recent"

    # Skill filter requires a separate lookup against skills + job_skills
    # because supabase-py doesn't express the join filter inline. We resolve
    # skill names + aliases → skill_ids, then job_ids → use .in_() on jobs.
    # An empty intersection short-circuits to "no jobs" without burning the
    # main query.
    job_id_filter: list[str] | None = None
    if skills:
        skill_names = [s.strip().lower() for s in skills.split(",") if s.strip()]
        if skill_names:
            sk_rows = (
                supabase.table("skills")
                .select("id")
                .in_("name", skill_names)
                .execute()
            )
            skill_ids = [r["id"] for r in (sk_rows.data or [])]
            # Also pick up aliases so "react" matches "reactjs", "react.js", etc.
            al_rows = (
                supabase.table("skill_aliases")
                .select("skill_id")
                .in_("alias", skill_names)
                .execute()
            )
            skill_ids.extend(r["skill_id"] for r in (al_rows.data or []))
            skill_ids = list(set(skill_ids))
            if not skill_ids:
                # No matching skills → no jobs can match.
                return JobList(jobs=[], total=0, page=page, per_page=per_page, pages=1)
            js_rows = (
                supabase.table("job_skills")
                .select("job_id")
                .in_("skill_id", skill_ids)
                .execute()
            )
            job_id_filter = list({r["job_id"] for r in (js_rows.data or [])})
            if not job_id_filter:
                return JobList(jobs=[], total=0, page=page, per_page=per_page, pages=1)

    query = (
        supabase.table("jobs")
        .select("*, job_skills(skills(name))", count="exact")
        .eq("is_active", True)
    )

    if sort_mode == "closing":
        # PostgREST does not support NULLS LAST inline; emulate by filtering
        # out null closing_dates for this view. Open-ended jobs aren't
        # "closing soon" by definition, so excluding them is intentional.
        query = query.not_.is_("closing_date", "null").order("closing_date", desc=False)
    else:
        # recent + relevance both reduce to posted_at desc for now.
        query = query.order("posted_at", desc=True)

    if location:
        query = query.ilike("location", f"%{location}%")
    if search:
        query = query.or_(
            f"title.ilike.%{search}%,"
            f"company.ilike.%{search}%,"
            f"description.ilike.%{search}%"
        )
    if source:
        sources = [s.strip() for s in source.split(",") if s.strip()]
        if sources:
            query = query.in_("source", sources)
    if job_id_filter is not None:
        query = query.in_("id", job_id_filter)

    offset = (page - 1) * per_page

    # Supabase free-tier Cloudflare Worker occasionally throws exception 1101
    # on filtered queries (especially `count=exact` + `ilike` + nested join).
    # Direct Postgres is fine; the issue is upstream of PostgREST. Retry once
    # before degrading to an empty result so a transient edge hiccup doesn't
    # nuke the user's session. Sentry sees both attempts via the logger.
    import time
    from postgrest.exceptions import APIError as PostgrestAPIError

    last_exc: Exception | None = None
    result = None
    for attempt in (1, 2):
        try:
            result = query.range(offset, offset + per_page - 1).execute()
            break
        except PostgrestAPIError as exc:
            last_exc = exc
            # Only retry on 5xx-shaped errors. 4xx (bad request, RLS) won't
            # heal from a retry — let those bubble in the final pass so we
            # don't silently mask schema mistakes.
            code = getattr(exc, "code", None)
            if isinstance(code, int) and code < 500:
                break
            if attempt == 1:
                time.sleep(0.3)  # tiny backoff; CF Worker cold starts can resolve
                continue
            # Final attempt: log + degrade. Sentry captures the trace via
            # the global handler. Returning empty is better UX than 500.
            logger.error(
                "list_jobs: Supabase 5xx after retry — degrading to empty. "
                "filters: location=%r search=%r sort=%r source=%r skills=%r",
                location, search, sort, source, skills,
                exc_info=True,
            )
            import math
            return JobList(jobs=[], total=0, page=page, per_page=per_page, pages=1)

    if result is None:
        # Either we hit a non-retryable APIError or somehow exited the loop
        # without a result. Surface the original exception via 503 so the
        # client knows to retry (vs 500 which suggests our bug).
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Job search is temporarily unavailable. Please try again in a moment.",
        )

    total = result.count or 0
    import math
    pages = math.ceil(total / per_page) if total > 0 else 1
    jobs = []
    for j in (result.data or []):
        skill_rows = j.pop("job_skills", [])
        job_skills = [s["skills"]["name"] for s in skill_rows if s.get("skills")]
        j["skills_required"] = job_skills
        j["skills"] = job_skills
        jobs.append(Job(**j))
    return JobList(jobs=jobs, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str, supabase=Depends(get_supabase)):
    result = supabase.table("jobs").select("*, job_skills(skills(name))").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    j = result.data
    skill_rows = j.pop("job_skills", [])
    skills = [s["skills"]["name"] for s in skill_rows if s.get("skills")]
    j["skills_required"] = skills
    j["skills"] = skills
    return Job(**j)


@router.post("", response_model=Job, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_job(request: Request, body: JobCreate, current_user: dict = Depends(require_admin), supabase=Depends(get_supabase)):
    fp = _fingerprint(body.title, body.company, body.description)
    existing = supabase.table("job_fingerprints").select("job_id").eq("fingerprint", fp).execute()
    if existing.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate job listing")

    try:
        embedding = await generate_embedding(f"{body.title} {body.company or ''} {body.description}")
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    job_data = body.model_dump(exclude_none=True, mode="json")
    skills_required = job_data.pop("skills_required", [])
    job_data["embedding"] = embedding
    result = supabase.table("jobs").insert(job_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create job")
    job = result.data[0]

    supabase.table("job_fingerprints").insert({"fingerprint": fp, "job_id": job["id"]}).execute()
    _link_job_skills(supabase, job["id"], skills_required)

    return Job(**job)


@router.post("/ingest", response_model=JobIngestResponse)
@limiter.limit("10/minute")
async def ingest_jobs(
    request: Request,
    body: JobIngestRequest,
    supabase=Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Bulk-ingest jobs from the n8n scraper.

    Auth: shared secret in body (`api_key`). Each job is processed
    independently — a single bad row never fails the batch. Returns
    `{ingested, duplicates, errors}` so the operator can triage from
    the n8n execution view.

    Dedup is by SHA-256 fingerprint of title|company|first-200-chars-desc
    against the `job_fingerprints` table. Skills are linked through
    `skills` then `skill_aliases` (fuzzy matches silently dropped — the
    AI parser can emit noisy strings, and that's preferable to 500-ing
    the row).
    """
    if not settings.ingest_api_key or body.api_key != settings.ingest_api_key:
        # Same response for missing-config and wrong-key — don't leak
        # whether the server has an ingest key configured.
        raise HTTPException(status_code=401, detail="Invalid ingest API key")

    ingested = 0
    duplicates = 0
    errors: list[JobIngestErrorItem] = []

    for idx, job in enumerate(body.jobs):
        try:
            fp = _fingerprint(job.title, job.company, job.description)
            existing = (
                supabase.table("job_fingerprints")
                .select("job_id")
                .eq("fingerprint", fp)
                .execute()
            )
            if existing.data:
                duplicates += 1
                continue

            try:
                embedding = await generate_embedding(
                    f"{job.title} {job.company or ''} {job.description}"
                )
            except Exception as exc:
                errors.append(JobIngestErrorItem(
                    index=idx,
                    title=job.title[:80],
                    reason=f"embedding_failed: {type(exc).__name__}",
                ))
                continue

            job_data = job.model_dump(exclude_none=True, mode="json")
            skills_required = job_data.pop("skills_required", [])
            job_data["embedding"] = embedding

            result = supabase.table("jobs").insert(job_data).execute()
            if not result.data:
                errors.append(JobIngestErrorItem(
                    index=idx,
                    title=job.title[:80],
                    reason="insert_returned_empty",
                ))
                continue

            new_job = result.data[0]
            supabase.table("job_fingerprints").insert({
                "fingerprint": fp,
                "job_id": new_job["id"],
            }).execute()
            _link_job_skills(supabase, new_job["id"], skills_required)
            ingested += 1
        except Exception as exc:
            # Catch-all so one bad row never poisons the batch. Sentry
            # captures the full trace via the global handler.
            logger.error(
                "ingest_jobs: row %d failed (title=%r): %s",
                idx, getattr(job, "title", None), exc, exc_info=True,
            )
            errors.append(JobIngestErrorItem(
                index=idx,
                title=(getattr(job, "title", None) or "<unknown>")[:80],
                reason=f"unexpected: {type(exc).__name__}",
            ))

    return JobIngestResponse(
        ingested=ingested,
        duplicates=duplicates,
        errors=errors[:50],  # cap to keep response size bounded
    )
