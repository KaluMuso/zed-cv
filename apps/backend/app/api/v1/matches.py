"""Matching routes."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks, Header
from app.core.config import Settings, get_settings
from app.core.deps import (
    get_supabase,
    get_current_user_id,
    get_current_user,
    is_superadmin,
)
from app.core.tier_gating import FEATURE_JOB_MATCHES, verify_tier_access
from app.core.rate_limit import limiter
from app.schemas.matching import (
    MatchResult,
    MatchList,
    MatchRefreshResponse,
    CronTickResponse,
    NotificationDigestResponse,
)
from app.services.batch_matching import (
    fetch_cached_batch_matches,
    get_latest_batch_for_user,
    run_on_demand_match_for_user,
)
from app.schemas.jobs import Job
from app.services.matching import (
    run_matching_for_user,
    store_matches,
    check_match_quota,
    credit_matches_for_cycle,
    get_credited_match_count,
    get_user_tier_limit,
    fetch_jobs_by_ids,
)
from app.services.matching import apply_preferences_to_match
from app.services.email import send_match_digest_email
from app.services.notification_channels import wants_email_digest, wants_whatsapp_digest
from app.services.quiet_hours import user_in_quiet_hours
from app.services.whatsapp import send_match_digest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["Matching"])

_AUTO_MATCH_CADENCE_HOURS: dict[str, int | None] = {
    "free": None,
    "starter": 24,
    "professional": 12,
    "super_standard": 12,
}


def _require_ingest_header(
    settings: Settings,
    ingest_api_key: str | None,
    x_ingest_api_key: str | None,
) -> None:
    supplied = ingest_api_key or x_ingest_api_key
    if not settings.ingest_api_key or supplied != settings.ingest_api_key:
        raise HTTPException(status_code=401, detail="Invalid ingest API key")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _channels(row: dict) -> dict[str, bool]:
    raw = row.get("notification_channels")
    if isinstance(raw, dict):
        return {
            "whatsapp": bool(raw.get("whatsapp", True)),
            "email": bool(raw.get("email", True)),
        }
    return {"whatsapp": True, "email": True}


def _row_needs_auto_match(row: dict, now: datetime) -> bool:
    if row.get("auto_match_enabled") is False:
        return False
    tier = row.get("subscription_tier") or "free"
    hours = _AUTO_MATCH_CADENCE_HOURS.get(tier)
    if hours is None:
        return False
    last = _parse_dt(row.get("last_auto_match_at"))
    return last is None or last <= now - timedelta(hours=hours)


def _notification_due(row: dict, now: datetime) -> bool:
    last = _parse_dt(row.get("last_notification_at"))
    return last is None or last <= now - timedelta(hours=24)


async def _load_user_preferences(user_id: str, supabase) -> dict | None:
    try:
        pref_res = (
            supabase.table("user_preferences")
            .select(
                "target_roles, salary_min, salary_max, salary_frequency, "
                "preferred_work_arrangement, acceptable_regions"
            )
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if pref_res.data:
            return pref_res.data[0]
    except Exception:
        logger.warning("user_preferences read failed", exc_info=True)
    return None


def _rows_to_match_results(
    rows: list[dict],
    preferences: dict | None,
) -> list[MatchResult]:
    matches: list[MatchResult] = []
    for raw in rows:
        m = dict(raw)
        job_data = m.pop("jobs", {}) if isinstance(m, dict) else {}
        adjusted_score, adjusted_bonus, adjustment_note = apply_preferences_to_match(
            base_score=m["score"],
            base_bonus=float(m.get("bonus_score") or 0),
            job=job_data,
            preferences=preferences,
        )
        explanation = m.get("explanation") or ""
        if adjustment_note and adjustment_note not in explanation:
            explanation = (explanation + " " + adjustment_note).strip()
        matches.append(
            MatchResult.from_stored_row(
                job=Job(**job_data),
                row=m,
                adjusted_score=adjusted_score,
                adjusted_bonus=adjusted_bonus,
                explanation=explanation or None,
            )
        )
    matches.sort(key=lambda mr: mr.score, reverse=True)
    return matches


async def _build_match_list_response(
    user_id: str,
    supabase,
    *,
    stored_rows: list[dict],
    last_batch_run_at: str | None = None,
    from_cache: bool = False,
    limit: int = 50,
) -> MatchList:
    _, remaining = await check_match_quota(user_id, supabase)
    _, matches_limit, _ = await get_user_tier_limit(user_id, supabase)
    credited_count = await get_credited_match_count(user_id, supabase)
    preferences = await _load_user_preferences(user_id, supabase)
    matches = _rows_to_match_results(list(stored_rows), preferences)
    parsed_batch_at = _parse_dt(last_batch_run_at)
    return MatchList(
        matches=matches[:limit],
        remaining_quota=remaining,
        credited_count=credited_count,
        matches_limit=matches_limit,
        last_batch_run_at=parsed_batch_at,
        from_cache=from_cache,
    )


async def _primary_cv_id(user_id: str, supabase) -> str | None:
    cv_result = (
        supabase.table("cvs")
        .select("id")
        .eq("user_id", user_id)
        .eq("is_primary", True)
        .limit(1)
        .execute()
    )
    return cv_result.data[0]["id"] if cv_result.data else None


async def _match_and_credit_user(user_id: str, cv_id: str, supabase) -> int:
    matches = await run_matching_for_user(user_id, supabase)
    await store_matches(user_id, cv_id, matches, supabase)
    return await credit_matches_for_cycle(
        user_id,
        [m["job_id"] for m in matches if m.get("job_id")],
        supabase,
    )


async def _send_due_digest(user: dict, supabase, now: datetime) -> bool:
    if not _notification_due(user, now):
        return False
    rows = (
        supabase.table("matches")
        .select("score, matched_skills, credited_at, jobs(title, company, apply_url, source_url)")
        .eq("user_id", user["id"])
        .gte("credited_at", (now - timedelta(hours=24)).isoformat())
        .order("score", desc=True)
        .limit(5)
        .execute()
    )
    matches = rows.data or []
    if not matches:
        return False

    legacy = _channels(user)
    sent = False
    phone = (user.get("whatsapp_number") or user.get("phone") or "").strip()
    if (
        wants_whatsapp_digest(user)
        and phone
        and legacy.get("whatsapp", True)
        and not user_in_quiet_hours(user, now)
    ):
        try:
            await send_match_digest(
                phone,
                [
                    {
                        "title": (m.get("jobs") or {}).get("title"),
                        "company": (m.get("jobs") or {}).get("company"),
                        "score": m.get("score", 0),
                        "matched_skills": m.get("matched_skills", []),
                    }
                    for m in matches[:3]
                ],
            )
            sent = True
        except Exception:
            logger.warning("auto-match WhatsApp digest failed for user=%s", user["id"], exc_info=True)
    if wants_email_digest(user) and legacy.get("email", True):
        try:
            sent = bool(await send_match_digest_email(user["id"], matches[:5], supabase)) or sent
        except Exception:
            logger.warning("auto-match email digest failed for user=%s", user["id"], exc_info=True)

    if sent:
        supabase.table("users").update(
            {"last_notification_at": now.isoformat()}
        ).eq("id", user["id"]).execute()
    return sent


@router.get("", response_model=MatchList)
async def get_matches(
    min_score: float = Query(50, ge=0, le=100), limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id), supabase=Depends(get_supabase),
):
    _, remaining = await check_match_quota(user_id, supabase)
    _, matches_limit, _ = await get_user_tier_limit(user_id, supabase)
    credited_count = await get_credited_match_count(user_id, supabase)
    # Pull a wider candidate set than `limit` so the preferences-aware
    # re-rank below can actually move things around. Without this, a
    # 10-row LIMIT means re-ranking can only shuffle within 10 rows,
    # which defeats the purpose. 50 is a reasonable upper bound — the
    # RPC writes at most 20 per run today.
    candidate_limit = max(limit * 3, 30)
    result = (
        supabase.table("matches").select("*, jobs(*)").eq("user_id", user_id)
        .gte("score", min_score).order("score", desc=True).limit(candidate_limit).execute()
    )

    preferences = await _load_user_preferences(user_id, supabase)
    matches = _rows_to_match_results(list(result.data or []), preferences)
    return MatchList(
        matches=matches[:limit],
        remaining_quota=remaining,
        credited_count=credited_count,
        matches_limit=matches_limit,
    )


async def _increment_match_views_after_response(
    user_id: str, count: int, supabase
) -> None:
    """Background quota decrement — runs after the HTTP response is sent."""
    if count <= 0:
        return
    try:
        from app.core.tier_gating import increment_matches_viewed

        await increment_matches_viewed(user_id, supabase, count=count)
    except Exception:
        logger.warning(
            "deferred match view increment failed user=%s count=%s",
            user_id,
            count,
            exc_info=True,
        )


@router.get("/{user_id}", response_model=MatchList)
async def get_matches_for_user(
    background_tasks: BackgroundTasks,
    user_id: str,
    min_score: float = Query(50, ge=0, le=100),
    limit: int = Query(10, ge=1, le=50),
    current_user_id: str = Depends(get_current_user_id),
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    """Live hybrid scores from match_jobs_for_user RPC (50/20/15/10/5 breakdown)."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot view another user's matches")

    await verify_tier_access(
        FEATURE_JOB_MATCHES,
        user_id,
        supabase,
        is_superadmin=is_superadmin(current_user),
    )

    _, remaining = await check_match_quota(user_id, supabase)
    _, matches_limit, _ = await get_user_tier_limit(user_id, supabase)
    credited_count = await get_credited_match_count(user_id, supabase)

    try:
        rpc_rows = await run_matching_for_user(
            user_id, supabase, limit=limit, min_score=min_score
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        logger.exception("match_jobs_for_user RPC failed for user=%s", user_id)
        raise HTTPException(
            status_code=503,
            detail="Matching is temporarily unavailable. Try again shortly.",
        )

    job_ids = [str(row["job_id"]) for row in rpc_rows if row.get("job_id")]
    jobs_by_id = await fetch_jobs_by_ids(job_ids, supabase)

    stored_by_job: dict[str, dict] = {}
    if job_ids:
        stored_res = (
            supabase.table("matches")
            .select("id, job_id, created_at, explanation")
            .eq("user_id", user_id)
            .in_("job_id", job_ids)
            .execute()
        )
        stored_by_job = {
            str(row["job_id"]): row
            for row in (stored_res.data or [])
            if isinstance(row, dict) and row.get("job_id")
        }

    preferences = None
    try:
        pref_res = (
            supabase.table("user_preferences")
            .select(
                "target_roles, salary_min, salary_max, salary_frequency, "
                "preferred_work_arrangement, acceptable_regions"
            )
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if pref_res.data:
            preferences = pref_res.data[0]
    except Exception:
        logger.warning(
            "user_preferences read failed in /matches/{user_id}", exc_info=True
        )

    matches: list[MatchResult] = []
    for row in rpc_rows:
        job_id = str(row.get("job_id") or "")
        job_data = jobs_by_id.get(job_id)
        if not job_data:
            continue
        stored = stored_by_job.get(job_id, {})
        adjusted_score, adjusted_bonus, adjustment_note = apply_preferences_to_match(
            base_score=float(row.get("final_score") or row.get("score") or 0),
            base_bonus=float(row.get("bonus_score") or 0),
            job=job_data,
            preferences=preferences,
        )
        explanation = stored.get("explanation") or row.get("explanation") or ""
        if adjustment_note and adjustment_note not in explanation:
            explanation = (explanation + " " + adjustment_note).strip()
        matches.append(
            MatchResult.from_rpc_row(
                job=Job(**job_data),
                row=row,
                match_id=stored.get("id") or job_id,
                created_at=stored.get("created_at")
                or datetime.now(timezone.utc),
                explanation=explanation or None,
                adjusted_score=adjusted_score,
                adjusted_bonus=adjusted_bonus,
            )
        )

    matches.sort(key=lambda mr: mr.score, reverse=True)
    delivered = matches[:limit]
    view_count = len(delivered)
    await verify_tier_access(
        FEATURE_JOB_MATCHES,
        user_id,
        supabase,
        increment_match_views=view_count,
        defer_match_view_increment=True,
        is_superadmin=is_superadmin(current_user),
    )
    if view_count > 0 and not is_superadmin(current_user):
        background_tasks.add_task(
            _increment_match_views_after_response,
            user_id,
            view_count,
            supabase,
        )
    return MatchList(
        matches=delivered,
        remaining_quota=remaining,
        credited_count=credited_count,
        matches_limit=matches_limit,
    )


@router.post("/refresh", response_model=MatchRefreshResponse)
@limiter.limit("5/minute")
async def refresh_matches(
    request: Request,
    min_score: float = Query(50, ge=0, le=100),
    limit: int = Query(50, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Return cached nightly batch matches; live RPC only when none exist yet."""
    batch_id, batch_at = await get_latest_batch_for_user(user_id, supabase)
    if batch_id:
        rows = await fetch_cached_batch_matches(
            user_id,
            supabase,
            batch_run_id=batch_id,
            min_score=min_score,
            limit=limit,
        )
        body = await _build_match_list_response(
            user_id,
            supabase,
            stored_rows=rows,
            last_batch_run_at=batch_at,
            from_cache=True,
            limit=limit,
        )
        return MatchRefreshResponse(**body.model_dump(), message=None)

    cv_id = await _primary_cv_id(user_id, supabase)
    if not cv_id:
        raise HTTPException(status_code=422, detail="Upload a CV first before matching")

    try:
        await run_on_demand_match_for_user(user_id, cv_id, supabase, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        logger.exception("on-demand match fallback failed for user=%s", user_id)
        raise HTTPException(
            status_code=503,
            detail="Matching is temporarily unavailable. Try again shortly.",
        )

    batch_id, batch_at = await get_latest_batch_for_user(user_id, supabase)
    rows = await fetch_cached_batch_matches(
        user_id,
        supabase,
        batch_run_id=batch_id or "",
        min_score=min_score,
        limit=limit,
    )
    body = await _build_match_list_response(
        user_id,
        supabase,
        stored_rows=rows,
        last_batch_run_at=batch_at,
        from_cache=False,
        limit=limit,
    )
    return MatchRefreshResponse(
        **body.model_dump(),
        message="Your first matches are computing — check back in a moment.",
    )


@router.post("/trigger")
@limiter.limit("3/minute")
async def trigger_matching(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    user_id = current_user["id"]

    if not is_superadmin(current_user):
        await check_match_quota(user_id, supabase)

    cv_id = await _primary_cv_id(user_id, supabase)
    if not cv_id:
        raise HTTPException(status_code=422, detail="Upload a CV first before matching")

    background_tasks.add_task(_run_matching_task, user_id, cv_id, supabase)
    return {"message": "Matching started. Results will be available shortly.", "estimated_seconds": 15}


async def _run_matching_task(user_id: str, cv_id: str, supabase):
    # Background task: must not propagate exceptions (would crash the
    # worker silently). But we MUST log them — a silent except-pass here
    # is what hid the match_jobs_for_user 42804 type-mismatch in prod for
    # weeks (slice 2D-1f).
    try:
        new_credited = await _match_and_credit_user(user_id, cv_id, supabase)
        if new_credited:
            digest_rows = (
                supabase.table("matches")
                .select("score, jobs(title, company)")
                .eq("user_id", user_id)
                .not_.is_("credited_at", "null")
                .order("score", desc=True)
                .limit(5)
                .execute()
            )
            try:
                await send_match_digest_email(user_id, digest_rows.data or [], supabase)
            except Exception:
                logger.warning(
                    "match digest email failed for user=%s", user_id, exc_info=True
                )
    except Exception:
        logger.error(
            "matching task failed for user=%s cv=%s", user_id, cv_id, exc_info=True
        )


@router.post("/cron-tick", response_model=CronTickResponse)
async def cron_tick(
    limit: int = Query(100, ge=1, le=500),
    ingest_api_key: str | None = Header(None, alias="INGEST_API_KEY"),
    x_ingest_api_key: str | None = Header(None, alias="X-INGEST-API-KEY"),
    supabase=Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    _require_ingest_header(settings, ingest_api_key, x_ingest_api_key)
    now = datetime.now(timezone.utc)
    users_res = (
        supabase.table("users")
        .select(
            "id, subscription_tier, last_auto_match_at, auto_match_enabled, "
            "notification_channels, last_notification_at, phone, email, "
            "whatsapp_number, whatsapp_verified, email_notifications_enabled, "
            "preferred_notification_channel, quiet_hours_start, quiet_hours_end, "
            "display_timezone"
        )
        .eq("auto_match_enabled", True)
        .neq("subscription_tier", "free")
        .limit(limit)
        .execute()
    )

    users_processed = 0
    new_matches_total = 0
    for user in users_res.data or []:
        if not _row_needs_auto_match(user, now):
            continue
        cv_id = await _primary_cv_id(user["id"], supabase)
        if not cv_id:
            continue
        new_credited = await _match_and_credit_user(user["id"], cv_id, supabase)
        users_processed += 1
        new_matches_total += new_credited
        supabase.table("users").update(
            {"last_auto_match_at": now.isoformat()}
        ).eq("id", user["id"]).execute()
        if new_credited:
            await _send_due_digest(user, supabase, now)

    return CronTickResponse(
        users_processed=users_processed,
        new_matches_total=new_matches_total,
    )


@router.post("/send-notifications", response_model=NotificationDigestResponse)
async def send_notifications(
    limit: int = Query(100, ge=1, le=500),
    ingest_api_key: str | None = Header(None, alias="INGEST_API_KEY"),
    x_ingest_api_key: str | None = Header(None, alias="X-INGEST-API-KEY"),
    supabase=Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    _require_ingest_header(settings, ingest_api_key, x_ingest_api_key)
    now = datetime.now(timezone.utc)
    users_res = (
        supabase.table("users")
        .select(
            "id, phone, email, subscription_tier, auto_match_enabled, "
            "notification_channels, last_notification_at, whatsapp_number, "
            "whatsapp_verified, email_notifications_enabled, preferred_notification_channel, "
            "quiet_hours_start, quiet_hours_end, display_timezone"
        )
        .eq("auto_match_enabled", True)
        .limit(limit)
        .execute()
    )
    users_processed = 0
    notifications_sent = 0
    for user in users_res.data or []:
        if not _notification_due(user, now):
            continue
        users_processed += 1
        if await _send_due_digest(user, supabase, now):
            notifications_sent += 1
    return NotificationDigestResponse(
        users_processed=users_processed,
        notifications_sent=notifications_sent,
    )
