from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from app.core.deps import get_supabase, get_current_user_id
from app.schemas.boosters import (
    BoosterPurchaseRequest, 
    BoosterPurchaseResponse, 
    EntitlementResponse, 
    ConsumeBoosterRequest
)
from supabase import Client
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/boosters", tags=["Boosters"])

@router.get("", response_model=List[EntitlementResponse])
async def list_boosters(
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase)
):
    """Returns user's active and consumed entitlements."""
    res = supabase.table("user_entitlements").select("*").eq("user_id", user_id).execute()
    return res.data

@router.post("/purchase", response_model=BoosterPurchaseResponse)
async def purchase_booster(
    req: BoosterPurchaseRequest,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase)
):
    """Initiates a Lenco checkout for a booster. Creates a pending payment and entitlement."""
    # Lookup SKU
    sku_res = supabase.table("booster_skus").select("*").eq("sku", req.sku).execute()
    if not sku_res.data:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    amount_ngwee = sku_res.data[0]["price_ngwee"]
    reference = f"zedapply-{user_id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    # Create pending payment row, no subscription_id
    payment_insert = supabase.table("payments").insert({
        "user_id": user_id,
        "amount": amount_ngwee,
        "currency": "ZMW",
        "payment_method": "lenco",
        "provider": "lenco",
        "provider_ref": reference,
        "status": "pending",
        "webhook_data": {"intended_sku": req.sku}
    }).execute()
    payment_id = payment_insert.data[0]["id"]

    # Create pending entitlement
    supabase.table("user_entitlements").insert({
        "user_id": user_id,
        "booster_sku": req.sku,
        "payment_id": payment_id,
        "status": "pending",
    }).execute()

    return BoosterPurchaseResponse(
        message="Payment initiated",
        transaction_id="pending",
        reference=reference,
        amount_ngwee=amount_ngwee,
    )

@router.post("/{id}/consume")
async def consume_booster(
    id: str,
    req: ConsumeBoosterRequest,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase)
):
    """Uses one charge, applies the CV boost."""
    res = supabase.table("user_entitlements").select("*").eq("id", id).eq("user_id", user_id).eq("status", "paid").execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="Booster not found or already consumed/pending")

    now = datetime.now(timezone.utc)
    supabase.table("user_entitlements").update({
        "status": "consumed",
        "consumed_at": now.isoformat()
    }).eq("id", id).execute()

    # The actual application of the boost (e.g., priority review) would happen here.
    return {"message": "Booster consumed successfully"}
