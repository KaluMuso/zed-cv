"""User account preference routes."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.core.deps import get_current_user_id, get_supabase
from app.schemas.saved_jobs import SavedJobsList
from app.schemas.user import (
    AutoMatchPreferences,
    AutoMatchPreferencesUpdate,
    NotificationChannels,
    UserPreferences,
    UserPreferencesUpdate,
)
from app.services.job_hydration import hydrate_job_row

router = APIRouter(prefix="/users", tags=["Users"])

_SETTINGS_SELECT = (
    "phone, whatsapp_number, location, currency, alert_frequency, whatsapp_verified"
)


def _effective_whatsapp_number(row: dict[str, Any]) -> str | None:
    """Delivery number; falls back to auth phone when unset."""
    return row.get("whatsapp_number") or row.get("phone")


def _row_to_user_preferences(row: dict[str, Any]) -> UserPreferences:
    return UserPreferences(
        whatsapp_number=_effective_whatsapp_number(row),
        location=row.get("location"),
        currency=row.get("currency") or "ZMW",
        alert_frequency=row.get("alert_frequency") or "daily",
        whatsapp_verified=bool(row.get("whatsapp_verified", False)),
    )


async def _fetch_user_settings_row(user_id: str, supabase) -> dict[str, Any]:
    result = (
        supabase.table("users")
        .select(_SETTINGS_SELECT)
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return result.data


@router.get("/me/saved-jobs", response_model=SavedJobsList)
async def list_saved_jobs(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    rows = (
        supabase.table("saved_jobs")
        .select("created_at, jobs(*, job_skills(skills(name)))")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    jobs_out = []
    for row in rows.data or []:
        nested = row.get("jobs")
        if isinstance(nested, dict):
            try:
                jobs_out.append(hydrate_job_row(nested))
            except ValidationError:
                continue
    return SavedJobsList(jobs=jobs_out)


def _channels(raw: object) -> NotificationChannels:
    if isinstance(raw, dict):
        return NotificationChannels(
            whatsapp=bool(raw.get("whatsapp", True)),
            email=bool(raw.get("email", True)),
        )
    return NotificationChannels()


@router.get("/me/preferences", response_model=UserPreferences)
async def get_user_preferences(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    row = await _fetch_user_settings_row(user_id, supabase)
    return _row_to_user_preferences(row)


@router.patch("/me/preferences", response_model=UserPreferences)
async def update_user_preferences(
    body: UserPreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields to update")

    existing = await _fetch_user_settings_row(user_id, supabase)

    if "whatsapp_number" in update_data:
        new_number = update_data["whatsapp_number"]
        prior = _effective_whatsapp_number(existing)
        if new_number != prior:
            update_data["whatsapp_verified"] = False

    supabase.table("users").update(update_data).eq("id", user_id).execute()
    refreshed = await _fetch_user_settings_row(user_id, supabase)
    return _row_to_user_preferences(refreshed)


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
