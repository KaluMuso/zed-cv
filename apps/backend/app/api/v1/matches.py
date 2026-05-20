"""Matching routes."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks, Header
from app.core.config import Settings, get_settings
from app.core.deps import get_supabase, get_current_user_id, get_current_user, is_superadmin
from app.core.rate_limit import limiter
from app.schemas.matching import MatchResult, MatchList, CronTickResponse, NotificationDigestResponse
from app.schemas.jobs import Job
from app.services.matching import (
    run_matching_for_user,
    store_matches,
    check_match_quota,
    credit_matches_for_cycle,
    get_credited_match_count,
    get_user_tier_limit,
)
from app.services.matching import apply_preferences_to_match
from app.services.email import send_match_digest_email
from app.services.whatsapp import send_match_digest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["Matching"])

_AUTO_MATCH_CADENCE_HOURS: dict[str, int | None] = {
    "free": None,
    "starter": 24,
    "professional": 24,
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

    channels = _channels(user)
    sent = False
    if channels["whatsapp"] and user.get("phone"):
        try:
            await send_match_digest(
                user["phone"],
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
    if channels["email"]:
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

    # Phase 2 Initiative #4 — preference-aware re-rank. Read the user's
    # row (None on fresh accounts; harmless — apply_preferences_to_match
    # treats None as no adjustment). Wrapped so a DB hiccup on the
    # preferences table never breaks /matches itself.
    preferences = None
    try:
        pref_res = (
            supabase.table("user_preferences")
            .select("target_roles, salary_min, salary_max, salary_frequency, "
                    "preferred_work_arrangement, acceptable_regions")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if pref_res.data:
            preferences = pref_res.data[0]
    except Exception:
        logger.warning("user_preferences read failed in /matches", exc_info=True)

    matches: list[MatchResult] = []
    for m in result.data or []:
        job_data = m.pop("jobs", {})
        adjusted_score, adjusted_bonus, adjustment_note = apply_preferences_to_match(
            base_score=m["score"],
            base_bonus=m["bonus_score"],
            job=job_data,
            preferences=preferences,
        )
        explanation = m.get("explanation") or ""
        if adjustment_note and adjustment_note not in explanation:
            explanation = (explanation + " " + adjustment_note).strip()
        matches.append(MatchResult(
            id=m["id"], job=Job(**job_data), score=adjusted_score,
            vector_score=m["vector_score"], skill_score=m["skill_score"],
            bonus_score=adjusted_bonus,
            experience_score=m.get("experience_score"),
            matched_skills=m.get("matched_skills", []), missing_skills=m.get("missing_skills", []),
            explanation=explanation or None, created_at=m["created_at"],
        ))

    # Re-sort by the adjusted score and trim to the requested limit.
    matches.sort(key=lambda mr: mr.score, reverse=True)
    return MatchList(
        matches=matches[:limit],
        remaining_quota=remaining,
        credited_count=credited_count,
        matches_limit=matches_limit,
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
        .select("id, subscription_tier, last_auto_match_at, auto_match_enabled, notification_channels, last_notification_at, phone")
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
        .select("id, phone, auto_match_enabled, notification_channels, last_notification_at")
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
