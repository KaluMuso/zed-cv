"""Employer portal — B2B candidate search, consent-gated contact, billing."""
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.deps import get_current_user_id, get_supabase
from app.core.employer_tier_gating import (
    assert_contact_quota,
    contact_limit_for_tier,
    increment_contact_usage,
    load_active_employer_subscription,
    load_employer_membership,
    price_ngwee_for_tier,
    require_employer_subscription,
)
from app.core.rate_limit import limiter
from app.schemas.employer import (
    CandidateSearchResponse,
    ContactRequestBody,
    ContactRequestRow,
    EmployerCheckoutBody,
    EmployerCheckoutResponse,
    ContactStatusSummary,
    EmployerContactsResponse,
    EmployerInviteBody,
    EmployerInviteResponse,
    EmployerMeResponse,
    EmployerRegisterBody,
    EmployerSeat,
    EmployerSubscriptionResponse,
    EmployerSummary,
    EmployerUserRole,
    EmployerVerifyPaymentBody,
    EmployerVerifyPaymentResponse,
)
from app.services.employer_auth import invite_team_member, register_employer
from app.services.employer_billing import verify_employer_lenco_payment
from app.services.employer_contact import create_contact_request, enrich_contact_row
from app.services.employer_search import search_candidates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/employers", tags=["Employers"])


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


def _first_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def _summarize_contact_statuses(contacts: list[ContactRequestRow]) -> ContactStatusSummary:
    counts = {
        "pending": 0,
        "consented": 0,
        "declined": 0,
        "expired": 0,
        "draft": 0,
        "unavailable": 0,
    }
    for row in contacts:
        key = row.status if row.status in counts else "unavailable"
        counts[key] += 1
    return ContactStatusSummary(
        pending=counts["pending"],
        consented=counts["consented"],
        declined=counts["declined"],
        expired=counts["expired"],
        draft=counts["draft"],
        unavailable=counts["unavailable"],
        total=len(contacts),
    )


async def _employer_context(user_id: str, supabase) -> tuple[str, dict, dict]:
    employer_id, employer, seat = await load_employer_membership(user_id, supabase)
    return employer_id, employer, seat


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(
    request: Request,
    body: EmployerRegisterBody = Body(...),
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Create employer company and link caller as owner."""
    del request
    employer = await register_employer(supabase, user_id=user_id, body=body)
    return {"employer": EmployerSummary(**employer)}


@router.get("/me", response_model=EmployerMeResponse)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    employer_id, employer, seat = await _employer_context(user_id, supabase)
    seats_res = (
        supabase.table("employer_users")
        .select("id, user_id, role, invited_at, accepted_at, invite_email")
        .eq("employer_id", employer_id)
        .execute()
    )
    seats = [
        EmployerSeat(
            id=r["id"],
            user_id=r["user_id"],
            role=EmployerUserRole(r["role"]),
            invited_at=r.get("invited_at"),
            accepted_at=r.get("accepted_at"),
            invite_email=r.get("invite_email"),
        )
        for r in _first_rows(seats_res.data)
    ]
    full = (
        supabase.table("employers")
        .select("*")
        .eq("id", employer_id)
        .limit(1)
        .execute()
    )
    emp = _first_row(full.data) or employer
    return EmployerMeResponse(
        employer=EmployerSummary(**emp),
        seats=seats,
        my_role=EmployerUserRole(seat["role"]),
    )


@router.post("/me/invite", response_model=EmployerInviteResponse)
@limiter.limit("20/hour")
async def invite_recruiter(
    request: Request,
    body: EmployerInviteBody = Body(...),
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    del request
    employer_id, _, _ = await _employer_context(user_id, supabase)
    seat = await invite_team_member(
        supabase,
        employer_id=employer_id,
        inviter_user_id=user_id,
        email=str(body.email),
        role=body.role,
    )
    return EmployerInviteResponse(
        seat_id=seat["id"],
        email=str(body.email),
        role=body.role,
        message="Invitation sent",
    )


@router.get("/candidates/search", response_model=CandidateSearchResponse)
@limiter.limit("60/minute")
async def search(
    request: Request,
    skills: str | None = Query(None, description="Comma-separated skills"),
    location: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    del request
    employer_id, _, seat = await _employer_context(user_id, supabase)
    if seat.get("role") == "viewer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewers cannot search")
    await require_employer_subscription(employer_id, supabase)
    results, total = await search_candidates(
        supabase, skills=skills, location=location, limit=limit
    )
    return CandidateSearchResponse(results=results, total=total)


@router.post("/candidates/{candidate_id}/contact", response_model=ContactRequestRow)
@limiter.limit("30/hour")
async def request_contact(
    request: Request,
    candidate_id: str,
    body: ContactRequestBody = Body(...),
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    del request
    employer_id, employer, seat = await _employer_context(user_id, supabase)
    if seat.get("role") == "viewer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewers cannot request contact")
    sub = await require_employer_subscription(employer_id, supabase)
    await assert_contact_quota(employer_id, sub, supabase)

    req = await create_contact_request(
        supabase,
        employer_id=employer_id,
        employer_name=employer.get("company_name", "An employer"),
        initiator_user_id=user_id,
        candidate_user_id=candidate_id,
        message_text=body.message_text,
        channel=body.channel,
    )
    await increment_contact_usage(employer_id, supabase)

    return ContactRequestRow(**enrich_contact_row(req, None))


@router.get("/me/contacts", response_model=EmployerContactsResponse)
async def list_contacts(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    employer_id, _, _ = await _employer_context(user_id, supabase)
    res = (
        supabase.table("candidate_contact_requests")
        .select("*")
        .eq("employer_id", employer_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    rows = _first_rows(res.data)
    contacts: list[ContactRequestRow] = []
    for row in rows:
        cand = None
        if row.get("candidate_consented") is True:
            cres = (
                supabase.table("users")
                .select("phone, email, full_name")
                .eq("id", row["candidate_user_id"])
                .limit(1)
                .execute()
            )
            cand = _first_row(cres.data)
        contacts.append(ContactRequestRow(**enrich_contact_row(row, cand)))
    return EmployerContactsResponse(
        contacts=contacts,
        total=len(contacts),
        summary=_summarize_contact_statuses(contacts),
    )


@router.get("/me/subscription", response_model=EmployerSubscriptionResponse)
async def get_subscription(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    employer_id, _, _ = await _employer_context(user_id, supabase)
    sub = await load_active_employer_subscription(employer_id, supabase)
    if not sub:
        return EmployerSubscriptionResponse(
            tier=None,
            status="inactive",
            active=False,
            contacts_used=0,
            contacts_limit=0,
            price_ngwee=0,
        )
    tier = str(sub.get("tier") or "lite")
    return EmployerSubscriptionResponse(
        tier=tier,
        status=sub.get("status", "active"),
        active=True,
        current_period_end=sub.get("current_period_end"),
        contacts_used=int(sub.get("contacts_used_this_period") or 0),
        contacts_limit=contact_limit_for_tier(tier),
        price_ngwee=price_ngwee_for_tier(tier),
    )


@router.post("/me/subscription/checkout", response_model=EmployerCheckoutResponse)
@limiter.limit("10/minute")
async def checkout(
    request: Request,
    body: EmployerCheckoutBody = Body(...),
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    del request
    employer_id, _, seat = await _employer_context(user_id, supabase)
    if seat.get("role") not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can manage billing",
        )
    settings = get_settings()
    if not settings.lenco_public_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments are not configured",
        )
    reference = f"zedapply-emp-{employer_id}-{int(datetime.now(timezone.utc).timestamp())}"
    amount = price_ngwee_for_tier(body.tier.value)
    return EmployerCheckoutResponse(
        reference=reference,
        amount_ngwee=amount,
        tier=body.tier,
        public_key=settings.lenco_public_key,
    )


@router.post(
    "/me/subscription/verify-payment",
    response_model=EmployerVerifyPaymentResponse,
    responses={202: {"model": EmployerVerifyPaymentResponse}},
)
@limiter.limit("10/minute")
async def verify_payment(
    request: Request,
    body: EmployerVerifyPaymentBody = Body(...),
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    del request
    employer_id, _, seat = await _employer_context(user_id, supabase)
    if seat.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Billing access denied")

    status_code, payload = await verify_employer_lenco_payment(
        supabase,
        employer_id=employer_id,
        user_id=user_id,
        reference=body.reference.strip(),
        tier=body.tier.value,
    )
    if status_code == 422:
        raise HTTPException(status_code=422, detail=payload.get("detail"))
    if status_code == 402:
        raise HTTPException(status_code=402, detail=payload.get("detail"))
    if status_code == 403:
        raise HTTPException(status_code=403, detail=payload.get("detail"))
    if status_code == 502:
        raise HTTPException(status_code=502, detail=payload.get("detail"))
    response = EmployerVerifyPaymentResponse(**payload)
    if status_code == 202:
        return JSONResponse(status_code=202, content=response.model_dump())
    return response
