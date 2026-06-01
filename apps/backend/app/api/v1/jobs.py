"""Job listing routes."""
import hashlib
import html as _html
import logging
import re as _re
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import Settings, get_settings
from app.core.deps import (
    get_current_user_id,
    get_supabase,
    require_admin,
    require_admin_or_ingest_key,
)
from app.core.errors import ProblemHTTPException
from app.core.rate_limit import limiter
from app.schemas.jobs import (
    Job,
    JobCreate,
    JobList,
    JobIngestRequest,
    JobIngestResponse,
    JobIngestErrorItem,
    JobEnrichPatch,
    DeepEnrichTickResponse,
    _parse_salary_to_ngwee,
)
from app.schemas.saved_jobs import SaveJobResponse
from app.services.job_hydration import hydrate_job_row
from app.services.embedding import generate_embedding
from app.services.job_enricher import enrich_job
from app.services.job_enrichment import apply_job_enrichment
from app.services.deep_link_enricher import schedule_deep_link_enrichment
from app.services.job_page_text_extractor import (
    is_aggregator,
    merge_resolved_apply_contacts,
    resolve_apply_contacts_from_aggregator_url,
)
from app.services.deep_scrape_tick import run_deep_enrich_tick
from app.services.description_body_extractor import merge_description_extraction
from app.services.job_quality import (
    apply_ingest_quality_to_job_data,
    split_multi_role_listing,
    strip_scraper_metadata,
)
from app.services.job_activation import apply_review_state_to_row, compute_review_state
from app.services.job_publication import (
    PUBLIC_JOBS_OR_FILTER,
    apply_contact_activation,
    is_publicly_listable,
)
from app.services.job_scraping_sources import merge_scraping_sources
from app.services.job_deadline_extractor import extract_closing_date_llm
from app.services.job_visibility import FEED_STATUSES, visibility_from_row
from app.services.skill_resolver import resolve_skill_ids
from app.services import skills_dictionary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])

_security_optional = HTTPBearer(auto_error=False)

# Match apps/frontend/src/lib/isJobHiddenFromUserFeed.ts — listings stay
# visible for three calendar days after closing_date, then drop from feeds.
_CLOSING_DATE_GRACE_DAYS = 3


def _closing_date_grace_cutoff() -> str:
    return (date.today() - timedelta(days=_CLOSING_DATE_GRACE_DAYS)).isoformat()


async def _optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security_optional),
    settings: Settings = Depends(get_settings),
) -> str | None:
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload.get("sub")
    except JWTError:
        return None


def _intersect_job_ids(
    current: list[str] | None,
    new_ids: list[str],
) -> list[str]:
    if current is None:
        return new_ids
    allowed = set(new_ids)
    return [job_id for job_id in current if job_id in allowed]


def _require_ingest_header(
    settings: Settings,
    ingest_api_key: str | None,
    x_ingest_api_key: str | None,
) -> None:
    supplied = ingest_api_key or x_ingest_api_key
    if not settings.ingest_api_key or supplied != settings.ingest_api_key:
        raise HTTPException(status_code=401, detail="Invalid ingest API key")

_EMAIL_RE = _re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", _re.IGNORECASE)
_URL_RE = _re.compile(r"\b(?:https?://|www\.)\S+|\b[A-Z0-9.-]+\.[A-Z]{2,}(?:/\S*)?", _re.IGNORECASE)
_PHONE_RE = _re.compile(r"(?:\+?260|0)?[79]\d{8}\b")


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def _instructions_have_contact(value: str | None) -> bool:
    if not value:
        return False
    return bool(_EMAIL_RE.search(value) or _URL_RE.search(value) or _PHONE_RE.search(value))


def _job_eligibility_reasons(job: JobCreate) -> list[str]:
    has_apply_url = _has_text(job.apply_url)
    has_apply_email = _has_text(job.apply_email)
    has_instruction_contact = _instructions_have_contact(job.application_instructions)
    if has_apply_url or has_apply_email or has_instruction_contact:
        return []

    reasons = ["missing_apply_link", "missing_contact"]
    if job.closing_date is None:
        reasons.append("missing_deadline")
    return reasons


def _emit_analytics_event(supabase, event: str, properties: dict) -> None:
    try:
        supabase.table("analytics_events").insert(
            {"event": event, "properties": properties, "user_id": None}
        ).execute()
    except Exception as exc:  # pragma: no cover
        logger.debug("analytics_events insert failed (%s): %s", event, exc)


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
    return strip_scraper_metadata(s.strip())


def _fingerprint(title: str, company: str | None, description: str) -> str:
    """Stable dedupe key — lowercase, title + company + first 200 desc chars."""
    return hashlib.sha256(
        f"{title}|{company or ''}|{description[:200]}".lower().encode()
    ).hexdigest()


async def _attach_job_skills(supabase, job_id: str, skill_names: list[str]) -> None:
    """Resolve skills via Wave 2.5 resolver and link job_skills rows."""
    skill_ids = await resolve_skill_ids(
        skill_names,
        supabase=supabase,
        source="job_ingest",
    )
    for skill_id in skill_ids:
        try:
            supabase.table("job_skills").insert(
                {"job_id": job_id, "skill_id": skill_id}
            ).execute()
        except Exception:
            pass


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
    has_salary: bool = Query(
        False,
        description="When true, only jobs with salary_min and/or salary_max set.",
    ),
    saved_only: bool = Query(
        False,
        description="When true, restrict to jobs saved by the authenticated user.",
    ),
    include_closed: bool = Query(
        False,
        description="Deprecated alias for include_archived.",
    ),
    include_archived: bool = Query(
        False,
        description="When true, include archived jobs (hidden after 3-day grace).",
    ),
    user_id: str | None = Depends(_optional_user_id),
    supabase=Depends(get_supabase),
):
    show_archived = include_archived or include_closed
    sort_mode = sort if sort in _ALLOWED_SORT else "recent"

    if saved_only and not user_id:
        raise ProblemHTTPException(
            status.HTTP_401_UNAUTHORIZED,
            code="auth_required",
            user_message="Sign in to view saved jobs.",
        )

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
            al_rows = (
                supabase.table("skill_aliases")
                .select("skill_id")
                .in_("alias", skill_names)
                .execute()
            )
            skill_ids.extend(r["skill_id"] for r in (al_rows.data or []))
            skill_ids = list(set(skill_ids))
            if not skill_ids:
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

    if saved_only and user_id:
        saved_rows = (
            supabase.table("saved_jobs")
            .select("job_id")
            .eq("user_id", user_id)
            .execute()
        )
        saved_ids = list({r["job_id"] for r in (saved_rows.data or [])})
        if not saved_ids:
            return JobList(jobs=[], total=0, page=page, per_page=per_page, pages=1)
        job_id_filter = _intersect_job_ids(job_id_filter, saved_ids)
        if not job_id_filter:
            return JobList(jobs=[], total=0, page=page, per_page=per_page, pages=1)

    # Main query selects only flat columns. PR #41 switched count from
    # "exact" to "estimated" to cut the planner cost, but Sentry issue
    # ZEDCV-BACKEND-C kept firing on filtered queries (location='Lusaka'
    # in particular). The remaining cause is the embedded join
    # `job_skills(skills(name))`: PostgREST streams a composite JSON
    # whose serialization size scales with the number of skills per row,
    # and that occasionally exceeds the free-tier Cloudflare Worker's
    # CPU budget — surfacing as `APIError: JSON could not be generated`
    # (CF error 1101). Unfiltered queries happened to fit; filtered ones
    # didn't, so users hit the degrade-to-empty fallback exactly when
    # they tried to narrow down by city.
    #
    # Path A: keep the main query flat, then fetch skills in a small
    # follow-up `.in_("job_id", [...])` call. Same outer response shape
    # for the frontend, but two cheap trips instead of one heavy stream.
    query = (
        supabase.table("jobs_user_facing")
        .select("*", count="estimated")
        .eq("is_review_required", False)
        .or_(PUBLIC_JOBS_OR_FILTER)
    )
    if not show_archived:
        query = query.in_("visibility_status", list(FEED_STATUSES))

    if sort_mode == "closing":
        # PostgREST does not support NULLS LAST inline; emulate by filtering
        # out null closing_dates for this view. Open-ended jobs aren't
        # "closing soon" by definition, so excluding them is intentional.
        query = query.not_.is_("closing_date", "null").order("closing_date", desc=False)
    else:
        # recent + relevance both reduce to posted_at desc for now.
        query = query.order("posted_at", desc=True)

    if location:
        # `*` is PostgREST's URL-safe wildcard for ilike, equivalent to
        # SQL's `%`. supabase-py 2.9.1 passes the raw filter value into
        # httpx.QueryParams; for the direct `.ilike(col, "%x%")` path
        # httpx does NOT percent-encode the `%` characters, so the URL
        # arrives at Supabase as `…location=ilike.%Lusaka%…` — a
        # malformed percent-encoding (Lu/sa are not hex). Direct
        # PostgREST tolerates it; the upstream Cloudflare Worker
        # doesn't and 1101's with `APIError: JSON could not be
        # generated` — Sentry issue ZEDCV-BACKEND-C. `*` encodes
        # cleanly to `%2A` and PostgREST treats it the same.
        query = query.ilike("location", f"*{location}*")
    if search:
        # Same wildcard treatment for the search-across-3-columns case.
        # (Note: the embedded form inside `.or_()` is encoded correctly
        # by httpx so the `%` would have worked here — switching to `*`
        # anyway for consistency with the location filter above.)
        query = query.or_(
            f"title.ilike.*{search}*,"
            f"company.ilike.*{search}*,"
            f"description.ilike.*{search}*"
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
    if has_salary:
        query = query.or_("salary_min.not.is.null,salary_max.not.is.null")
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
                "filters: location=%r search=%r sort=%r source=%r skills=%r "
                "employment_type=%r work_arrangement=%r has_salary=%r saved_only=%r",
                location, search, sort, source, skills,
                employment_type, work_arrangement, has_salary, saved_only,
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

    # Second hop: fetch skill names for the returned page only. Goes to
    # the same Supabase but with a flat shape (no nested join), which
    # comfortably fits the CF Worker budget. Skipped when the page is
    # empty so we don't issue a `.in_("job_id", [])` round-trip.
    #
    # If the follow-up call hiccups we log and continue with empty skill
    # lists rather than degrading the whole page — skills are metadata,
    # not the primary signal users came for.
    job_rows = result.data or []
    skills_by_job: dict[str, list[str]] = {}
    if job_rows:
        try:
            sk_res = (
                supabase.table("job_skills")
                .select("job_id, skills(name)")
                .in_("job_id", [j["id"] for j in job_rows])
                .execute()
            )
            for row in (sk_res.data or []):
                skill_obj = row.get("skills") if isinstance(row, dict) else None
                name = (
                    skill_obj.get("name")
                    if isinstance(skill_obj, dict)
                    else None
                )
                if name:
                    skills_by_job.setdefault(row["job_id"], []).append(name)
        except PostgrestAPIError:
            logger.warning(
                "list_jobs: skills lookup failed; returning %d jobs with empty "
                "skill lists. filters: location=%r search=%r",
                len(job_rows), location, search,
                exc_info=True,
            )

    jobs = []
    for j in job_rows:
        # Drop the legacy embedded-join field if a future caller re-adds
        # it; the response shape is driven entirely by skills_by_job now.
        j.pop("job_skills", None)
        skills_list = skills_by_job.get(j["id"], [])
        j["skills_required"] = skills_list
        j["skills"] = skills_list
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
        .eq("is_review_required", False)
        .or_(PUBLIC_JOBS_OR_FILTER)
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


@router.post("/deep-enrich-tick", response_model=DeepEnrichTickResponse)
@limiter.limit("30/minute")
async def deep_enrich_tick(
    request: Request,
    limit: int = Query(25, ge=1, le=100),
    ingest_api_key: str | None = Header(None, alias="INGEST_API_KEY"),
    x_ingest_api_key: str | None = Header(None, alias="X-INGEST-API-KEY"),
    supabase=Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Secondary scrape batch: fetch HTTP source_url pages and set apply contacts.

    Intended for n8n cron (every 6h). Complements fire-and-forget
    ``schedule_deep_link_enrichment`` on ingest and manual PATCH
    ``/jobs/{job_id}/enrich`` callbacks from browser-based scrapers.

    Declared before ``/{job_id}`` so FastAPI does not treat
    ``deep-enrich-tick`` as a job UUID (which would yield HTTP 405 on POST).
    """
    _require_ingest_header(settings, ingest_api_key, x_ingest_api_key)
    stats = await run_deep_enrich_tick(supabase, limit=limit)
    return DeepEnrichTickResponse(**stats)


@router.post("/{job_id}/save", response_model=SaveJobResponse)
async def save_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    exists = (
        supabase.table("jobs").select("id").eq("id", job_id).limit(1).execute()
    )
    if not exists.data:
        raise HTTPException(status_code=404, detail="Job not found")
    supabase.table("saved_jobs").upsert(
        {"user_id": user_id, "job_id": job_id},
        on_conflict="user_id,job_id",
    ).execute()
    return SaveJobResponse()


@router.delete("/{job_id}/save", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    supabase.table("saved_jobs").delete().eq("user_id", user_id).eq(
        "job_id", job_id
    ).execute()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str, supabase=Depends(get_supabase)):
    """Return a job by id including inactive/closed rows (frontend renders closure UX)."""
    result = supabase.table("jobs").select("*, job_skills(skills(name))").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return hydrate_job_row(result.data)


@router.patch("/{job_id}/enrich", response_model=Job)
@limiter.limit("60/minute")
async def enrich_job_listing(
    request: Request,
    job_id: str,
    body: JobEnrichPatch,
    _auth: dict = Depends(require_admin_or_ingest_key),
    supabase=Depends(get_supabase),
):
    """Apply deep-scrape enrichment from n8n (employer contacts + original URL).

    Auth: admin Bearer JWT or ``X-INGEST-API-KEY`` / ``INGEST_API_KEY`` header
    (same secret as bulk ingest — suitable for service-role automation).
    """
    existing = (
        supabase.table("jobs")
        .select("id, apply_url, apply_email")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Job not found")

    patch = body.model_dump(exclude_unset=True, mode="json")
    if not patch:
        raise HTTPException(status_code=422, detail="No fields to update")

    if body.is_enriched is not False:
        patch["is_enriched"] = True

    if patch.get("original_source_url") and not patch.get("apply_url"):
        row = existing.data[0]
        if not row.get("apply_url"):
            patch["apply_url"] = patch["original_source_url"]

    if patch.get("apply_url") or patch.get("apply_email"):
        patch["apply_source"] = "enriched"

    supabase.table("jobs").update(patch).eq("id", job_id).execute()

    refreshed = (
        supabase.table("jobs")
        .select("*, job_skills(skills(name))")
        .eq("id", job_id)
        .single()
        .execute()
    )
    if not refreshed.data:
        raise HTTPException(status_code=500, detail="Failed to load updated job")
    return hydrate_job_row(refreshed.data)


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
    await _attach_job_skills(supabase, job["id"], skills_required)

    return Job(**job)


def _build_aggregator_blacklist(settings: Settings) -> list[str]:
    """Lowercased aggregator-domain list ready for substring matching."""
    return [
        d.strip().lower()
        for d in (settings.aggregator_domains_blacklist or "").split(",")
        if d.strip()
    ]


def _merge_contact_fields(existing: dict, incoming: dict) -> dict[str, object]:
    """Fill missing apply contacts on an existing row from a new scrape."""
    patch: dict[str, object] = {}
    for field in ("apply_url", "apply_email", "contact_phone"):
        if not existing.get(field) and incoming.get(field):
            patch[field] = incoming[field]
    return patch


async def _merge_duplicate_ingest(
    supabase,
    job_id: str,
    job: JobCreate,
    incoming: dict,
) -> tuple[str, str]:
    """Append provenance + contacts to an existing fingerprint match."""
    from datetime import datetime, timezone

    row_res = (
        supabase.table("jobs")
        .select(
            "id, apply_url, apply_email, contact_phone, admin_published, "
            "scraping_sources, source_url"
        )
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    if not row_res.data:
        return "error", "duplicate_job_missing"

    existing = row_res.data[0]
    now = datetime.now(timezone.utc).isoformat()
    patch: dict[str, object] = {"updated_at": now}

    sources = merge_scraping_sources(
        existing.get("scraping_sources"),
        job.source_url or incoming.get("source_url"),
        scraped_at=now,
    )
    if job.source_url and not existing.get("source_url"):
        patch["source_url"] = job.source_url
    patch["scraping_sources"] = sources
    patch.update(_merge_contact_fields(existing, incoming))

    merged_row = {**existing, **patch}
    apply_contact_activation(merged_row)
    patch["is_active"] = merged_row["is_active"]

    supabase.table("jobs").update(patch).eq("id", job_id).execute()
    return "merged", ""


async def _ingest_one_job(
    supabase,
    job: JobCreate,
    aggregator_blacklist: list[str],
    *,
    _skip_split: bool = False,
) -> tuple[str, str]:
    """Run the full per-row ingest pipeline on one JobCreate.

    Returns (status, detail) where status is one of:
      - "ingested" — row inserted, fingerprint stored, skills linked.
      - "merged" — fingerprint match; provenance/contacts updated on existing row.
      - "duplicate" — reserved for legacy no-op duplicates (unused after merge path).
      - "skipped" — apply_url/source_url matched the aggregator blacklist.
      - "error" — anything else; detail carries the short reason.

    Shared between the n8n bulk-ingest route and Slice F's WhatsApp
    channel ingest path so both go through the same HTML-strip /
    fingerprint-dedup / embedding / skills-link pipeline. Mutating
    `job.description` here (HTML strip) is intentional — see the comment
    in the body.
    """
    try:
        if not _skip_split:
            expanded = await split_multi_role_listing(
                job.model_dump(mode="json"), None
            )
            if len(expanded) > 1:
                last_status = "ingested"
                last_detail = ""
                any_ok = False
                for child in expanded:
                    child_job = JobCreate.model_validate(child)
                    status, detail = await _ingest_one_job(
                        supabase,
                        child_job,
                        aggregator_blacklist,
                        _skip_split=True,
                    )
                    if status == "ingested":
                        any_ok = True
                    last_status, last_detail = status, detail
                if any_ok:
                    return "ingested", ""
                return last_status, last_detail

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

        original_contact_phone = job.contact_phone

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

        job_data = job.model_dump(exclude_none=True, mode="json")
        skills_required = job_data.pop("skills_required", [])
        job_data.pop("salary_text", None)
        merge_description_extraction(job_data, job_data.get("description"))
        apply_url_raw = job_data.get("apply_url")
        if apply_url_raw and is_aggregator(str(apply_url_raw)):
            contacts = await resolve_apply_contacts_from_aggregator_url(
                str(apply_url_raw)
            )
            merge_resolved_apply_contacts(
                job_data,
                contacts,
                original_apply_url=str(apply_url_raw),
            )
        if not job_data.get("closing_date"):
            extracted_deadline = await extract_closing_date_llm(
                job.description,
                job.title,
                job.company or "",
            )
            if extracted_deadline:
                job_data["closing_date"] = extracted_deadline.isoformat()

        apply_ingest_quality_to_job_data(
            job_data,
            original_contact_phone=original_contact_phone,
        )
        if job.parent_listing_signature:
            job_data["parent_listing_signature"] = job.parent_listing_signature

        if existing.data:
            return await _merge_duplicate_ingest(
                supabase,
                existing.data[0]["job_id"],
                job,
                job_data,
            )

        try:
            embedding = await generate_embedding(
                f"{job.title} {job.company or ''} {job.description}"
            )
        except Exception as exc:
            return "error", f"embedding_failed: {type(exc).__name__}"

        job_data["embedding"] = embedding
        if job.source_url:
            job_data["scraping_sources"] = merge_scraping_sources(
                job_data.get("scraping_sources"),
                job.source_url,
            )
        review = compute_review_state(
            apply_url=job_data.get("apply_url"),
            apply_email=job_data.get("apply_email"),
            contact_phone=job_data.get("contact_phone"),
            closing_date=job_data.get("closing_date"),
            application_instructions=job.application_instructions,
            instructions_have_contact=_instructions_have_contact(
                job.application_instructions
            ),
            admin_published=job_data.get("admin_published"),
        )
        apply_review_state_to_row(job_data, review)
        apply_contact_activation(job_data)
        if job_data.get("deactivation_reason"):
            job_data["is_active"] = False
        review_reasons = (
            [p.strip() for p in (job_data.get("admin_review_reason") or "").split(",") if p.strip()]
        )

        result = supabase.table("jobs").insert(job_data).execute()
        if not result.data:
            return "error", "insert_returned_empty"

        new_job = result.data[0]
        job_id = new_job["id"]
        if review_reasons:
            _emit_analytics_event(
                supabase,
                "job_eligibility_flagged",
                {"job_id": job_id, "reasons": review_reasons},
            )
        supabase.table("job_fingerprints").insert(
            {"fingerprint": fp, "job_id": job_id}
        ).execute()
        skills_for_job = skills_dictionary.record_raw_skills(
            supabase, skills_required
        )
        await _attach_job_skills(supabase, job_id, skills_for_job)

        try:
            enrichment = await enrich_job(
                title=job.title,
                company=job.company,
                description=job.description,
            )
            await apply_job_enrichment(
                supabase,
                job_id=job_id,
                job_row=new_job,
                enrichment=enrichment,
                source="ingest",
            )
        except Exception as exc:
            logger.warning(
                "ingest_one_job: enrichment failed for job %s (%r): %s",
                job_id,
                job.title,
                exc,
            )

        schedule_deep_link_enrichment(supabase, job_id, new_job)
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
    merged = 0
    skipped = 0
    errors: list[JobIngestErrorItem] = []

    for idx, job in enumerate(body.jobs):
        status, detail = await _ingest_one_job(supabase, job, aggregator_blacklist)
        if status == "ingested":
            ingested += 1
        elif status == "merged":
            merged += 1
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
        merged=merged,
        skipped=skipped,
        errors=errors[:50],  # cap to keep response size bounded
    )
