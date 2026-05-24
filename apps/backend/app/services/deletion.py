"""Scheduled account erasure (ZDPA right-to-erasure, Bucket 9)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.config import Settings
from app.services.otp import verify_sensitive_action_otp
from app.services.storage import purge_cv_storage

log = logging.getLogger(__name__)

GRACE_DAYS = 7

# Tables wiped by user_id (order after safety check + storage purge).
_HARD_DELETE_TABLES = (
    "user_skills",
    "cvs",
    "matches",
    "cv_generations",
    "generated_documents",
    "application_outcomes",
    "user_preferences",
    "interview_sessions",
    "aptitude_scores",
    "saved_jobs",
    "cv_upload_queue",
)

_ANONYMISE_TABLES = ("payments", "consent_log")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _count_deleted(supabase: Any, table: str, user_id: str) -> int:
    rows = (
        supabase.table(table)
        .select("id")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    if not rows:
        return 0
    supabase.table(table).delete().eq("user_id", user_id).execute()
    return len(rows)


def _delete_bwana_chat_cache(supabase: Any, user_id: str) -> int:
    """Bwana history lives in ai_cache (cache_type=bwana_chat), not a separate table."""
    rows = (
        supabase.table("ai_cache")
        .select("id, result")
        .eq("cache_type", "bwana_chat")
        .execute()
        .data
        or []
    )
    removed = 0
    for row in rows:
        payload = row.get("result") or {}
        if isinstance(payload, dict) and str(payload.get("user_id")) == user_id:
            supabase.table("ai_cache").delete().eq("id", row["id"]).execute()
            removed += 1
    return removed


def _delete_otp_codes_for_phone(supabase: Any, phone: str) -> int:
    rows = (
        supabase.table("otp_codes")
        .select("id")
        .eq("phone", phone)
        .execute()
        .data
        or []
    )
    if not rows:
        return 0
    supabase.table("otp_codes").delete().eq("phone", phone).execute()
    return len(rows)


def _delete_trusted_devices_if_present(supabase: Any, user_id: str) -> int:
    try:
        return _count_deleted(supabase, "trusted_devices", user_id)
    except Exception as exc:  # noqa: BLE001
        log.debug("trusted_devices purge skipped: %s", exc)
        return 0


def _phone_on_safety_allowlist(phone: str, supabase: Any) -> bool:
    row = (
        supabase.table("deletion_safety_allowlist")
        .select("phone")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )
    return bool(row.data)


def request_deletion(
    user_id: str,
    *,
    otp_code: str,
    supabase: Any,
    settings: Settings,
) -> dict[str, Any]:
    """Insert a pending deletion after sensitive-action OTP verification."""
    user_row = (
        supabase.table("users")
        .select("id, phone, deleted_at")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not user_row.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_row.data[0]
    if user.get("deleted_at"):
        raise HTTPException(status_code=409, detail="Account already deleted")

    phone = user.get("phone")
    if not phone:
        raise HTTPException(status_code=500, detail="Account is missing a phone of record")

    verify_sensitive_action_otp(
        user_phone=phone,
        otp_code=otp_code,
        action="delete_account",
        supabase=supabase,
        settings=settings,
    )

    pending = (
        supabase.table("data_deletion_requests")
        .select("id")
        .eq("user_id", user_id)
        .eq("status", "pending")
        .limit(1)
        .execute()
    )
    if pending.data:
        raise HTTPException(
            status_code=409,
            detail="A deletion request is already pending",
        )

    now = _now()
    scheduled = now + timedelta(days=GRACE_DAYS)
    inserted = (
        supabase.table("data_deletion_requests")
        .insert({
            "user_id": user_id,
            "requested_at": now.isoformat(),
            "scheduled_at": scheduled.isoformat(),
            "status": "pending",
        })
        .execute()
    )
    row = inserted.data[0] if inserted.data else {}
    return {
        "request_id": row.get("id"),
        "status": "pending",
        "scheduled_at": scheduled.isoformat(),
    }


def cancel_deletion(user_id: str, request_id: str, supabase: Any) -> dict[str, Any]:
    result = (
        supabase.table("data_deletion_requests")
        .select("id, status")
        .eq("id", request_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    row = result.data[0]
    if row.get("status") != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel request in status {row.get('status')}",
        )
    supabase.table("data_deletion_requests").update({
        "status": "cancelled",
    }).eq("id", request_id).execute()
    return {"request_id": request_id, "status": "cancelled"}


def execute_deletion(request_id: str, supabase: Any) -> dict[str, Any]:
    """Run erasure for a due request. Safety allowlist is checked before any DELETE."""
    req = (
        supabase.table("data_deletion_requests")
        .select("id, user_id, status, scheduled_at")
        .eq("id", request_id)
        .limit(1)
        .execute()
    )
    if not req.data:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    request_row = req.data[0]
    if request_row.get("status") not in ("pending", "executing"):
        raise HTTPException(
            status_code=400,
            detail=f"Request not executable (status={request_row.get('status')})",
        )

    user_id = request_row["user_id"]
    user = (
        supabase.table("users")
        .select("id, phone, email, full_name")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not user.data:
        _mark_failed(supabase, request_id, "user_not_found")
        return {"status": "failed", "failure_reason": "user_not_found"}

    phone = user.data[0].get("phone") or ""

    # Hard rule: allowlist BEFORE any destructive statement.
    if phone and _phone_on_safety_allowlist(phone, supabase):
        _mark_failed(supabase, request_id, "safety_allowlist")
        return {"status": "failed", "failure_reason": "safety_allowlist"}

    supabase.table("data_deletion_requests").update({
        "status": "executing",
    }).eq("id", request_id).execute()

    artifacts: dict[str, Any] = {"hard_deleted": {}, "anonymised": {}, "storage": {}}

    try:
        artifacts["storage"]["cv_files_removed"] = purge_cv_storage(user_id, supabase)

        for table in _HARD_DELETE_TABLES:
            artifacts["hard_deleted"][table] = _count_deleted(supabase, table, user_id)

        artifacts["hard_deleted"]["otp_codes"] = _delete_otp_codes_for_phone(
            supabase, phone
        )
        artifacts["hard_deleted"]["trusted_devices"] = _delete_trusted_devices_if_present(
            supabase, user_id
        )
        artifacts["hard_deleted"]["ai_cache_bwana_chat"] = _delete_bwana_chat_cache(
            supabase, user_id
        )

        for table in _ANONYMISE_TABLES:
            count = (
                supabase.table(table)
                .select("id")
                .eq("user_id", user_id)
                .execute()
                .data
                or []
            )
            if count:
                supabase.table(table).update({"user_id": None}).eq(
                    "user_id", user_id
                ).execute()
            artifacts["anonymised"][table] = len(count)

        sub_count = (
            supabase.table("subscriptions")
            .select("id")
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )
        if sub_count:
            supabase.table("subscriptions").update({"user_id": None}).eq(
                "user_id", user_id
            ).execute()
        artifacts["anonymised"]["subscriptions"] = len(sub_count)

        now = _now()
        supabase.table("users").update({
            "phone": None,
            "email": None,
            "full_name": None,
            "deleted_at": now.isoformat(),
            "is_active": False,
        }).eq("id", user_id).execute()

        supabase.table("data_deletion_requests").update({
            "status": "completed",
            "executed_at": now.isoformat(),
            "artifacts": artifacts,
            "failure_reason": None,
        }).eq("id", request_id).execute()

        return {"status": "completed", "artifacts": artifacts}
    except Exception as exc:  # noqa: BLE001
        log.exception("execute_deletion failed request_id=%s", request_id)
        _mark_failed(supabase, request_id, str(exc)[:500])
        raise


def _mark_failed(supabase: Any, request_id: str, reason: str) -> None:
    supabase.table("data_deletion_requests").update({
        "status": "failed",
        "failure_reason": reason,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", request_id).execute()
