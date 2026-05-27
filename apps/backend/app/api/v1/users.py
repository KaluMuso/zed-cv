"""User account preference routes."""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.core.deps import get_current_user_id, get_supabase
from app.schemas.application_status import (
    ApplicationStatus,
    ApplicationStatusResponse,
    ApplicationStatusUpdate,
    SavedJobApplication,
)
from app.schemas.data_rights import (
    ConsentRecordResponse,
    ConsentStatusResponse,
    ConsentUpdateBody,
    ConsentUpdateResponse,
)
from app.schemas.saved_jobs import SavedJobsList
from app.services.application_status import validate_status_transition
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
    "preferred_notification_channel, subscription_tier, quiet_hours_start, quiet_hours_end, "
    "profile_visible_to_employers, hidden_employer_name, notify_product_updates, display_timezone"
)


def _effective_whatsapp_number(row: dict[str, Any]) -> str | None:
    """Delivery number; falls back to auth phone when unset."""
    return row.get("whatsapp_number") or row.get("phone")


def _format_time_field(value: object) -> str:
    if value is None:
        return "20:00"
    text = str(value)
    return text[:5] if len(text) >= 5 else text


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
        quiet_hours_start=_format_time_field(row.get("quiet_hours_start")),
        quiet_hours_end=_format_time_field(row.get("quiet_hours_end")),
        profile_visible_to_employers=bool(row.get("profile_visible_to_employers", True)),
        hidden_employer_name=row.get("hidden_employer_name"),
        notify_product_updates=bool(row.get("notify_product_updates", False)),
        display_timezone=row.get("display_timezone") or "Africa/Lusaka",
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


def _parse_application_status(raw: object) -> ApplicationStatus:
    try:
        return ApplicationStatus(str(raw or ApplicationStatus.saved.value))
    except ValueError:
        return ApplicationStatus.saved


@router.get("/me/saved-jobs", response_model=SavedJobsList)
async def list_saved_jobs(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    rows = (
        supabase.table("saved_jobs")
        .select(
            "application_status, status_updated_at, application_notes, interview_date, "
            "created_at, jobs(*, job_skills(skills(name)))"
        )
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    jobs_out = []
    applications_out: list[SavedJobApplication] = []
    for row in rows.data or []:
        nested = row.get("jobs")
        if isinstance(nested, dict):
            try:
                job = hydrate_job_row(nested)
            except ValidationError:
                continue
            jobs_out.append(job)
            applications_out.append(
                SavedJobApplication(
                    job=job,
                    application_status=_parse_application_status(
                        row.get("application_status")
                    ),
                    status_updated_at=row.get("status_updated_at"),
                    application_notes=row.get("application_notes"),
                    interview_date=row.get("interview_date"),
                )
            )
    return SavedJobsList(jobs=jobs_out, applications=applications_out)


@router.patch(
    "/me/saved-jobs/{job_id}/status",
    response_model=ApplicationStatusResponse,
)
async def update_saved_job_status(
    job_id: UUID,
    body: ApplicationStatusUpdate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    job_id_str = str(job_id)
    existing = (
        supabase.table("saved_jobs")
        .select(
            "id, application_status, application_notes, interview_date, status_updated_at"
        )
        .eq("user_id", user_id)
        .eq("job_id", job_id_str)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Saved job not found")

    row = existing.data[0]
    current_status = _parse_application_status(row.get("application_status"))
    try:
        validate_status_transition(current_status, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    now = datetime.now(timezone.utc)
    update_data: dict[str, Any] = {
        "application_status": body.status.value,
        "status_updated_at": now.isoformat(),
    }
    if body.notes is not None:
        update_data["application_notes"] = body.notes
    if body.interview_date is not None:
        update_data["interview_date"] = body.interview_date.isoformat()

    updated = (
        supabase.table("saved_jobs")
        .update(update_data)
        .eq("user_id", user_id)
        .eq("job_id", job_id_str)
        .execute()
    )
    saved_row = {**row, **update_data}
    if updated.data:
        saved_row = {**updated.data[0], **update_data}

    if body.status != current_status:
        supabase.table("application_status_history").insert(
            {
                "saved_job_id": row["id"],
                "from_status": current_status.value,
                "to_status": body.status.value,
                "changed_at": now.isoformat(),
                "changed_by_user_id": user_id,
            }
        ).execute()

    return ApplicationStatusResponse(
        job_id=job_id_str,
        application_status=body.status,
        status_updated_at=saved_row.get("status_updated_at"),
        application_notes=saved_row.get("application_notes"),
        interview_date=saved_row.get("interview_date"),
    )


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


# ── Consent audit log (privacy settings) ──

_CONSENT_DEFAULTS: dict[str, bool] = {
    "terms_of_service": True,
    "privacy_policy": True,
    "marketing_email": False,
    "marketing_whatsapp": False,
    "analytics_cookies": False,
    "third_party_data_sharing": False,
}


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


def _latest_consent_by_type(user_id: str, supabase) -> tuple[dict[str, bool], dict[str, str]]:
    rows = (
        supabase.table("consent_log")
        .select("consent_type, granted, granted_at")
        .eq("user_id", user_id)
        .order("granted_at", desc=True)
        .execute()
    )
    consents = dict(_CONSENT_DEFAULTS)
    last_updated: dict[str, str] = {}
    seen: set[str] = set()
    for row in rows.data or []:
        ctype = row.get("consent_type")
        if not ctype or ctype in seen:
            continue
        seen.add(ctype)
        consents[ctype] = bool(row.get("granted"))
        granted_at = row.get("granted_at")
        if granted_at:
            last_updated[ctype] = str(granted_at)
    return consents, last_updated


@router.get("/me/consent", response_model=ConsentStatusResponse)
async def get_consent_status(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Latest consent flag per type from consent_log (defaults when unset)."""
    consents, last_updated = _latest_consent_by_type(user_id, supabase)
    return ConsentStatusResponse(consents=consents, last_updated=last_updated)


@router.post("/me/consent", response_model=ConsentUpdateResponse)
async def record_consent(
    body: ConsentUpdateBody,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Append an immutable consent_log row (service role insert)."""
    now = datetime.now(timezone.utc)
    version = _legal_doc_version(body.consent_type, supabase)
    inserted = (
        supabase.table("consent_log")
        .insert(
            {
                "user_id": user_id,
                "consent_type": body.consent_type,
                "granted": body.granted,
                "granted_at": now.isoformat(),
                "legal_doc_version": version,
                "ip_address": _client_ip(request),
                "user_agent": (request.headers.get("user-agent") or "")[:500] or None,
            }
        )
        .execute()
    )
    row = inserted.data[0] if inserted.data else {}
    granted_at = row.get("granted_at")
    if not isinstance(granted_at, str):
        granted_at = now.isoformat()
    record = ConsentRecordResponse(
        consent_type=body.consent_type,
        granted=body.granted,
        granted_at=granted_at,
        legal_doc_version=version,
    )
    return ConsentUpdateResponse(consent=record)
