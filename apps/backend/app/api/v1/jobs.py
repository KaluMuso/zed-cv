"""Job listing routes."""
import hashlib
import html as _html
import logging
import re as _re
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
    _parse_salary_to_ngwee,
)
from app.services.embedding import generate_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# Whitelist of HTML tag names the sanitizer will strip. Anything outside
# this set is left as literal text so non-HTML angle-bracket content
# (salary ranges like "<K15000 - K30000>", emails like "<user@host>",
# placeholders like "<relevant degree>", comparisons like "< 10ms")
# survives ingestion instead of being silently deleted.
_KNOWN_HTML_TAGS = (
    "a|abbr|address|article|aside|b|big|blockquote|body|br|button|canvas|"
    "caption|center|cite|code|col|colgroup|dd|del|details|dfn|div|dl|dt|"
    "em|embed|fieldset|figcaption|figure|font|footer|form|h[1-6]|head|"
    "header|hr|html|i|iframe|img|input|ins|kbd|label|legend|li|main|mark|"
    "meta|nav|noscript|ol|optgroup|option|p|pre|q|s|samp|script|section|"
    "select|small|source|span|strong|style|sub|summary|sup|svg|table|tbody|"
    "td|template|textarea|tfoot|th|thead|time|title|tr|tt|u|ul|var|video|wbr"
)
_HTML_TAG_RE = _re.compile(
    rf"</?(?:{_KNOWN_HTML_TAGS})\b[^<>]*>", _re.IGNORECASE
)
_BR_RE = _re.compile(r"<\s*br\s*/?\s*>", _re.IGNORECASE)
_LI_OPEN_RE = _re.compile(r"<\s*li\b[^>]*>", _re.IGNORECASE)
_BLOCK_CLOSE_RE = _re.compile(
    # <li> opener already injects "\n• "; closing </li> shouldn't add another
    # newline or adjacent bullets render with a blank line between them.
    r"</\s*(p|div|h[1-6]|ul|ol|tr|table)\s*>", _re.IGNORECASE
)


def _strip_html(text: str | None) -> str:
    """Sanitize scraper-supplied HTML into plain text.

    Why this lives in the backend rather than in each n8n workflow: the
    sanitiser then covers every scraper automatically, including any future
    ones we add, and we don't have to keep two regexes in sync. Applied to
    each row's description before fingerprinting so two listings that differ
    only in HTML markup (one with <p>, one without) collapse to the same
    dedup key, and so the cleaned text is what /jobs/[id] renders (it uses
    whitespace-pre-wrap, which would otherwise print raw <p> tags).

    Block-level tags are converted to newlines before stripping so the
    rendered description keeps its paragraph and bullet structure. Inline
    tags (<b>, <em>, <a>) just disappear.
    """
    if not text:
        return ""
    s = _BR_RE.sub("\n", text)
    s = _LI_OPEN_RE.sub("\n• ", s)
    # Double-newline on block close so paragraph-style HTML
    # (<p>A</p><p>B</p>) renders as "A\n\nB" — a blank line between
    # paragraphs reads much better under whitespace-pre-wrap. Three+
    # newlines get collapsed to two below.
    s = _BLOCK_CLOSE_RE.sub("\n\n", s)
    s = _HTML_TAG_RE.sub("", s)
    # html.unescape covers &amp; &nbsp; &#39; &quot; — common in scraper output.
    s = _html.unescape(s)
    # Collapse horizontal whitespace per line; preserve newlines so
    # whitespace-pre-wrap keeps the visual structure.
    s = _re.sub(r"[ \t ]+", " ", s)
    s = _re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


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
    employment_type: str | None = Query(
        None,
        description=(
            "Comma-separated employment types. ANY semantics. "
            "Accepted: full_time, part_time, contract, freelance, "
            "internship, temporary."
        ),
    ),
    work_arrangement: str | None = Query(
        None,
        description=(
            "Comma-separated work arrangements. ANY semantics. "
            "Accepted: remote, hybrid, on_site."
        ),
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

    # `count="estimated"` uses Postgres planner stats for total instead of
    # running the full filtered query a second time without LIMIT, which
    # is what `count="exact"` requires. Exact counts on this query (ilike
    # + nested join through job_skills → skills) routinely tripped the
    # Cloudflare Worker upstream of Supabase's PostgREST (CF error 1101,
    # surfacing as `APIError: JSON could not be generated`) and forced
    # the retry-and-degrade path below to swallow the filtered request
    # entirely — Sentry issue ZEDCV-BACKEND-C. Estimated is sub-ms even
    # on a multi-million row table; pagination tolerates an approximate
    # total and the frontend doesn't surface it as an authoritative count.
    query = (
        supabase.table("jobs")
        .select("*, job_skills(skills(name))", count="estimated")
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
    # task #60: filter on the new structural dimensions. ANY-semantics
    # via .in_() so users can request e.g. employment_type=full_time,contract
    # without losing the listings that only set one. Unknown values are
    # passed through — they simply match zero rows and surface as empty
    # state, which is the same UX as an unknown skill chip.
    if employment_type:
        ets = [s.strip() for s in employment_type.split(",") if s.strip()]
        if ets:
            query = query.in_("employment_type", ets)
    if work_arrangement:
        was = [s.strip() for s in work_arrangement.split(",") if s.strip()]
        if was:
            query = query.in_("work_arrangement", was)
    if job_id_filter is not None:
        query = query.in_("id", job_id_filter)

    offset = (page - 1) * per_page

    # Defensive retry: even with count="estimated" the Supabase free-tier
    # Cloudflare Worker can throw exception 1101 on a noisy ilike + nested
    # join. Direct Postgres is fine; the issue is upstream of PostgREST.
    # Retry once before degrading to an empty result so a transient edge
    # hiccup doesn't nuke the user's session. Sentry sees both attempts.
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


@router.get("/sitemap")
async def list_jobs_for_sitemap(supabase=Depends(get_supabase)):
    """ID-only export of active jobs for /sitemap.xml.

    Public, auth-free, and deliberately narrow: only `id` + a `lastmod`
    timestamp. Used by the Next.js dynamic sitemap route — calling the
    full /jobs list endpoint instead would force 1000+ paginated requests
    to enumerate 50k jobs. Cap matches sitemap.org's 50,000-entry
    per-file limit. NOTE: this MUST be declared before the
    `/{job_id}` route below so FastAPI doesn't capture `/sitemap` as an
    id path parameter.
    """
    rows = (
        supabase.table("jobs")
        .select("id, updated_at, posted_at")
        .eq("is_active", True)
        .order("posted_at", desc=True)
        .limit(50000)
        .execute()
    )
    return {
        "ids": [
            {
                "id": r["id"],
                "lastmod": r.get("updated_at") or r.get("posted_at"),
            }
            for r in (rows.data or [])
        ]
    }


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
    # Same HTML strip as the ingest path — keeps manual admin creates and
    # scraper-fed rows on the same plain-text contract.
    body.description = _strip_html(body.description)

    # task #60: same salary-text fallback as the ingest path so admins who
    # paste "K15,000 - K20,000" don't need to convert it by hand.
    if body.salary_min is None and body.salary_max is None and body.salary_text:
        parsed_min, parsed_max = _parse_salary_to_ngwee(body.salary_text)
        if parsed_min is not None or parsed_max is not None:
            body.salary_min = parsed_min
            body.salary_max = parsed_max

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
    # salary_text is input-only (see ingest path comment).
    job_data.pop("salary_text", None)
    job_data["embedding"] = embedding
    result = supabase.table("jobs").insert(job_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create job")
    job = result.data[0]

    supabase.table("job_fingerprints").insert({"fingerprint": fp, "job_id": job["id"]}).execute()
    _link_job_skills(supabase, job["id"], skills_required)

    return Job(**job)


def _build_aggregator_blacklist(settings: Settings) -> list[str]:
    """Lowercased aggregator-domain list ready for substring matching."""
    return [
        d.strip().lower()
        for d in (settings.aggregator_domains_blacklist or "").split(",")
        if d.strip()
    ]


async def _ingest_one_job(
    supabase,
    job: JobCreate,
    aggregator_blacklist: list[str],
) -> tuple[str, str]:
    """Run the full per-row ingest pipeline on one JobCreate.

    Returns (status, detail) where status is one of:
      - "ingested" — row inserted, fingerprint stored, skills linked.
      - "duplicate" — fingerprint already in job_fingerprints; no write.
      - "skipped" — apply_url/source_url matched the aggregator blacklist.
      - "error" — anything else; detail carries the short reason.

    Shared between the n8n bulk-ingest route and Slice F's WhatsApp
    channel ingest path so both go through the same HTML-strip /
    fingerprint-dedup / embedding / skills-link pipeline. Mutating
    `job.description` here (HTML strip) is intentional — see the comment
    in the body.
    """
    try:
        if aggregator_blacklist:
            urls_to_check = " ".join(
                filter(None, [job.apply_url or "", job.source_url or ""])
            ).lower()
            if urls_to_check and any(
                domain in urls_to_check for domain in aggregator_blacklist
            ):
                logger.info(
                    "ingest_one_job: skipped as aggregator cross-listing (title=%r)",
                    job.title,
                )
                return "skipped", "aggregator"

        # Strip HTML BEFORE fingerprinting so identical jobs that differ
        # only in markup collapse to the same dedup key. Mutated value is
        # what gets embedded, fingerprinted, AND stored — all three stay
        # in sync.
        job.description = _strip_html(job.description)

        # task #60: salary text → ngwee fallback. Only fires when the
        # scraper left both ints null AND supplied a salary_text string.
        # Helper returns (None, None) on unparseable / non-ZMW input so
        # bad text falls through to "no salary listed". The salary_text
        # field itself is dropped from the insert payload below — DB has
        # no column for it.
        if (
            job.salary_min is None
            and job.salary_max is None
            and job.salary_text
        ):
            parsed_min, parsed_max = _parse_salary_to_ngwee(job.salary_text)
            if parsed_min is not None or parsed_max is not None:
                job.salary_min = parsed_min
                job.salary_max = parsed_max

        fp = _fingerprint(job.title, job.company, job.description)
        existing = (
            supabase.table("job_fingerprints")
            .select("job_id")
            .eq("fingerprint", fp)
            .execute()
        )
        if existing.data:
            return "duplicate", ""

        try:
            embedding = await generate_embedding(
                f"{job.title} {job.company or ''} {job.description}"
            )
        except Exception as exc:
            return "error", f"embedding_failed: {type(exc).__name__}"

        job_data = job.model_dump(exclude_none=True, mode="json")
        skills_required = job_data.pop("skills_required", [])
        # salary_text is input-only — used by the parser above but never
        # stored. Same goes for the empty-list fields where the model
        # defaulted to [] and exclude_none didn't strip them: leave the
        # explicit empty lists in place so a row with no benefits still
        # stores benefits=[] (matches the JSONB DEFAULT in migration 016).
        job_data.pop("salary_text", None)
        job_data["embedding"] = embedding

        result = supabase.table("jobs").insert(job_data).execute()
        if not result.data:
            return "error", "insert_returned_empty"

        new_job = result.data[0]
        supabase.table("job_fingerprints").insert(
            {"fingerprint": fp, "job_id": new_job["id"]}
        ).execute()
        _link_job_skills(supabase, new_job["id"], skills_required)
        return "ingested", ""
    except Exception as exc:
        logger.error(
            "ingest_one_job: failed (title=%r): %s",
            getattr(job, "title", None), exc, exc_info=True,
        )
        return "error", f"unexpected: {type(exc).__name__}"


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

    aggregator_blacklist = _build_aggregator_blacklist(settings)

    ingested = 0
    duplicates = 0
    skipped = 0
    errors: list[JobIngestErrorItem] = []

    for idx, job in enumerate(body.jobs):
        status, detail = await _ingest_one_job(supabase, job, aggregator_blacklist)
        if status == "ingested":
            ingested += 1
        elif status == "duplicate":
            duplicates += 1
        elif status == "skipped":
            skipped += 1
        else:  # "error"
            errors.append(JobIngestErrorItem(
                index=idx,
                title=(getattr(job, "title", None) or "<unknown>")[:80],
                reason=detail,
            ))

    return JobIngestResponse(
        ingested=ingested,
        duplicates=duplicates,
        skipped=skipped,
        errors=errors[:50],  # cap to keep response size bounded
    )
