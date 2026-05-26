"""OTP generation, delivery, trusted-device checks, and sensitive-action gating."""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import Settings, get_settings
from app.services.email import send_otp_email
from app.services.email_delivery import EmailDeliveryError
from app.services.whatsapp import ensure_session_started, send_whatsapp_otp

log = logging.getLogger(__name__)

SENSITIVE_ACTIONS = frozenset({
    "delete_account",
    "change_tier",
    "change_phone",
    "change_email",
    "export_data",
})

PAID_TIERS = frozenset({"starter", "professional", "super_standard"})
OTP_CHANNELS = frozenset({"email", "whatsapp", "both"})


def hash_otp_code(code: str, phone: str, secret: str) -> str:
    """HMAC-SHA256(secret, phone:code) — matches auth route storage."""
    message = f"{phone}:{code}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def hash_device_token(raw_token: str) -> str:
    """SHA-256 of the raw device trust token (stored in trusted_devices)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def is_sensitive_action(action: str | None) -> bool:
    return action is not None and action in SENSITIVE_ACTIONS


def requires_otp_for_action(action: str | None) -> bool:
    """Sensitive actions always need a fresh OTP even on a trusted device."""
    return is_sensitive_action(action)


def default_otp_channel_for_tier(tier: str | None) -> str:
    """Free tier defaults to email; paid tiers default to WhatsApp."""
    if tier and tier in PAID_TIERS:
        return "whatsapp"
    return "email"


def resolve_otp_channel(
    *,
    user_row: dict[str, Any] | None,
    tier: str | None,
    requested_channel: str | None,
) -> str:
    """Pick delivery channel: explicit request > user pref > tier default."""
    if requested_channel and requested_channel in OTP_CHANNELS:
        return requested_channel
    if user_row:
        pref = user_row.get("otp_channel_preference")
        if pref in OTP_CHANNELS:
            return pref
    return default_otp_channel_for_tier(tier)


def generate_otp_code(settings: Settings) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(settings.otp_code_length))


async def send_otp(
    *,
    phone: str,
    code: str,
    channel: str,
    email: str | None,
) -> None:
    """Dispatch OTP via Resend (email) or WAHA (whatsapp)."""
    if channel == "email":
        if not email:
            raise ValueError("Email required for email OTP channel")
        await send_otp_email(email, code)
        return

    if channel in ("whatsapp", "both"):
        session_ok = await ensure_session_started("default", timeout_seconds=20)
        if not session_ok:
            raise RuntimeError("WAHA session not WORKING")
        await send_whatsapp_otp(phone, code)
        if channel == "both" and email:
            try:
                await send_otp_email(email, code)
            except EmailDeliveryError:
                log.warning(
                    "Email leg of both-channel OTP failed for %s; WhatsApp sent",
                    phone,
                )
        return

    raise ValueError(f"Unknown OTP channel: {channel}")


def is_device_trusted(
    user_id: str,
    raw_device_token: str | None,
    supabase: Any,
    *,
    now: datetime | None = None,
) -> bool:
    if not raw_device_token or not raw_device_token.strip():
        return False
    now = now or datetime.now(timezone.utc)
    token_hash = hash_device_token(raw_device_token.strip())
    result = (
        supabase.table("trusted_devices")
        .select("id, expires_at")
        .eq("user_id", user_id)
        .eq("device_token_hash", token_hash)
        .is_("revoked_at", "null")
        .gte("expires_at", now.isoformat())
        .limit(1)
        .execute()
    )
    if not result.data:
        return False
    row = result.data[0]
    supabase.table("trusted_devices").update({
        "last_used_at": now.isoformat(),
    }).eq("id", row["id"]).execute()
    return True


def register_trusted_device(
    user_id: str,
    raw_device_token: str,
    *,
    label: str | None,
    ip: str | None,
    supabase: Any,
    ttl_days: int = 365,
) -> None:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=ttl_days)
    token_hash = hash_device_token(raw_device_token)
    supabase.table("trusted_devices").insert({
        "user_id": user_id,
        "device_token_hash": token_hash,
        "device_label": label,
        "ip_first_seen": ip,
        "ip_last_seen": ip,
        "expires_at": expires.isoformat(),
        "last_used_at": now.isoformat(),
    }).execute()


def lookup_user_auth_context(phone: str, supabase: Any) -> dict[str, Any] | None:
    """Return user row + subscription tier for OTP/login routing."""
    user_result = (
        supabase.table("users")
        .select("id, role, email, otp_channel_preference")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )
    if not user_result.data:
        return None
    user = user_result.data[0]
    sub = (
        supabase.table("subscriptions")
        .select("tier")
        .eq("user_id", user["id"])
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    tier = "free"
    if sub.data:
        tier = sub.data[0].get("tier") or "free"
    user["tier"] = tier
    return user


def otp_delivery_message(channel: str) -> str:
    if channel == "email":
        return "OTP sent to your email"
    if channel == "both":
        return "OTP sent to your email and WhatsApp"
    return "OTP sent to your WhatsApp"
