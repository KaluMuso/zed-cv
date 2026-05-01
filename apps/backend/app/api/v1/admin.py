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

# Default match quotas per tier — kept here so tier changes update the cap
# in lockstep without a separate config indirection.
TIER_MATCH_LIMITS = {"free": 5, "starter": 25, "professional": 125}

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/stats", response_model=AdminStats)
async def get_stats(supabase=Depends(get_supabase)):
    """Aggregate counters for the admin dashboard."""
    rpc_res = supabase.rpc("admin_stats").execute()
    data = rpc_res.data or {}
    if isinstance(data, list):
        # supabase-py returns list of one row for SETOF; handle either shape
        data = data[0] if data else {}
    return AdminStats(**(data or {}))


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
    tier: str | None = Query(None, pattern="^(free|starter|professional)$"),
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
    counts = {"free": 0, "starter": 0, "professional": 0}
    for row in breakdown_res.data or []:
        t = row.get("tier")
        if t in counts:
            counts[t] += 1
    breakdown = AdminTierBreakdown(
        free=counts["free"],
        starter=counts["starter"],
        professional=counts["professional"],
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
    new_limit = TIER_MATCH_LIMITS.get(body.tier, 5)
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
