"""Subscription and payment routes."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.deps import get_supabase, get_current_user_id
from app.core.rate_limit import limiter
from app.schemas.subscription import (
    Subscription,
    PaymentInitiate,
    PaymentInitiateResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    PaymentHistoryList,
    PaymentHistoryRow,
    InvoiceDetail,
    SubscriptionCancelResponse,
)
from app.core.tier_gating import get_effective_match_limit, welcome_bonus_active
from app.schemas.tier_config import UNLIMITED_MATCHES
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
        matches_unlimited=matches_limit >= UNLIMITED_MATCHES,
        active=sub["status"] == "active",
        expires_at=sub.get("current_period_end"),
        welcome_match_bonus=user_data.get("welcome_match_bonus"),
        welcome_match_bonus_until=welcome_until,
        promo_until=promo_until,
        welcome_bonus_active=welcome_bonus_active(welcome_until)
        if tier == "free"
        else False,
    )


@router.get("/payments", response_model=PaymentHistoryList)
async def list_my_payments(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
    limit: int = Query(50, ge=1, le=100),
):
    """Completed and pending payments for the authenticated user (newest first)."""
    capped = max(1, min(limit, 100))
    result = (
        supabase.table("payments")
        .select(
            "id, amount, currency, payment_method, provider, status, created_at, completed_at",
            count="exact",
        )
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(capped)
        .execute()
    )
    rows = [
        PaymentHistoryRow(
            id=p["id"],
            amount=int(p["amount"]),
            currency=p.get("currency") or "ZMW",
            payment_method=p["payment_method"],
            provider=p.get("provider"),
            status=p["status"],
            created_at=p.get("created_at"),
            completed_at=p.get("completed_at"),
        )
        for p in (result.data or [])
    ]
    return PaymentHistoryList(payments=rows, total=result.count or len(rows))


@router.get("/payments/{payment_id}/invoice", response_model=InvoiceDetail)
async def get_payment_invoice(
    payment_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Invoice metadata for a completed payment belonging to the current user."""
    from app.services.invoice import load_payment_invoice

    invoice = await load_payment_invoice(
        supabase, user_id=user_id, payment_id=payment_id
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Payment not found")
    if invoice["status"] not in {"completed", "refunded"}:
        raise HTTPException(status_code=404, detail="Invoice not available for this payment")
    return InvoiceDetail(**invoice)


@router.get("/payments/{payment_id}/invoice/download")
async def download_payment_invoice(
    payment_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Downloadable HTML invoice (print to PDF from browser)."""
    from app.services.invoice import load_payment_invoice, render_invoice_html

    invoice = await load_payment_invoice(
        supabase, user_id=user_id, payment_id=payment_id
    )
    if not invoice or invoice["status"] not in {"completed", "refunded"}:
        raise HTTPException(status_code=404, detail="Invoice not found")
    html = render_invoice_html(invoice)
    filename = f"{invoice['invoice_number']}.html"
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/payments/{payment_id}/invoice/email")
async def email_payment_invoice(
    payment_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Email invoice/receipt copy to the user's registered email."""
    from app.services.invoice import load_payment_invoice
    from app.services.email import send_invoice_email

    invoice = await load_payment_invoice(
        supabase, user_id=user_id, payment_id=payment_id
    )
    if not invoice or invoice["status"] not in {"completed", "refunded"}:
        raise HTTPException(status_code=404, detail="Invoice not found")
    sent = await send_invoice_email(invoice, supabase)
    if not sent:
        raise HTTPException(
            status_code=503,
            detail="Could not send invoice email — check email notifications are enabled",
        )
    return {"status": "sent", "invoice_number": invoice["invoice_number"]}


@router.post("/cancel", response_model=SubscriptionCancelResponse)
async def cancel_subscription(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Cancel paid plan at end of current billing period (no immediate downgrade)."""
    from datetime import datetime, timezone

    sub_res = (
        supabase.table("subscriptions")
        .select("id, tier, status, current_period_end, cancelled_at")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not sub_res.data:
        raise HTTPException(status_code=404, detail="No subscription found")

    raw = sub_res.data
    sub = raw[0] if isinstance(raw, list) else raw
    if not isinstance(sub, dict):
        raise HTTPException(status_code=404, detail="No subscription found")
    tier = sub.get("tier") or "free"
    if tier == "free":
        raise HTTPException(status_code=400, detail="Free plan cannot be cancelled")

    now = datetime.now(timezone.utc)
    if sub.get("cancelled_at"):
        return SubscriptionCancelResponse(
            status="already_cancelled",
            message="Your plan is already set to cancel at period end.",
            tier=tier,
            active_until=sub.get("current_period_end"),
            cancelled_at=sub["cancelled_at"],
        )

    supabase.table("subscriptions").update(
        {"cancelled_at": now.isoformat(), "updated_at": now.isoformat()}
    ).eq("id", sub["id"]).execute()

    return SubscriptionCancelResponse(
        status="cancelled",
        message=(
            "Your subscription will remain active until the end of your billing period, "
            "then revert to the Free plan. You can upgrade again anytime on the pricing page."
        ),
        tier=tier,
        active_until=sub.get("current_period_end"),
        cancelled_at=now,
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
@limiter.limit("10/minute")
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
        billing_period_days=body.billing_period_days,
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
