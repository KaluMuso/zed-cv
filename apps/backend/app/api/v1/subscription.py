"""Subscription and payment routes."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.deps import get_supabase, get_current_user_id
from app.core.rate_limit import limiter
from app.dependencies.rate_limit import apply_rate_limits, per_user_key
from app.schemas.subscription import (
    Subscription,
    PaymentInitiate,
    PaymentInitiateResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
)
from app.core.tier_gating import get_effective_match_limit, welcome_bonus_active
from app.services.matching import get_credited_match_count
from app.services.pricing import load_user_promotion_until

router = APIRouter(prefix="/subscription", tags=["Subscription"])


@router.get("", response_model=Subscription)
async def get_subscription(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    result = (
        supabase.table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No subscription found")

    sub = result.data
    matches_used = await get_credited_match_count(user_id, supabase)
    tier = sub["tier"]
    matches_limit = await get_effective_match_limit(user_id, supabase)

    user_row = (
        supabase.table("users")
        .select("welcome_match_bonus, welcome_match_bonus_until")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    user_data = (user_row.data or [{}])[0]
    welcome_until = user_data.get("welcome_match_bonus_until")
    promo_until = await load_user_promotion_until(supabase, user_id)

    return Subscription(
        tier=tier,
        matches_used=matches_used,
        matches_limit=matches_limit,
        active=sub["status"] == "active",
        expires_at=sub.get("current_period_end"),
        welcome_match_bonus=user_data.get("welcome_match_bonus"),
        welcome_match_bonus_until=welcome_until,
        promo_until=promo_until,
        welcome_bonus_active=welcome_bonus_active(welcome_until)
        if tier == "free"
        else False,
    )


@router.post("/pay", response_model=PaymentInitiateResponse)
@limiter.limit("3/minute")
async def initiate_payment(
    request: Request,
    body: PaymentInitiate,
    user_id: str = Depends(get_current_user_id),
):
    """Deprecated — Lenco widget + POST /verify-payment replaced server-side initiation."""
    del request, body, user_id
    raise HTTPException(
        status_code=410,
        detail=(
            "Server-side payment initiation is removed. Use the Lenco widget on "
            "/pricing, then POST /subscription/verify-payment with your reference."
        ),
    )


@router.post(
    "/verify-payment",
    response_model=PaymentVerifyResponse,
    responses={
        202: {"model": PaymentVerifyResponse},
        402: {"description": "Payment failed at Lenco"},
        502: {"description": "Lenco upstream error"},
    },
)
@apply_rate_limits(("30/hour", per_user_key))
async def verify_payment(
    request: Request,
    body: PaymentVerifyRequest,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Confirm a Lenco widget payment via collections/status and activate tier."""
    from app.services.lenco_payment_verify import verify_lenco_widget_payment

    tier_value = body.tier.value if hasattr(body.tier, "value") else body.tier
    status_code, payload = await verify_lenco_widget_payment(
        supabase,
        user_id=user_id,
        reference=body.reference.strip(),
        tier=tier_value,
    )

    if status_code == 422:
        raise HTTPException(status_code=422, detail=payload.get("detail", "Invalid tier"))
    if status_code == 402:
        raise HTTPException(status_code=402, detail=payload.get("detail", "Payment failed"))
    if status_code == 502:
        raise HTTPException(status_code=502, detail=payload.get("detail", "Upstream error"))
    if status_code >= 500:
        raise HTTPException(status_code=status_code, detail=payload.get("detail", "Error"))

    response = PaymentVerifyResponse(**payload)
    if status_code == 202:
        return JSONResponse(
            status_code=202,
            content=response.model_dump(),
        )
    return response
