"""Business profile CRUD (PR N1).

One business_profile per user (PK same as users.id). Used by the
/tenders/matches embedding-based match RPC. Frontend uses this to drive
the /business-profile setup wizard.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.deps import get_current_user_id, get_supabase
from app.schemas.business_profiles import (
    BusinessProfileCreate,
    BusinessProfileResponse,
    BusinessProfileUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/business-profile", tags=["Business Profile"])


@router.get("", response_model=BusinessProfileResponse)
async def get_business_profile(
    current_user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
) -> BusinessProfileResponse:
    """Read the authenticated user's business profile.

    404 if the user hasn't created one yet — the frontend uses this to
    decide whether to show the setup wizard vs the dashboard.
    """
    try:
        res = (
            supabase.table("business_profiles")
            .select("*")
            .eq("id", current_user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("business_profile fetch failed user=%s", current_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load business profile.",
        ) from exc

    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not set up yet.",
        )

    return BusinessProfileResponse(**res.data[0])


@router.put("", response_model=BusinessProfileResponse)
async def upsert_business_profile(
    body: BusinessProfileUpdate,
    current_user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
) -> BusinessProfileResponse:
    """Create or update the authenticated user's business profile.

    Idempotent upsert keyed on the user's UUID. First call requires all
    base fields (enforced via BusinessProfileCreate validation); subsequent
    calls can be partial.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Check if profile exists.
    try:
        existing = (
            supabase.table("business_profiles")
            .select("id")
            .eq("id", current_user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("business_profile existence check failed user=%s", current_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not check existing profile.",
        ) from exc

    if not existing.data:
        # First-time create — validate that all required fields are present.
        try:
            create_payload = BusinessProfileCreate(
                **{k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
            )
        except Exception as exc:
            # Validation error → 422 with field-level detail (Pydantic surfaces this).
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Initial profile creation requires all base fields: {exc}",
            ) from exc

        insert_data = {
            "id": current_user_id,
            "company_name": create_payload.company_name,
            "phone_number": create_payload.phone_number,
            "industry_tags": create_payload.industry_tags,
            "operating_provinces": create_payload.operating_provinces,
            "company_bio": create_payload.company_bio,
            "created_at": now,
            "updated_at": now,
        }
        try:
            ins_res = supabase.table("business_profiles").insert(insert_data).execute()
        except Exception as exc:
            logger.exception("business_profile insert failed user=%s", current_user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create profile.",
            ) from exc
        if not ins_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Profile insert returned empty.",
            )
        return BusinessProfileResponse(**ins_res.data[0])

    # Partial update path.
    patch = body.model_dump(exclude_unset=True, exclude_none=True)
    if not patch:
        # Nothing to update — return current row.
        cur = (
            supabase.table("business_profiles")
            .select("*")
            .eq("id", current_user_id)
            .limit(1)
            .execute()
        )
        return BusinessProfileResponse(**cur.data[0])

    patch["updated_at"] = now
    try:
        upd_res = (
            supabase.table("business_profiles")
            .update(patch)
            .eq("id", current_user_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("business_profile update failed user=%s", current_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update profile.",
        ) from exc
    if not upd_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found after update.",
        )
    return BusinessProfileResponse(**upd_res.data[0])


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_profile(
    current_user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
) -> None:
    """Clear the authenticated user's business profile.

    Hard delete — RLS keeps users from deleting anyone else's. Used when a
    user switches from B2B back to B2C usage and wants to remove the
    profile entirely.
    """
    try:
        supabase.table("business_profiles").delete().eq("id", current_user_id).execute()
    except Exception as exc:
        logger.exception("business_profile delete failed user=%s", current_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete profile.",
        ) from exc
