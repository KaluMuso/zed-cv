"""User account preference and data-rights routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.deps import get_current_user_id, get_supabase
from app.schemas.data_rights import (
    ConsentRecordResponse,
    ConsentUpdateBody,
    ConsentUpdateResponse,
    DeletionCancelResponse,
    DeletionRequestResponse,
    ExportRequestResponse,
    ExportStatusResponse,
    SensitiveActionBody,
)
from app.services.deletion import cancel_deletion, request_deletion
from app.services.export import generate_export, get_export_status, request_export
from app.schemas.saved_jobs import SavedJobsList
from app.schemas.user import (
    AutoMatchPreferences,
    AutoMatchPreferencesUpdate,
    NotificationChannels,
    UserPreferences,
    UserPreferencesUpdate,
)
from app.services.job_hydration import hydrate_job_row
from app.services.notification_channels import (
    validate_channel_update,
    whatsapp_digest_allowed,
)

router = APIRouter(prefix="/users", tags=["Users"])

_SETTINGS_SELECT = (
    "phone, whatsapp_number, location, currency, alert_frequency, whatsapp_verified, "
    "preferred_notification_channel, subscription_tier"
)


def _effective_whatsapp_number(row: dict[str, Any]) -> str | None:
    """Delivery number; falls back to auth phone when unset."""
    return row.get("whatsapp_number") or row.get("phone")


def _row_to_user_preferences(row: dict[str, Any]) -> UserPreferences:
    tier = (row.get("subscription_tier") or "free").strip().lower()
    return UserPreferences(
        whatsapp_number=_effective_whatsapp_number(row),
        location=row.get("location"),
        currency=row.get("currency") or "ZMW",
        alert_frequency=row.get("alert_frequency") or "daily",
        whatsapp_verified=bool(row.get("whatsapp_verified", False)),
        preferred_notification_channel=row.get("preferred_notification_channel") or "email",
        whatsapp_digest_available=whatsapp_digest_allowed(row),
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

    if "preferred_notification_channel" in update_data:
        tier = (existing.get("subscription_tier") or "free").strip().lower()
        try:
            update_data["preferred_notification_channel"] = validate_channel_update(
                update_data["preferred_notification_channel"],
                tier,
            )
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

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


# ── ZDPA: scheduled deletion, portable export, consent log (Bucket 9) ──


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _legal_doc_version(consent_type: str, supabase) -> str | None:
    slug = None
    if consent_type == "terms_of_service":
        slug = "terms"
    elif consent_type == "privacy_policy":
        slug = "privacy"
    if not slug:
        return None
    row = (
        supabase.table("legal_docs")
        .select("version")
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if row.data:
        return row.data[0].get("version")
    return None


@router.post("/me/delete-request", response_model=DeletionRequestResponse)
async def create_delete_request(
    body: SensitiveActionBody,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Schedule account erasure after 7-day grace (requires fresh OTP)."""
    result = request_deletion(
        user_id,
        otp_code=body.otp_code,
        supabase=supabase,
        settings=settings,
    )
    return DeletionRequestResponse(**result)


@router.post("/me/delete-cancel/{request_id}", response_model=DeletionCancelResponse)
async def cancel_delete_request(
    request_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    result = cancel_deletion(user_id, request_id, supabase)
    return DeletionCancelResponse(**result)


@router.post("/me/export-request", response_model=ExportRequestResponse)
async def create_export_request(
    body: SensitiveActionBody,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Start a ZIP data export (requires fresh OTP). Generation runs in background."""
    result = request_export(
        user_id,
        otp_code=body.otp_code,
        supabase=supabase,
        settings=settings,
    )
    request_id = result.get("request_id")
    if request_id and result.get("status") == "pending":
        background_tasks.add_task(generate_export, request_id, supabase)
    return ExportRequestResponse(**result)


@router.get("/me/export-status/{request_id}", response_model=ExportStatusResponse)
async def read_export_status(
    request_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    result = get_export_status(user_id, request_id, supabase)
    return ExportStatusResponse(**result)


@router.post("/me/consent", response_model=ConsentUpdateResponse)
async def record_consent(
    body: ConsentUpdateBody,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Append an immutable consent_log row (service role insert)."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    version = _legal_doc_version(body.consent_type, supabase)
    inserted = (
        supabase.table("consent_log")
        .insert({
            "user_id": user_id,
            "consent_type": body.consent_type,
            "granted": body.granted,
            "granted_at": now.isoformat(),
            "legal_doc_version": version,
            "ip_address": _client_ip(request),
            "user_agent": (request.headers.get("user-agent") or "")[:500] or None,
        })
        .execute()
    )
    row = inserted.data[0] if inserted.data else {}
    record = ConsentRecordResponse(
        consent_type=body.consent_type,
        granted=body.granted,
        granted_at=row.get("granted_at") or now.isoformat(),
        legal_doc_version=version,
    )
    return ConsentUpdateResponse(consent=record)
