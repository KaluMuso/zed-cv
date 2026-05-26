"""Admin routes — superadmin only.

All endpoints require role = 'superadmin'. The frontend's AdminGuard
mirrors this check, but the API enforces it as the source of truth.
"""
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.deps import get_supabase, require_admin
from app.services.matching import get_credited_match_count
from app.schemas.admin import (
    AdminParserStats,
    AdminLlmCostStats,
    AdminLlmCostByModel,
    AdminLlmCostByFeature,
    AdminLlmCostDay,
    AdminScraperStats,
    AdminScraperStatsDay,
    AdminStats,
    AdminUserRow,
    AdminUserList,
    AdminJobRow,
    AdminJobList,
    BulkDeactivateRequest,
    BulkDeactivateResponse,
    AdminPaymentRow,
    AdminPaymentList,
    AdminMatchRow,
    AdminMatchList,
    AdminTierBreakdown,
    AdminSubscriptionRow,
    AdminSubscriptionList,
    AdminSubscriptionUpdate,
    AdminWelcomeBonusUpdate,
    AdminJobReviewRow,
    AdminJobReviewQueue,
    AdminJobReviewUpdate,
)
from app.schemas.jobs import AdminJobCreate, AdminJobUpdate, Job
from app.core.tier_gating import get_effective_match_limit
from app.services.tier_config import get_tier_limits
from app.schemas.db_enums import QueueStatus
from app.services.embedding import generate_embedding
from app.services.llm import DASHBOARD_FEATURES
from app.services.skill_resolver import resolve_skill_id, resolve_skill_ids

logger = logging.getLogger(__name__)


def _emit_analytics_event(
    supabase,
    event: str,
    properties: dict,
    user_id: Optional[str],
) -> None:
    """Fire-and-forget write to analytics_events. Never raises.

    Mirrors the inline pattern from skill_resolver._log_auto_insert
    (PR #27). Column is `event` (singular). Failures are logged at
    debug — analytics must never block the user-facing write.
    """
    try:
        supabase.table("analytics_events").insert(
            {"event": event, "properties": properties, "user_id": user_id}
        ).execute()
    except Exception as exc:  # pragma: no cover - logging path
        logger.debug("analytics_events insert failed (%s): %s", event, exc)


def _split_review_reasons(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


# Fields whose change forces an embedding regenerate. These match the
# inputs to generate_embedding() in the ingest path
# (title + company + description) plus the two structured fields
# (requirements, tools_tech_stack) per the Wave 4 brief.
_EMBEDDING_TRIGGER_FIELDS = {
    "title", "description", "requirements", "tools_tech_stack",
}

# Fields whose change forces a dedup-fingerprint recompute. These
# correspond 1:1 with the inputs to _fingerprint() in jobs.py.
_FINGERPRINT_TRIGGER_FIELDS = {"title", "company", "description"}

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/stats", response_model=AdminStats)
async def get_stats(supabase=Depends(get_supabase)):
    """Aggregate counters for the admin dashboard."""
    rpc_res = supabase.rpc("admin_stats").execute()
    data = rpc_res.data
    # supabase-py may return: a dict (jsonb output), a list-of-one (SETOF),
    # a bool (some RPCs), or None. Normalize to a dict and let AdminStats
    # apply its own defaults for missing fields.
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        data = {}
    try:
        pending = (
            supabase.table("jobs")
            .select("id", count="exact")
            .not_.is_("admin_review_reason", "null")
            .is_("admin_reviewed_at", "null")
            .execute()
        )
        data["pending_review_count"] = pending.count or 0
    except Exception:
        logger.warning("admin pending review count failed", exc_info=True)
    return AdminStats(**data)


def _aggregate_llm_cost_rows(rows: list[dict], *, days: int) -> AdminLlmCostStats:
    """Roll up llm_usage_log rows for the admin cost panel."""
    by_model: dict[str, dict[str, float | int]] = {}
    by_feature: dict[str, dict[str, float | int]] = {}
    by_day: dict[str, float] = {}
    total_cost = 0.0
    total_requests = 0

    for row in rows:
        cost = float(row.get("cost_usd") or 0)
        prompt = int(row.get("prompt_tokens") or 0)
        completion = int(row.get("completion_tokens") or 0)
        model = str(row.get("model") or "unknown")
        feature = str(row.get("feature") or "other")
        created = row.get("created_at")
        day_key = str(created)[:10] if created else ""

        total_cost += cost
        total_requests += 1
        by_day[day_key] = by_day.get(day_key, 0.0) + cost

        mb = by_model.setdefault(
            model,
            {"cost_usd": 0.0, "request_count": 0, "prompt_tokens": 0, "completion_tokens": 0},
        )
        mb["cost_usd"] = float(mb["cost_usd"]) + cost
        mb["request_count"] = int(mb["request_count"]) + 1
        mb["prompt_tokens"] = int(mb["prompt_tokens"]) + prompt
        mb["completion_tokens"] = int(mb["completion_tokens"]) + completion

        fb = by_feature.setdefault(feature, {"cost_usd": 0.0, "request_count": 0})
        fb["cost_usd"] = float(fb["cost_usd"]) + cost
        fb["request_count"] = int(fb["request_count"]) + 1

    model_rows = [
        AdminLlmCostByModel(
            model=m,
            cost_usd=round(float(v["cost_usd"]), 6),
            request_count=int(v["request_count"]),
            prompt_tokens=int(v["prompt_tokens"]),
            completion_tokens=int(v["completion_tokens"]),
        )
        for m, v in sorted(by_model.items(), key=lambda x: -float(x[1]["cost_usd"]))
    ]

    feature_order = {f: i for i, f in enumerate(DASHBOARD_FEATURES)}
    feature_rows = [
        AdminLlmCostByFeature(
            feature=f,
            cost_usd=round(float(v["cost_usd"]), 6),
            request_count=int(v["request_count"]),
        )
        for f, v in sorted(
            by_feature.items(),
            key=lambda x: (feature_order.get(x[0], 99), -float(x[1]["cost_usd"])),
        )
    ]

    daily_rows = [
        AdminLlmCostDay(date=day, cost_usd=round(cost, 6))
        for day, cost in sorted(by_day.items())
    ]

    return AdminLlmCostStats(
        days=days,
        total_cost_usd=round(total_cost, 6),
        total_requests=total_requests,
        by_model=model_rows,
        by_feature=feature_rows,
        daily=daily_rows,
    )


@router.get("/llm-cost-stats", response_model=AdminLlmCostStats)
async def get_llm_cost_stats(
    supabase=Depends(get_supabase),
    days: int = Query(7, ge=1, le=90, description="Rolling window in calendar days"),
):
    """Rolling LLM cost by model and product feature (llm_usage_log)."""
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    since_iso = since.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    try:
        rows_res = (
            supabase.table("llm_usage_log")
            .select(
                "feature, model, prompt_tokens, completion_tokens, cost_usd, created_at"
            )
            .gte("created_at", since_iso)
            .execute()
        )
        rows = rows_res.data or []
    except Exception as exc:
        logger.warning("llm-cost-stats query failed: %s", exc)
        rows = []

    return _aggregate_llm_cost_rows(rows, days=days)


@router.get("/scraper-stats", response_model=AdminScraperStats)
async def get_scraper_stats(
    supabase=Depends(get_supabase),
    days: int = Query(7, ge=1, le=90, description="Number of calendar days to include"),
):
    """Daily WhatsApp classifier decisions from ai_cache metadata (Track 4c)."""
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    since_iso = since.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    try:
        rows_res = (
            supabase.table("ai_cache")
            .select("metadata, created_at")
            .eq("cache_type", "whatsapp_classify")
            .gte("created_at", since_iso)
            .execute()
        )
        rows = rows_res.data or []
    except Exception as exc:
        logger.warning("scraper-stats query failed: %s", exc)
        rows = []

    by_day: dict[str, dict[str, int]] = {}
    totals = {
        "accepted_as_job": 0,
        "rejected_as_promo": 0,
        "rejected_as_other": 0,
    }

    for row in rows:
        meta = row.get("metadata") or {}
        if not isinstance(meta, dict):
            continue
        decision = meta.get("classifier_decision")
        if decision not in totals:
            continue
        created = row.get("created_at")
        day_key = str(created)[:10] if created else since.strftime("%Y-%m-%d")
        bucket = by_day.setdefault(
            day_key,
            {
                "accepted_as_job": 0,
                "rejected_as_promo": 0,
                "rejected_as_other": 0,
            },
        )
        bucket[decision] += 1
        totals[decision] += 1

    day_rows = [
        AdminScraperStatsDay(
            date=day,
            accepted_as_job=counts["accepted_as_job"],
            rejected_as_promo=counts["rejected_as_promo"],
            rejected_as_other=counts["rejected_as_other"],
        )
        for day, counts in sorted(by_day.items())
    ]

    return AdminScraperStats(
        days=day_rows,
        accepted_as_job=totals["accepted_as_job"],
        rejected_as_promo=totals["rejected_as_promo"],
        rejected_as_other=totals["rejected_as_other"],
        parsers=_aggregate_parser_stats(supabase, since_iso),
    )


def _aggregate_parser_stats(supabase, since_iso: str) -> list[AdminParserStats]:
    """Roll up deep-link parser telemetry from ai_cache metadata."""
    try:
        rows_res = (
            supabase.table("ai_cache")
            .select("metadata, created_at")
            .eq("cache_type", "deep_link_parser")
            .gte("created_at", since_iso)
            .execute()
        )
        rows = rows_res.data or []
    except Exception as exc:
        logger.warning("scraper-stats parser query failed: %s", exc)
        return []

    buckets: dict[str, dict[str, int]] = {}
    for row in rows:
        meta = row.get("metadata") or {}
        if not isinstance(meta, dict):
            continue
        parser = str(meta.get("parser") or "generic")
        outcome = str(meta.get("outcome") or "failed")
        bucket = buckets.setdefault(
            parser,
            {"attempted": 0, "found_email": 0, "found_phone": 0, "failed": 0},
        )
        bucket["attempted"] += 1
        if outcome in ("found_email", "found_both"):
            bucket["found_email"] += 1
        if outcome in ("found_phone", "found_both"):
            bucket["found_phone"] += 1
        if outcome == "failed":
            bucket["failed"] += 1

    return [
        AdminParserStats(parser=parser, **counts)
        for parser, counts in sorted(buckets.items())
    ]


@router.post("/cv-queue/drain")
async def drain_cv_queue(
    limit: int = Query(20, ge=1, le=100, description="Max queue rows to drain in this call"),
    supabase=Depends(get_supabase),
):
    """Drain the cv_upload_queue — process rows that were queued when
    /cv/upload hit Gemini's rate cap.

    Called manually after a quota reset OR scheduled via n8n cron at
    00:05 UTC daily. Idempotent: each row is marked 'processing' before
    work starts, so a re-entrant call won't double-process. Bumps the
    `attempts` counter; after attempts >= 5 we mark 'failed' and stop
    retrying so the queue doesn't grow forever on a stuck row.

    Returns per-row status. Errors don't fail the batch — each row's
    failure is captured in its own row's error_message.
    """
    from app.services.cv_parser import parse_cv_with_llm
    from app.services.embedding import generate_embedding
    from app.core.config import get_settings
    import hashlib
    import logging

    settings = get_settings()
    MAX_ATTEMPTS = 5

    # FIFO grab. Status filter + index makes this cheap even with a long queue.
    queued = (
        supabase.table("cv_upload_queue")
        .select("*")
        .eq("status", "queued")
        .lt("attempts", MAX_ATTEMPTS)
        .order("queued_at", desc=False)
        .limit(limit)
        .execute()
    )

    out = {"drained": 0, "failed": 0, "rows": []}

    for row in (queued.data or []):
        row_id = row["id"]
        user_id = row["user_id"]
        raw_text = row.get("raw_text") or ""
        file_path = row["file_path"]
        file_type = row["file_type"]

        # Mark processing + bump attempts upfront. If we crash mid-flight,
        # the row stays in 'processing' until manually nudged — that's
        # intentional, manual is safer than auto-retry-storm.
        # All queue-status writes validated via the enum (migration 013
        # dropped the SQL CHECK; QueueStatus is now the source of truth).
        supabase.table("cv_upload_queue").update({
            "status": QueueStatus.processing.value,
            "attempts": row.get("attempts", 0) + 1,
            "updated_at": "NOW()",
        }).eq("id", row_id).execute()

        try:
            parsed = await parse_cv_with_llm(raw_text)
            embedding = await generate_embedding(raw_text)

            # Mirror the /cv/upload write path so the resulting cvs row
            # looks identical to a non-queued upload. is_primary=True so
            # this becomes the user's active CV.
            supabase.table("cvs").update({"is_primary": False}).eq("user_id", user_id).eq("is_primary", True).execute()
            cv_row = supabase.table("cvs").insert({
                "user_id": user_id,
                "file_url": file_path,
                "file_type": file_type,
                "raw_text": raw_text[:10000],
                "parsed_data": parsed,
                "embedding": embedding,
                "parsing_confidence": parsed.get("confidence", 0),
                "is_primary": True,
            }).execute()
            new_cv_id = cv_row.data[0]["id"] if cv_row.data else None

            # Skills linkage — same shape as /cv/upload.
            for skill_name in parsed.get("skills", []):
                sk = supabase.table("skills").select("id").eq("name", skill_name.lower()).limit(1).execute()
                skill_id = sk.data[0]["id"] if sk.data else None
                if not skill_id:
                    al = supabase.table("skill_aliases").select("skill_id").eq("alias", skill_name.lower()).limit(1).execute()
                    skill_id = al.data[0]["skill_id"] if al.data else None
                if skill_id:
                    supabase.table("user_skills").upsert(
                        {"user_id": user_id, "skill_id": skill_id, "source": "cv_parse"},
                        on_conflict="user_id,skill_id",
                    ).execute()

            supabase.table("cv_upload_queue").update({
                "status": QueueStatus.completed.value,
                "processed_at": "NOW()",
                "updated_at": "NOW()",
            }).eq("id", row_id).execute()
            out["drained"] += 1
            out["rows"].append({"id": row_id, "status": QueueStatus.completed.value, "cv_id": new_cv_id})

        except Exception as exc:
            logging.error("cv_upload_queue: row %s failed (attempt %s): %s",
                          row_id, row.get("attempts", 0) + 1, exc)
            new_status = (
                QueueStatus.queued.value
                if (row.get("attempts", 0) + 1) < MAX_ATTEMPTS
                else QueueStatus.failed.value
            )
            supabase.table("cv_upload_queue").update({
                "status": new_status,
                "error_message": f"{type(exc).__name__}: {str(exc)[:300]}",
                "updated_at": "NOW()",
            }).eq("id", row_id).execute()
            if new_status == QueueStatus.failed.value:
                out["failed"] += 1
            out["rows"].append({
                "id": row_id, "status": new_status,
                "reason": f"{type(exc).__name__}",
            })

    return out


@router.get("/email/health")
async def email_health(settings: Settings = Depends(get_settings)):
    """Resend connectivity check (domains list) — no email is sent."""
    from app.services.email_delivery import check_resend_health

    report = check_resend_health(
        resend_api_key=settings.resend_api_key,
        resend_from_email=settings.resend_from_email,
    )
    return report.as_dict()


@router.post("/waha/bootstrap-session")
async def bootstrap_waha_session_endpoint(
    session: str = Query("default", description="WAHA session name to ensure WORKING"),
    timeout: int = Query(45, ge=5, le=120, description="Max seconds to wait for WORKING"),
):
    """Manually trigger the WAHA session bootstrap.

    The backend already runs this on startup, but if WAHA restarts
    mid-runtime (container crash, OOM, manual `docker compose restart waha`),
    the startup hook won't re-fire and OTP delivery will start returning
    503s. This endpoint lets admin re-run the bootstrap without restarting
    the backend.

    Returns `{ok: bool, session: str}`. Safe to call any time — the
    underlying function is idempotent (no-op if session is already
    WORKING).
    """
    from app.services.whatsapp import ensure_session_started
    ok = await ensure_session_started(session_name=session, timeout_seconds=timeout)
    if not ok:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to bring session {session!r} to WORKING within {timeout}s. "
                   "Check WAHA logs and consider scanning a fresh QR via the dashboard.",
        )
    return {"ok": True, "session": session}


@router.post("/jobs/backfill-html-strip")
async def backfill_jobs_html_strip(
    limit: int = Query(500, ge=1, le=2000, description="Max rows to scan per call"),
    dry_run: bool = Query(False, description="If true, count rows that would change but don't write"),
    supabase=Depends(get_supabase),
):
    """One-shot backfill: sanitize HTML in existing jobs.description rows.

    The 2026-05-13 slice added `_strip_html` to ingest_jobs and create_job
    so all NEW rows land as plain text. Existing rows from before that
    deploy still contain raw HTML (Quill markup, `<p>` tags, etc.) which
    renders as visible markup on the /jobs/[id] standalone page because
    whitespace-pre-wrap doesn't parse HTML.

    This endpoint scans up to `limit` rows where description still
    contains `<` or `>` and rewrites them through the same sanitizer.
    Idempotent: a row whose cleaned text equals the original is skipped.

    Returns counts so the operator knows how many rows were touched and
    whether another pass is needed.
    """
    from app.api.v1.jobs import _strip_html, _fingerprint

    # Fetch jobs whose description still looks HTML-ish. The `like` filter
    # cuts the scan to actually-affected rows; we still cap with `limit`
    # so a runaway scan can't drown a Supabase free-tier instance.
    # title + company are required to recompute the dedup fingerprint —
    # see the comment by the update below.
    res = (
        supabase.table("jobs")
        .select("id, title, company, description")
        .like("description", "%<%")
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    scanned = len(rows)
    changed = 0
    skipped = 0
    errors: list[dict] = []

    for row in rows:
        original = row.get("description") or ""
        cleaned = _strip_html(original)
        if cleaned == original:
            skipped += 1
            continue
        if dry_run:
            changed += 1
            continue
        try:
            supabase.table("jobs").update({"description": cleaned}).eq("id", row["id"]).execute()
            # CRITICAL: also rewrite the dedup fingerprint. The fingerprint
            # stored in `job_fingerprints` was hashed over the ORIGINAL HTML
            # description; once we clean the description, the next scraper
            # ingest will compute a clean-text fingerprint, miss the stale
            # one, and insert a duplicate row for every cleaned job. Skip
            # this update and the next n8n run effectively duplicates the
            # entire backfilled set.
            new_fp = _fingerprint(row["title"], row.get("company"), cleaned)
            supabase.table("job_fingerprints").update(
                {"fingerprint": new_fp}
            ).eq("job_id", row["id"]).execute()
            changed += 1
        except Exception as exc:
            errors.append({"id": row["id"], "reason": f"{type(exc).__name__}: {exc}"[:200]})

    return {
        "scanned": scanned,
        "changed": changed,
        "skipped_no_change": skipped,
        "errors": errors[:20],
        "dry_run": dry_run,
        # Hint for the operator: if scanned == limit, there might be more
        # rows to clean — run again until scanned < limit.
        "more_likely": scanned == limit,
    }


@router.post("/re-embed")
async def re_embed_all(
    target: str = Query("all", description="One of: jobs, cvs, all"),
    limit: int = Query(200, ge=1, le=2000, description="Cap on rows to re-embed in this call"),
    supabase=Depends(get_supabase),
):
    """Re-embed existing jobs and/or CVs with the current EMBEDDING_MODEL.

    Why this exists: the catalog accumulated embeddings from
    text-embedding-004 (retired May 2026) and gemini-embedding-001. Two
    different coordinate spaces in the same vector(768) column makes
    cosine similarity nonsense. This endpoint rebuilds all embeddings
    using the model that's currently configured (settings.embedding_model),
    so every row lives in the same space.

    Safe to run multiple times — it just overwrites. Idempotent within
    a single embedding model. Rate-limited by Gemini's free tier at
    1500 req/min, so a typical 100-row pass takes ~5 seconds.
    """
    from app.services.embedding import generate_embedding

    if target not in ("jobs", "cvs", "all"):
        raise HTTPException(status_code=422, detail="target must be jobs|cvs|all")

    out = {"jobs": {"updated": 0, "errors": []}, "cvs": {"updated": 0, "errors": []}}

    if target in ("jobs", "all"):
        # Use title + company + first chunk of description as the embedding
        # text — same shape as the ingest path so re-embeds match what
        # new rows look like.
        rows = (
            supabase.table("jobs")
            .select("id, title, company, description")
            .eq("is_active", True)
            .limit(limit)
            .execute()
        )
        for row in (rows.data or []):
            try:
                text = f"{row['title']} {row.get('company') or ''} {row.get('description') or ''}"
                emb = await generate_embedding(text)
                supabase.table("jobs").update({"embedding": emb}).eq("id", row["id"]).execute()
                out["jobs"]["updated"] += 1
            except Exception as exc:
                # Don't poison the batch — record the failure and keep going.
                out["jobs"]["errors"].append({"id": row.get("id"), "reason": f"{type(exc).__name__}"})

    if target in ("cvs", "all"):
        rows = (
            supabase.table("cvs")
            .select("id, raw_text")
            .limit(limit)
            .execute()
        )
        for row in (rows.data or []):
            try:
                text = (row.get("raw_text") or "").strip()
                if not text:
                    continue
                emb = await generate_embedding(text)
                supabase.table("cvs").update({"embedding": emb}).eq("id", row["id"]).execute()
                out["cvs"]["updated"] += 1
            except Exception as exc:
                out["cvs"]["errors"].append({"id": row.get("id"), "reason": f"{type(exc).__name__}"})

    return out


@router.get("/capacity")
async def get_capacity(supabase=Depends(get_supabase)):
    """Capacity gauges across the free-tier ceilings we actually have.

    Returns a uniform shape per resource:
      { used: int, ceiling: int, pct: float, status: "ok"|"warn"|"crit" }

    Thresholds: warn >= 75%, crit >= 85%. The frontend can render these
    as traffic-light bars and alert when any goes crit. Sentry alerting
    can be wired to log a structured event when pct >= 85.

    Today this is a snapshot endpoint; the long-term play is a Prometheus
    /metrics endpoint (see task #45 in the queue) but JSON is enough for
    the admin dashboard. All counts come from cheap queries — no scans.
    """
    # Pull catalog + user counts via the existing admin_stats RPC so we
    # don't double-query. Falls back to direct counts when the RPC is
    # missing (shouldn't happen post-migration 010 but be defensive).
    rpc_res = supabase.rpc("admin_stats").execute()
    rpc_data = rpc_res.data
    if isinstance(rpc_data, list):
        rpc_data = rpc_data[0] if rpc_data else {}
    if not isinstance(rpc_data, dict):
        rpc_data = {}

    total_jobs = int(rpc_data.get("total_jobs") or 0)
    total_users = int(rpc_data.get("total_users") or 0)
    total_cvs = int(rpc_data.get("total_cvs") or 0)

    # Ceilings — chosen from the realistic-bottleneck table in our
    # capacity audit. Bump these as paid-tier upgrades happen.
    JOBS_CEILING = 50_000          # Supabase free disk + HNSW comfort
    USERS_CEILING = 50_000         # Supabase free MAU
    CVS_CEILING = 10_000           # Supabase free disk + storage bucket
    GEMINI_DAILY_TOKENS = 1_000_000  # Gemini 2.5 Flash free daily allowance

    gemini_tokens_today = 0
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        usage_res = (
            supabase.table("llm_usage_log")
            .select("prompt_tokens, completion_tokens")
            .gte("created_at", today_start)
            .execute()
        )
        for row in usage_res.data or []:
            gemini_tokens_today += int(row.get("prompt_tokens") or 0)
            gemini_tokens_today += int(row.get("completion_tokens") or 0)
    except Exception:
        logger.debug("capacity gemini token rollup failed", exc_info=True)

    def gauge(used: int, ceiling: int) -> dict:
        pct = (used / ceiling * 100.0) if ceiling > 0 else 0.0
        if pct >= 85.0:
            status = "crit"
        elif pct >= 75.0:
            status = "warn"
        else:
            status = "ok"
        return {
            "used": used,
            "ceiling": ceiling,
            "pct": round(pct, 2),
            "status": status,
        }

    return {
        "jobs": gauge(total_jobs, JOBS_CEILING),
        "users": gauge(total_users, USERS_CEILING),
        "cvs": gauge(total_cvs, CVS_CEILING),
        "gemini_tokens_today": gauge(gemini_tokens_today, GEMINI_DAILY_TOKENS),
        "notes": {
            "gemini": (
                "Token counts from llm_usage_log (all providers) for today UTC."
            ),
        },
    }


@router.get("/users", response_model=AdminUserList)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Match against phone, full_name, email"),
    tier: str | None = Query(None, description="Filter by subscription_tier"),
    supabase=Depends(get_supabase),
):
    query = supabase.table("users").select(
        "id, phone, full_name, location, subscription_tier, role, created_at, "
        "welcome_match_bonus, welcome_match_bonus_until",
        count="exact",
    ).order("created_at", desc=True)
    if tier:
        query = query.eq("subscription_tier", tier)
    if search:
        # Use `*` as the ilike wildcard (PostgREST-equivalent of `%`) so
        # the URL doesn't carry literal `%` characters into the upstream
        # Cloudflare Worker, which 1101's on malformed percent-encoding
        # — same vector as the /jobs filter fix.
        query = query.or_(
            f"phone.ilike.*{search}*,full_name.ilike.*{search}*,email.ilike.*{search}*"
        )
    offset = (page - 1) * per_page
    result = query.range(offset, offset + per_page - 1).execute()
    total = result.count or 0
    pages = math.ceil(total / per_page) if total > 0 else 1

    user_ids = [u["id"] for u in (result.data or [])]
    sub_map: dict[str, dict] = {}
    if user_ids:
        subs = (
            supabase.table("subscriptions")
            .select("user_id, tier")
            .in_("user_id", user_ids)
            .execute()
        )
        for s in subs.data or []:
            sub_map[s["user_id"]] = s

    rows = []
    for u in result.data or []:
        sub = sub_map.get(u["id"], {})
        tier = u.get("subscription_tier") or sub.get("tier") or "free"
        rows.append(
            AdminUserRow(
                id=u["id"],
                phone=u["phone"],
                full_name=u.get("full_name"),
                location=u.get("location"),
                subscription_tier=tier,
                role=u.get("role") or "user",
                matches_used=await get_credited_match_count(u["id"], supabase),
                matches_limit=await get_effective_match_limit(u["id"], supabase),
                welcome_match_bonus=u.get("welcome_match_bonus"),
                welcome_match_bonus_until=u.get("welcome_match_bonus_until"),
                created_at=u.get("created_at"),
            )
        )
    return AdminUserList(users=rows, total=total, page=page, per_page=per_page, pages=pages)


@router.patch("/users/{user_id}/welcome-bonus", response_model=AdminUserRow)
async def update_user_welcome_bonus(
    user_id: str,
    body: AdminWelcomeBonusUpdate,
    supabase=Depends(get_supabase),
):
    """Superadmin: extend or override a user's welcome match bonus window."""
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields to update")

    existing = (
        supabase.table("users")
        .select(
            "id, phone, full_name, location, subscription_tier, role, created_at, "
            "welcome_match_bonus, welcome_match_bonus_until"
        )
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    supabase.table("users").update(update_data).eq("id", user_id).execute()
    refreshed = (
        supabase.table("users")
        .select(
            "id, phone, full_name, location, subscription_tier, role, created_at, "
            "welcome_match_bonus, welcome_match_bonus_until"
        )
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    u = refreshed.data[0]
    tier = u.get("subscription_tier") or "free"
    return AdminUserRow(
        id=u["id"],
        phone=u["phone"],
        full_name=u.get("full_name"),
        location=u.get("location"),
        subscription_tier=tier,
        role=u.get("role") or "user",
        matches_used=await get_credited_match_count(user_id, supabase),
        matches_limit=await get_effective_match_limit(user_id, supabase),
        welcome_match_bonus=u.get("welcome_match_bonus"),
        welcome_match_bonus_until=u.get("welcome_match_bonus_until"),
        created_at=u.get("created_at"),
    )


@router.get("/jobs", response_model=AdminJobList)
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    expired: bool | None = Query(None, description="true = past closing_date and still active"),
    is_active: bool | None = Query(None),
    supabase=Depends(get_supabase),
):
    query = supabase.table("jobs").select(
        "id, title, company, location, source, quality_score, is_active, closing_date, posted_at",
        count="exact",
    ).order("posted_at", desc=True)
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if expired is True:
        # Postgres: closing_date < today AND is_active = true
        from datetime import date
        query = query.lt("closing_date", date.today().isoformat()).eq("is_active", True)
    elif expired is False:
        from datetime import date
        query = query.gte("closing_date", date.today().isoformat())

    offset = (page - 1) * per_page
    result = query.range(offset, offset + per_page - 1).execute()
    total = result.count or 0
    pages = math.ceil(total / per_page) if total > 0 else 1

    rows = [
        AdminJobRow(
            id=j["id"],
            title=j["title"],
            company=j.get("company"),
            location=j.get("location"),
            source=j["source"],
            quality_score=j.get("quality_score") or 0,
            is_active=j.get("is_active", True),
            closing_date=j.get("closing_date"),
            posted_at=j.get("posted_at"),
        )
        for j in (result.data or [])
    ]
    return AdminJobList(jobs=rows, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/jobs/review-queue", response_model=AdminJobReviewQueue)
async def review_queue(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    supabase=Depends(get_supabase),
):
    query = (
        supabase.table("jobs")
        .select("id, title, company, source, source_url, admin_review_reason, created_at", count="exact")
        .not_.is_("admin_review_reason", "null")
        .is_("admin_reviewed_at", "null")
        .order("created_at", desc=False)
    )
    offset = (page - 1) * per_page
    result = query.range(offset, offset + per_page - 1).execute()
    total = result.count or 0
    pages = math.ceil(total / per_page) if total > 0 else 1
    rows = [
        AdminJobReviewRow(
            id=j["id"],
            title=j["title"],
            company=j.get("company"),
            source=j["source"],
            source_url=j.get("source_url"),
            reasons=_split_review_reasons(j.get("admin_review_reason")),
            created_at=j.get("created_at"),
        )
        for j in (result.data or [])
    ]
    return AdminJobReviewQueue(jobs=rows, total=total, page=page, per_page=per_page, pages=pages)


@router.post("/jobs/{job_id}/approve")
async def approve_review_job(
    job_id: str,
    body: AdminJobReviewUpdate | None = None,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    patch = (body or AdminJobReviewUpdate()).model_dump(
        exclude_unset=True,
        exclude_none=True,
    )
    now = datetime.now(timezone.utc).isoformat()
    patch.update(
        {
            "is_active": True,
            "admin_reviewed_at": now,
            "admin_reviewed_by_user_id": current_user["id"],
            "updated_by_user_id": current_user["id"],
            "updated_at": now,
        }
    )
    result = supabase.table("jobs").update(patch).eq("id", job_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    _emit_analytics_event(
        supabase,
        "admin_job_review_approved",
        {"job_id": job_id, "admin_user_id": current_user["id"]},
        current_user["id"],
    )
    return {"id": job_id, "is_active": True, "admin_reviewed_at": now}


@router.post("/jobs/{job_id}/dismiss")
async def dismiss_review_job(
    job_id: str,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    now = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table("jobs")
        .update(
            {
                "is_active": False,
                "admin_reviewed_at": now,
                "admin_reviewed_by_user_id": current_user["id"],
                "updated_by_user_id": current_user["id"],
                "updated_at": now,
            }
        )
        .eq("id", job_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    _emit_analytics_event(
        supabase,
        "admin_job_review_dismissed",
        {"job_id": job_id, "admin_user_id": current_user["id"]},
        current_user["id"],
    )
    return {"id": job_id, "is_active": False, "admin_reviewed_at": now}


@router.post("/jobs/bulk-deactivate", response_model=BulkDeactivateResponse)
async def bulk_deactivate(body: BulkDeactivateRequest, supabase=Depends(get_supabase)):
    """Deactivate jobs by ID, or all expired jobs if expired_only=true.

    Uses the existing `deactivate_expired_jobs()` RPC for the expired_only path
    so the row count stays consistent with the WhatsApp/n8n cleanup workflow.
    """
    if body.expired_only:
        rpc_res = supabase.rpc("deactivate_expired_jobs").execute()
        count = rpc_res.data if isinstance(rpc_res.data, int) else (rpc_res.data or 0)
        return BulkDeactivateResponse(deactivated=int(count))

    if not body.job_ids:
        raise HTTPException(status_code=422, detail="Provide job_ids or set expired_only=true")

    res = (
        supabase.table("jobs")
        .update({"is_active": False})
        .in_("id", body.job_ids)
        .execute()
    )
    return BulkDeactivateResponse(deactivated=len(res.data or []))


@router.get("/payments", response_model=AdminPaymentList)
async def list_payments(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    supabase=Depends(get_supabase),
):
    query = supabase.table("payments").select(
        "id, user_id, amount, currency, payment_method, provider, status, created_at, completed_at",
        count="exact",
    ).order("created_at", desc=True)
    if status_filter:
        query = query.eq("status", status_filter)

    offset = (page - 1) * per_page
    result = query.range(offset, offset + per_page - 1).execute()
    total = result.count or 0
    pages = math.ceil(total / per_page) if total > 0 else 1

    user_ids = list({p["user_id"] for p in (result.data or [])})
    phone_map: dict[str, str] = {}
    if user_ids:
        users = supabase.table("users").select("id, phone").in_("id", user_ids).execute()
        phone_map = {u["id"]: u["phone"] for u in (users.data or [])}

    rows = [
        AdminPaymentRow(
            id=p["id"],
            user_id=p["user_id"],
            user_phone=phone_map.get(p["user_id"]),
            amount=p["amount"],
            currency=p.get("currency", "ZMW"),
            payment_method=p["payment_method"],
            provider=p.get("provider"),
            status=p["status"],
            created_at=p.get("created_at"),
            completed_at=p.get("completed_at"),
        )
        for p in (result.data or [])
    ]

    completed_total_res = (
        supabase.table("payments")
        .select("amount")
        .eq("status", "completed")
        .execute()
    )
    total_completed = sum((p.get("amount") or 0) for p in (completed_total_res.data or []))

    return AdminPaymentList(
        payments=rows,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        total_completed_ngwee=total_completed,
    )


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: dict,
    supabase=Depends(get_supabase),
):
    role = body.get("role")
    if role not in {"user", "admin", "superadmin"}:
        raise HTTPException(status_code=422, detail="role must be one of: user, admin, superadmin")
    res = supabase.table("users").update({"role": role}).eq("id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user_id, "role": role}


# ── Manual job entry (Wave 4) ───────────────────────────────────────
# POST/PATCH/DELETE wired through the same embedding, fingerprint and
# resolver pipeline the scraper uses, so manually-added jobs land in
# the matching engine the same way scraper-fed rows do. Audit column
# `updated_by_user_id` (migration 027) records the admin who last
# touched each row.

@router.post("/jobs", response_model=Job, status_code=status.HTTP_201_CREATED)
async def create_admin_job(
    body: AdminJobCreate,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    # Local imports keep admin.py's top free of jobs.py's regex constants.
    from app.api.v1.jobs import _fingerprint, _strip_html
    from app.schemas.jobs import _parse_salary_to_ngwee

    body.description = _strip_html(body.description)

    # Salary text → ngwee fallback (consistency with the ingest path).
    if (
        body.salary_min is None
        and body.salary_max is None
        and body.salary_text
    ):
        parsed_min, parsed_max = _parse_salary_to_ngwee(body.salary_text)
        if parsed_min is not None or parsed_max is not None:
            body.salary_min = parsed_min
            body.salary_max = parsed_max

    fp = _fingerprint(body.title, body.company, body.description)
    existing = (
        supabase.table("job_fingerprints")
        .select("job_id")
        .eq("fingerprint", fp)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate job listing",
        )

    skill_ids: list[str] = []
    if body.skills_required:
        skill_ids = await resolve_skill_ids(
            body.skills_required,
            supabase=supabase,
            source="admin_job_create",
            user_id=current_user["id"],
        )

    try:
        embedding = await generate_embedding(
            f"{body.title} {body.company or ''} {body.description}"
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    job_data = body.model_dump(exclude_none=True, mode="json")
    # Input-only fields not stored on jobs.
    job_data.pop("skills_required", None)
    job_data.pop("salary_text", None)
    job_data["embedding"] = embedding
    job_data["updated_by_user_id"] = current_user["id"]

    result = supabase.table("jobs").insert(job_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create job")
    job = result.data[0]

    supabase.table("job_fingerprints").insert(
        {"fingerprint": fp, "job_id": job["id"]}
    ).execute()
    for sid in skill_ids:
        supabase.table("job_skills").insert(
            {"job_id": job["id"], "skill_id": sid}
        ).execute()

    _emit_analytics_event(
        supabase,
        "admin_job_created",
        {
            "job_id": job["id"],
            "admin_user_id": current_user["id"],
            "source": "admin",
            "skill_count": len(skill_ids),
        },
        current_user["id"],
    )

    return Job(**job)


@router.patch("/jobs/{job_id}", response_model=Job)
async def update_admin_job(
    job_id: str,
    body: AdminJobUpdate,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    from app.api.v1.jobs import _fingerprint, _strip_html
    from app.schemas.jobs import _parse_salary_to_ngwee

    if not body.model_fields_set:
        raise HTTPException(status_code=422, detail="No fields to update")

    existing_res = (
        supabase.table("jobs").select("*").eq("id", job_id).limit(1).execute()
    )
    if not existing_res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = existing_res.data[0]

    # exclude_unset → only fields the client actually sent. This keeps
    # the field-absent vs explicitly-empty-list distinction the owner
    # addendum relies on (a sent `requirements: []` clears job_skills;
    # an omitted `requirements` leaves them alone). exclude_none would
    # collapse the two — never substitute.
    update_payload = body.model_dump(exclude_unset=True, mode="json")

    # Pull input-only fields out before the diff/write.
    skills_required_new = update_payload.pop("skills_required", None)
    salary_text = update_payload.pop("salary_text", None)

    if "description" in update_payload and update_payload["description"]:
        update_payload["description"] = _strip_html(update_payload["description"])

    if (
        salary_text
        and "salary_min" not in update_payload
        and "salary_max" not in update_payload
    ):
        parsed_min, parsed_max = _parse_salary_to_ngwee(salary_text)
        if parsed_min is not None:
            update_payload["salary_min"] = parsed_min
        if parsed_max is not None:
            update_payload["salary_max"] = parsed_max

    changed_fields = [
        k for k, v in update_payload.items() if existing.get(k) != v
    ]
    changed_set = set(changed_fields)

    embedding_regen = bool(changed_set & _EMBEDDING_TRIGGER_FIELDS)
    fingerprint_regen = bool(changed_set & _FINGERPRINT_TRIGGER_FIELDS)

    # Either `requirements` or `skills_required` (when EXPLICITLY sent —
    # absence vs `[]` matters) drives a job_skills rebuild. Owner
    # addendum #2 treats `requirements` as the skill list; the codebase
    # also accepts `skills_required` for compatibility. The more
    # specific field (`skills_required`) wins when both are sent.
    requirements_explicit = "requirements" in body.model_fields_set
    skills_required_explicit = "skills_required" in body.model_fields_set
    skills_changed = requirements_explicit or skills_required_explicit
    if skills_required_explicit:
        skill_names_new: list[str] = list(skills_required_new or [])
    elif requirements_explicit:
        skill_names_new = list(body.requirements or [])
    else:
        skill_names_new = []

    new_title = update_payload.get("title", existing["title"])
    new_company = update_payload.get("company", existing.get("company"))
    new_description = update_payload.get(
        "description", existing.get("description") or ""
    )

    if embedding_regen:
        try:
            update_payload["embedding"] = await generate_embedding(
                f"{new_title} {new_company or ''} {new_description}"
            )
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))

    if fingerprint_regen:
        new_fp = _fingerprint(new_title, new_company, new_description)
        # Collision check (warn-only per owner addendum #1). If the new
        # fingerprint matches another ACTIVE job's fingerprint, log +
        # emit an analytics event, but still apply the update. POST
        # remains a hard 409 on duplicates; PATCH lets admin reconcile
        # whatever situation they're knowingly creating.
        same_fp_rows = (
            supabase.table("job_fingerprints")
            .select("job_id")
            .eq("fingerprint", new_fp)
            .execute()
        )
        other_job_ids = [
            r["job_id"]
            for r in (same_fp_rows.data or [])
            if r.get("job_id") and r["job_id"] != job_id
        ]
        collided_with: Optional[str] = None
        for other_id in other_job_ids:
            other_row = (
                supabase.table("jobs")
                .select("is_active")
                .eq("id", other_id)
                .limit(1)
                .execute()
            )
            if other_row.data and other_row.data[0].get("is_active") is not False:
                collided_with = other_id
                break
        if collided_with:
            logger.warning(
                "admin_job PATCH fingerprint collision: job_id=%s now matches active job_id=%s",
                job_id, collided_with,
            )
            _emit_analytics_event(
                supabase,
                "admin_job_fingerprint_collision",
                {
                    "job_id": job_id,
                    "collided_with_job_id": collided_with,
                    "admin_user_id": current_user["id"],
                },
                current_user["id"],
            )
        supabase.table("job_fingerprints").update(
            {"fingerprint": new_fp}
        ).eq("job_id", job_id).execute()

    if skills_changed:
        resolved_ids = await resolve_skill_ids(
            skill_names_new,
            supabase=supabase,
            source="admin_job_create",
            user_id=current_user["id"],
        )
        # Replace job_skills wholesale. Diff-insert/delete would save
        # one round trip on no-op changes, but the wholesale path keeps
        # the code shape simple and the row counts are small (<50 per
        # job by validator). An empty `skill_names_new` (admin sent
        # `requirements: []` or `skills_required: []`) deletes all rows
        # and inserts none — clears job_skills, as the owner addendum
        # specifies.
        supabase.table("job_skills").delete().eq("job_id", job_id).execute()
        for sid in resolved_ids:
            supabase.table("job_skills").insert(
                {"job_id": job_id, "skill_id": sid}
            ).execute()

    update_payload["updated_by_user_id"] = current_user["id"]
    update_payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = (
        supabase.table("jobs").update(update_payload).eq("id", job_id).execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update job")
    job = result.data[0]

    _emit_analytics_event(
        supabase,
        "admin_job_edited",
        {
            "job_id": job_id,
            "admin_user_id": current_user["id"],
            "changed_fields": changed_fields,
            "embedding_regenerated": embedding_regen,
            "skills_changed": skills_changed,
        },
        current_user["id"],
    )

    return Job(**job)


@router.delete("/jobs/{job_id}", response_model=Job)
async def deactivate_admin_job(
    job_id: str,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
):
    """Soft-delete a job (is_active = false).

    Hard-delete is intentionally NOT supported here — matches, analytics,
    and audit history all reference the row. Returns the row in its
    deactivated state so the caller can refresh the UI without a
    follow-up GET.
    """
    existing_res = (
        supabase.table("jobs").select("*").eq("id", job_id).limit(1).execute()
    )
    if not existing_res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    if existing_res.data[0].get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is already inactive",
        )

    update_payload = {
        "is_active": False,
        "updated_by_user_id": current_user["id"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = (
        supabase.table("jobs").update(update_payload).eq("id", job_id).execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to deactivate job")
    job = result.data[0]

    _emit_analytics_event(
        supabase,
        "admin_job_deactivated",
        {"job_id": job_id, "admin_user_id": current_user["id"]},
        current_user["id"],
    )

    return Job(**job)


@router.get("/matches", response_model=AdminMatchList)
async def list_matches(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    min_score: float | None = Query(None, ge=0, le=100),
    supabase=Depends(get_supabase),
):
    query = supabase.table("matches").select(
        "id, user_id, job_id, score, status, created_at",
        count="exact",
    ).order("created_at", desc=True)
    if min_score is not None:
        query = query.gte("score", min_score)

    offset = (page - 1) * per_page
    result = query.range(offset, offset + per_page - 1).execute()
    total = result.count or 0
    pages = math.ceil(total / per_page) if total > 0 else 1

    user_ids = list({m["user_id"] for m in (result.data or [])})
    job_ids = list({m["job_id"] for m in (result.data or [])})

    phone_map: dict[str, str] = {}
    if user_ids:
        users = supabase.table("users").select("id, phone").in_("id", user_ids).execute()
        phone_map = {u["id"]: u["phone"] for u in (users.data or [])}

    job_map: dict[str, dict] = {}
    if job_ids:
        jobs = supabase.table("jobs").select("id, title, company").in_("id", job_ids).execute()
        job_map = {j["id"]: j for j in (jobs.data or [])}

    rows = [
        AdminMatchRow(
            id=m["id"],
            user_id=m["user_id"],
            user_phone=phone_map.get(m["user_id"]),
            job_id=m["job_id"],
            job_title=(job_map.get(m["job_id"], {}).get("title") or "—"),
            job_company=job_map.get(m["job_id"], {}).get("company"),
            score=float(m.get("score") or 0),
            status=m.get("status"),
            created_at=m.get("created_at"),
        )
        for m in (result.data or [])
    ]
    return AdminMatchList(matches=rows, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/subscriptions", response_model=AdminSubscriptionList)
async def list_subscriptions(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    tier: str | None = Query(None, pattern="^(free|starter|professional|super_standard)$"),
    status: str | None = Query(None, pattern="^(active|expired|cancelled|past_due)$"),
    supabase=Depends(get_supabase),
):
    # Tier breakdown over active subs — small enough to do in a single round trip.
    breakdown_res = (
        supabase.table("subscriptions")
        .select("tier")
        .eq("status", "active")
        .execute()
    )
    counts = {"free": 0, "starter": 0, "professional": 0, "super_standard": 0}
    for row in breakdown_res.data or []:
        t = row.get("tier")
        if t in counts:
            counts[t] += 1
    breakdown = AdminTierBreakdown(
        free=counts["free"],
        starter=counts["starter"],
        professional=counts["professional"],
        super_standard=counts["super_standard"],
        total_active=sum(counts.values()),
    )

    query = supabase.table("subscriptions").select(
        "user_id, tier, status, current_period_end, created_at",
        count="exact",
    ).order("created_at", desc=True)
    if tier:
        query = query.eq("tier", tier)
    if status:
        query = query.eq("status", status)

    offset = (page - 1) * per_page
    result = query.range(offset, offset + per_page - 1).execute()
    total = result.count or 0
    pages = math.ceil(total / per_page) if total > 0 else 1

    user_ids = list({s["user_id"] for s in (result.data or [])})
    user_map: dict[str, dict] = {}
    if user_ids:
        users = (
            supabase.table("users")
            .select("id, phone, full_name")
            .in_("id", user_ids)
            .execute()
        )
        user_map = {u["id"]: u for u in (users.data or [])}

    tier_limits = await get_tier_limits(supabase)
    rows = []
    for s in (result.data or []):
        tier = s.get("tier", "free")
        rows.append(
            AdminSubscriptionRow(
                user_id=s["user_id"],
                user_phone=user_map.get(s["user_id"], {}).get("phone"),
                full_name=user_map.get(s["user_id"], {}).get("full_name"),
                tier=tier,
                status=s.get("status", "active"),
                matches_used=await get_credited_match_count(s["user_id"], supabase),
                matches_limit=await get_effective_match_limit(s["user_id"], supabase),
                current_period_end=s.get("current_period_end"),
                created_at=s.get("created_at"),
            )
        )

    return AdminSubscriptionList(
        breakdown=breakdown,
        subscriptions=rows,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.patch("/subscriptions/{user_id}", response_model=AdminSubscriptionRow)
async def update_subscription(
    user_id: str,
    body: AdminSubscriptionUpdate,
    supabase=Depends(get_supabase),
):
    """Set a user's tier. Quota limit is derived from tier_config by tier."""
    tier_limits = await get_tier_limits(supabase)
    new_limit = tier_limits[body.tier]
    res = (
        supabase.table("subscriptions")
        .update({"tier": body.tier, "status": "active"})
        .eq("user_id", user_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Mirror the tier on users.subscription_tier so the existing UI stays in sync.
    supabase.table("users").update({"subscription_tier": body.tier}).eq("id", user_id).execute()

    user = (
        supabase.table("users")
        .select("phone, full_name")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    user_row = (user.data or [{}])[0]
    sub = res.data[0]
    tier = sub.get("tier", body.tier)
    return AdminSubscriptionRow(
        user_id=user_id,
        user_phone=user_row.get("phone"),
        full_name=user_row.get("full_name"),
        tier=tier,
        status=sub.get("status", "active"),
        matches_used=await get_credited_match_count(user_id, supabase),
        matches_limit=await get_effective_match_limit(user_id, supabase),
        current_period_end=sub.get("current_period_end"),
        created_at=sub.get("created_at"),
    )


# ── Skill canonicalization (Phase 2 Initiative #1) ──────────────────
# Ad-hoc admin endpoint to run the resolver against a list of raw skill
# names — useful for testing the resolver against suspected duplicates
# before triggering the full job_skills backfill, or for previewing what
# canonical id a brand-new name would map to.
#
# This is NOT the path /cv/upload uses (that calls resolve_skill_ids
# directly). It's a thin echo of the resolver for admin tooling.

class _CanonicalizeRequest(BaseModel):
    names: list[str] = Field(..., min_length=1, max_length=200)


class _CanonicalizeResult(BaseModel):
    input: str
    skill_id: Optional[str]


class _CanonicalizeResponse(BaseModel):
    resolved: list[_CanonicalizeResult]


@router.post("/skills/canonicalize", response_model=_CanonicalizeResponse)
async def canonicalize_skills(
    body: _CanonicalizeRequest,
    supabase=Depends(get_supabase),
):
    """Resolve a batch of skill names through the production resolver.

    Returns one row per input — the canonical `skills.id` it mapped to
    (or null if the input normalized to an empty string). When the
    resolver hits Pass 4 (auto-insert), a new row IS created in
    `skills` and the analytics event fires — so this endpoint has
    side effects. Use against duplicates you want to merge, not against
    arbitrary user-typed input.

    Single batch reuses one in-memory cache, so passing the same name
    twice is one resolve call.
    """
    cache: dict[str, str] = {}
    out: list[_CanonicalizeResult] = []
    for name in body.names:
        sid = await resolve_skill_id(
            name,
            supabase=supabase,
            cache=cache,
            source="admin_canonicalize",
            user_id=None,
        )
        out.append(_CanonicalizeResult(input=name, skill_id=sid))
    return _CanonicalizeResponse(resolved=out)
