"""User account preference routes."""
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user_id, get_supabase
from app.schemas.user import AutoMatchPreferences, AutoMatchPreferencesUpdate, NotificationChannels

router = APIRouter(prefix="/users", tags=["Users"])


def _channels(raw: object) -> NotificationChannels:
    if isinstance(raw, dict):
        return NotificationChannels(
            whatsapp=bool(raw.get("whatsapp", True)),
            email=bool(raw.get("email", True)),
        )
    return NotificationChannels()


@router.get("/me/preferences/auto-match", response_model=AutoMatchPreferences)
async def get_auto_match_preferences(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    result = (
        supabase.table("users")
        .select("auto_match_enabled, notification_channels")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return AutoMatchPreferences(
        auto_match_enabled=result.data.get("auto_match_enabled", True),
        notification_channels=_channels(result.data.get("notification_channels")),
    )


@router.patch("/me/preferences/auto-match", response_model=AutoMatchPreferences)
async def update_auto_match_preferences(
    body: AutoMatchPreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    update_data = body.model_dump(exclude_unset=True, mode="json")
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields to update")
    supabase.table("users").update(update_data).eq("id", user_id).execute()
    return await get_auto_match_preferences(user_id, supabase)
