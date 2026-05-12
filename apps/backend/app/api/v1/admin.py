"""Admin routes — superadmin only.

All endpoints require role = 'superadmin'. The frontend's AdminGuard
mirrors this check, but the API enforces it as the source of truth.
"""
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.deps import get_supabase, require_admin
from app.schemas.admin import (
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
)
from app.schemas.subscription import TIER_LIMITS
from app.schemas.db_enums import QueueStatus

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
    return AdminStats(**data)


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

    # Gemini-tokens-used today: tracked elsewhere if we wire a counter.
    # For now we expose 0 with a note so the frontend can show the gauge
    # at zero rather than missing it. Task #45 follow-up: wire an actual
    # token-spend counter in ai_cache or a sidecar table.
    gemini_tokens_today = 0

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
                "Token spend tracker not yet wired — gauge is a placeholder. "
                "Follow-up in task #45."
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
        "id, phone, full_name, location, subscription_tier, role, created_at",
        count="exact",
    ).order("created_at", desc=True)
    if tier:
        query = query.eq("subscription_tier", tier)
    if search:
        query = query.or_(
            f"phone.ilike.%{search}%,full_name.ilike.%{search}%,email.ilike.%{search}%"
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
            .select("user_id, matches_used, matches_limit")
            .in_("user_id", user_ids)
            .execute()
        )
        for s in subs.data or []:
            sub_map[s["user_id"]] = s

    rows = []
    for u in result.data or []:
        sub = sub_map.get(u["id"], {})
        rows.append(
            AdminUserRow(
                id=u["id"],
                phone=u["phone"],
                full_name=u.get("full_name"),
                location=u.get("location"),
                subscription_tier=u.get("subscription_tier") or "free",
                role=u.get("role") or "user",
                matches_used=sub.get("matches_used", 0),
                matches_limit=sub.get("matches_limit", 0),
                created_at=u.get("created_at"),
            )
        )
    return AdminUserList(users=rows, total=total, page=page, per_page=per_page, pages=pages)


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


@router.post("/jobs")
async def create_admin_job(body: dict, supabase=Depends(get_supabase)):
    required = {"title", "description", "source"}
    missing = [k for k in required if not body.get(k)]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required fields: {', '.join(missing)}")
    res = supabase.table("jobs").insert(body).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create job")
    return res.data[0]


@router.patch("/jobs/{job_id}")
async def update_admin_job(job_id: str, body: dict, supabase=Depends(get_supabase)):
    if not body:
        raise HTTPException(status_code=422, detail="No fields to update")
    res = supabase.table("jobs").update(body).eq("id", job_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return res.data[0]


@router.delete("/jobs/{job_id}")
async def delete_admin_job(job_id: str, supabase=Depends(get_supabase)):
    res = supabase.table("jobs").delete().eq("id", job_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"deleted": True, "id": job_id}


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
        "user_id, tier, status, matches_used, matches_limit, current_period_end, created_at",
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

    rows = [
        AdminSubscriptionRow(
            user_id=s["user_id"],
            user_phone=user_map.get(s["user_id"], {}).get("phone"),
            full_name=user_map.get(s["user_id"], {}).get("full_name"),
            tier=s.get("tier", "free"),
            status=s.get("status", "active"),
            matches_used=s.get("matches_used", 0),
            matches_limit=s.get("matches_limit", 0),
            current_period_end=s.get("current_period_end"),
            created_at=s.get("created_at"),
        )
        for s in (result.data or [])
    ]

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
    """Set a user's tier. Resets matches_limit to the tier default; matches_used preserved."""
    new_limit = TIER_LIMITS[body.tier]
    res = (
        supabase.table("subscriptions")
        .update({"tier": body.tier, "matches_limit": new_limit, "status": "active"})
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
    return AdminSubscriptionRow(
        user_id=user_id,
        user_phone=user_row.get("phone"),
        full_name=user_row.get("full_name"),
        tier=sub.get("tier", body.tier),
        status=sub.get("status", "active"),
        matches_used=sub.get("matches_used", 0),
        matches_limit=sub.get("matches_limit", new_limit),
        current_period_end=sub.get("current_period_end"),
        created_at=sub.get("created_at"),
    )
