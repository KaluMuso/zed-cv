"""Verify Lenco widget payments and activate subscriptions."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import Client

from app.services.lenco import (
    LencoApiError,
    amount_to_ngwee,
    fetch_collection_status,
    map_lenco_payment_method,
    normalize_collection_status,
)
from app.services.pricing import (
    effective_checkout_price_ngwee,
    load_user_promotion_until,
)
from app.services.subscription_billing import activate_subscription_after_payment
from app.services.tier_config import get_tier_prices

logger = logging.getLogger(__name__)


def _payment_webhook_data(collection: dict[str, Any], *, tier: str) -> dict[str, Any]:
    """Persist Lenco payload plus checkout tier for webhook tier resolution."""
    data = dict(collection) if isinstance(collection, dict) else {}
    data["intended_tier"] = tier
    return data


def _find_payment_by_reference(
    supabase: Client, user_id: str, reference: str
) -> dict[str, Any] | None:
    result = (
        supabase.table("payments")
        .select("*, subscriptions(id, user_id, tier, current_period_end)")
        .eq("user_id", user_id)
        .eq("provider_ref", reference)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def _subscription_row_for_user(supabase: Client, user_id: str) -> dict[str, Any]:
    result = (
        supabase.table("subscriptions")
        .select("id, user_id, tier, current_period_end")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise ValueError("No subscription record found")
    return result.data


async def verify_lenco_widget_payment(
    supabase: Client,
    *,
    user_id: str,
    reference: str,
    tier: str,
) -> tuple[int, dict[str, Any]]:
    """Verify widget reference with Lenco and return (http_status, body)."""
    tier_prices = await get_tier_prices(supabase)
    if tier not in tier_prices or tier == "free":
        return 422, {"detail": "Invalid tier. Choose starter, professional, or super_standard."}

    now = datetime.now(timezone.utc)
    list_price_ngwee = tier_prices[tier]
    promo_until = await load_user_promotion_until(supabase, user_id)
    expected_ngwee = effective_checkout_price_ngwee(
        list_price_ngwee, promo_until, now=now
    )
    payment = _find_payment_by_reference(supabase, user_id, reference)

    if payment and payment.get("status") == "completed":
        return 200, {
            "status": "completed",
            "tier": tier,
            "reference": reference,
            "payment_id": payment["id"],
            "message": "Payment already verified.",
        }

    try:
        collection = await fetch_collection_status(reference)
    except LencoApiError as exc:
        if exc.status_code == 404:
            return 502, {"detail": "Payment reference not found at Lenco."}
        if exc.status_code >= 500:
            return 502, {"detail": "Payment provider temporarily unavailable."}
        return 502, {"detail": "Could not verify payment with Lenco."}

    lenco_status = normalize_collection_status(collection)
    method_label = map_lenco_payment_method(collection)
    amount_ngwee = amount_to_ngwee(collection) or expected_ngwee
    lenco_ref = collection.get("lencoReference") or collection.get("id")

    if lenco_status == "failed":
        if payment:
            supabase.table("payments").update({
                "status": "failed",
                "webhook_data": collection,
            }).eq("id", payment["id"]).execute()
        return 402, {
            "detail": collection.get("reasonForFailure")
            or "Payment failed at Lenco.",
            "reference": reference,
        }

    if lenco_status == "processing":
        if not payment:
            sub = _subscription_row_for_user(supabase, user_id)
            insert = supabase.table("payments").insert({
                "user_id": user_id,
                "subscription_id": sub["id"],
                "amount": expected_ngwee,
                "currency": "ZMW",
                "payment_method": method_label,
                "provider": "lenco",
                "provider_ref": reference,
                "status": "pending",
                "webhook_data": _payment_webhook_data(collection, tier=tier),
            }).execute()
            payment_id = insert.data[0]["id"] if insert.data else None
        else:
            payment_id = payment["id"]
            supabase.table("payments").update({
                "webhook_data": _payment_webhook_data(collection, tier=tier),
            }).eq("id", payment_id).execute()
        return 202, {
            "status": "processing",
            "tier": tier,
            "reference": reference,
            "payment_id": payment_id,
            "message": "Payment is processing; you will be upgraded when Lenco confirms.",
        }

    # successful
    subscription_row = _subscription_row_for_user(supabase, user_id)
    if not payment:
        insert = supabase.table("payments").insert({
            "user_id": user_id,
            "subscription_id": subscription_row["id"],
            "amount": amount_ngwee,
            "currency": "ZMW",
            "payment_method": method_label,
            "provider": "lenco",
            "provider_ref": reference,
            "status": "pending",
            "webhook_data": _payment_webhook_data(collection, tier=tier),
        }).execute()
        if not insert.data:
            return 500, {"detail": "Failed to create payment record"}
        payment = insert.data[0]
        payment["subscriptions"] = subscription_row
    else:
        supabase.table("payments").update({
            "webhook_data": _payment_webhook_data(collection, tier=tier),
        }).eq("id", payment["id"]).execute()

    payment_id = payment["id"]
    if payment.get("status") == "completed":
        return 200, {
            "status": "completed",
            "tier": tier,
            "reference": reference,
            "payment_id": payment_id,
            "message": "Payment already verified.",
        }

    claim = (
        supabase.table("payments")
        .update({
            "status": "completed",
            "amount": amount_ngwee,
            "payment_method": method_label,
            "provider_ref": reference,
            "webhook_data": _payment_webhook_data(collection, tier=tier),
            "completed_at": now.isoformat(),
        })
        .eq("id", payment_id)
        .eq("status", "pending")
        .execute()
    )
    if not claim.data:
        refreshed = _find_payment_by_reference(supabase, user_id, reference)
        if refreshed and refreshed.get("status") == "completed":
            return 200, {
                "status": "completed",
                "tier": tier,
                "reference": reference,
                "payment_id": payment_id,
                "message": "Payment already verified.",
            }
        return 500, {"detail": "Could not finalize payment"}

    activate_subscription_after_payment(
        supabase,
        user_id=user_id,
        payment_id=payment_id,
        new_tier=tier,
        subscription_row=payment.get("subscriptions") or subscription_row,
        lenco_subscription_ref=str(lenco_ref) if lenco_ref else None,
        now=now,
    )

    return 200, {
        "status": "completed",
        "tier": tier,
        "reference": reference,
        "payment_id": payment_id,
        "message": "Payment confirmed — your plan is active.",
    }
