"""OTP helpers and sensitive-action step-up verification (Bucket 8.5 + 9)."""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.config import Settings

log = logging.getLogger(__name__)

SENSITIVE_ACTIONS = frozenset({
    "delete_account",
    "change_tier",
    "change_phone",
    "change_email",
    "export_data",
})

ACTION_TO_OTP_PURPOSE = {
    "delete_account": "delete_account",
    "export_data": "export_data",
}


def hash_otp_code(code: str, phone: str, secret: str) -> str:
    """HMAC-SHA256(secret, phone:code) — matches auth route storage."""
    message = f"{phone}:{code}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def is_sensitive_action(action: str | None) -> bool:
    return action is not None and action in SENSITIVE_ACTIONS


def requires_otp_for_action(action: str | None) -> bool:
    return is_sensitive_action(action)


def verify_sensitive_action_otp(
    *,
    user_phone: str,
    otp_code: str,
    action: str,
    supabase: Any,
    settings: Settings,
) -> None:
    """Require a fresh, valid OTP before delete/export/consent-sensitive flows.

    Raises HTTPException 401/400 on failure. Marks the OTP row verified on success.
    """
    if not requires_otp_for_action(action):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown sensitive action: {action}",
        )

    code = otp_code.strip()
    if len(code) != settings.otp_code_length or not code.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP must be a 6-digit code",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    code_hash = hash_otp_code(code, user_phone, settings.jwt_secret)
    result = (
        supabase.table("otp_codes")
        .select("id, attempts")
        .eq("phone", user_phone)
        .eq("code", code_hash)
        .eq("verified", False)
        .gte("expires_at", now_iso)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP. Request a new code first.",
        )

    row = result.data[0]
    if (row.get("attempts") or 0) >= settings.max_otp_attempts:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Too many OTP attempts. Request a new code.",
        )

    supabase.table("otp_codes").update({"verified": True}).eq("id", row["id"]).execute()
