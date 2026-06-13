from fastapi import APIRouter, Depends, HTTPException
from app.core.deps import get_supabase, require_superadmin

router = APIRouter(prefix="/admin/referrals", tags=["Admin Referrals"], dependencies=[Depends(require_superadmin)])

@router.get("/config")
async def get_referral_config(supabase=Depends(get_supabase)):
    res = supabase.table("referral_config").select("*").order("id").execute()
    return {"configs": res.data or []}

@router.get("/payouts")
async def get_pending_payouts(supabase=Depends(get_supabase)):
    res = (
        supabase.table("referral_rewards")
        .select("id, user_id, reward_value, earned_at, status, users(phone)")
        .eq("reward_type", "cash")
        .eq("status", "pending_payout")
        .order("earned_at")
        .execute()
    )
    
    payouts = []
    for r in (res.data or []):
        phone = r.get("users", {}).get("phone") if isinstance(r.get("users"), dict) else None
        payouts.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "phone": phone,
            "amount_ngwee": r["reward_value"],
            "created_at": r["earned_at"]
        })
    return {"payouts": payouts}

@router.post("/payouts/{reward_id}/mark-paid")
async def mark_payout_paid(reward_id: int, supabase=Depends(get_supabase)):
    res = supabase.table("referral_rewards").update({"status": "credited"}).eq("id", reward_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Reward not found")
    return {"message": "Marked as paid"}

@router.patch("/config/{config_id}")
async def update_referral_config(config_id: int, body: dict, supabase=Depends(get_supabase)):
    allowed_keys = {"required_count", "reward_value", "is_active"}
    update_data = {k: v for k, v in body.items() if k in allowed_keys}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
        
    res = supabase.table("referral_config").update(update_data).eq("id", config_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"config": res.data[0]}
