"""Subscription and payment routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.deps import get_supabase, get_current_user_id
from app.core.rate_limit import limiter
from app.schemas.subscription import (
    Subscription,
    PaymentInitiate,
    PaymentInitiateResponse,
    TIER_PRICES,
    TIER_LIMITS,
)
from app.services.matching import get_credited_match_count
from app.services.payment_methods import normalize_payment_method

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
    matches_limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    return Subscription(
        tier=tier,
        matches_used=matches_used,
        matches_limit=matches_limit,
        active=sub["status"] == "active",
        expires_at=sub.get("current_period_end"),
    )


@router.post("/pay", response_model=PaymentInitiateResponse)
@limiter.limit("3/minute")
async def initiate_payment(
    request: Request,
    body: PaymentInitiate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    tier_value = body.tier.value if hasattr(body.tier, "value") else body.tier
    if tier_value not in TIER_PRICES or tier_value == "free":
        raise HTTPException(
            status_code=422,
            detail="Invalid tier. Choose starter, professional, or super_standard.",
        )

    amount_ngwee = TIER_PRICES[tier_value]

    # Get or verify subscription exists
    sub_result = (
        supabase.table("subscriptions")
        .select("id")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not sub_result.data:
        raise HTTPException(status_code=404, detail="No subscription record found")

    subscription_id = sub_result.data["id"]

    # Branch on payment method. Lenco goes via app/services/lenco.py and
    # the /webhooks/lenco signed-callback handler. DPO Pay handles mtn /
    # airtel / card via the existing token-create + browser-redirect flow.
    method_label = normalize_payment_method(body.payment_method, body.phone)
    is_lenco = method_label.startswith("lenco_")
    provider = "lenco" if is_lenco else "dpo_pay"

    # Create payment record (status=pending) BEFORE calling the provider.
    # We use the row id as the company_ref so the webhook can look it up.
    payment_result = supabase.table("payments").insert({
        "user_id": user_id,
        "subscription_id": subscription_id,
        "amount": amount_ngwee,
        "currency": "ZMW",
        "payment_method": method_label,
        "provider": provider,
        "status": "pending",
    }).execute()
    if not payment_result.data:
        raise HTTPException(status_code=500, detail="Failed to create payment record")

    payment_id = payment_result.data[0]["id"]
    amount_zmw = amount_ngwee / 100
    tier_name = {
        "starter": "Starter",
        "professional": "Professional",
        "super_standard": "Super Standard",
    }.get(tier_value, "Plan")

    if is_lenco:
        from app.services.lenco import create_lenco_payment
        try:
            lenco_result = await create_lenco_payment(
                amount_zmw=amount_zmw,
                phone=body.phone,
                description=f"Zed CV {tier_name} Plan - 1 Month",
                payment_ref=payment_id,
            )
            supabase.table("payments").update({
                "provider_ref": lenco_result["transaction_id"],
            }).eq("id", payment_id).execute()

            logging.info(
                "Lenco payment initiated: user=%s tier=%s amount=K%s tx=%s",
                user_id, tier_value, amount_zmw, lenco_result["transaction_id"],
            )
            return PaymentInitiateResponse(
                message=(
                    f"Payment of K{int(amount_zmw)} initiated via Lenco. "
                    "Check your phone for the mobile money prompt."
                ),
                transaction_id=payment_id,
            )
        except ValueError as e:
            logging.warning("Lenco payment failed: %s", e)
            return PaymentInitiateResponse(
                message=f"Payment of K{int(amount_zmw)} recorded. {str(e)}",
                transaction_id=payment_id,
            )

    from app.services.dpo_pay import create_payment_token
    try:
        dpo_result = await create_payment_token(
            amount_zmw=amount_zmw,
            phone=body.phone,
            description=f"Zed CV {tier_name} Plan - 1 Month",
            payment_ref=payment_id,
        )
        supabase.table("payments").update({
            "provider_ref": dpo_result["token"],
        }).eq("id", payment_id).execute()

        logging.info(
            f"Payment token created: user={user_id}, tier={tier_value}, "
            f"amount=K{amount_zmw}, token={dpo_result['token']}"
        )

        return PaymentInitiateResponse(
            message=f"Payment of K{int(amount_zmw)} initiated. "
                    f"Complete payment at the redirect URL or check your phone for a prompt.",
            transaction_id=payment_id,
        )

    except ValueError as e:
        logging.warning(f"DPO Pay token creation failed: {e}")
        return PaymentInitiateResponse(
            message=f"Payment of K{int(amount_zmw)} recorded. {str(e)}",
            transaction_id=payment_id,
        )
