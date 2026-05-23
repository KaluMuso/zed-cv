"""Helpers for preferred_notification_channel and tier-gated WhatsApp digests."""
from __future__ import annotations

from typing import Any

PAID_TIERS = frozenset({"starter", "professional", "super_standard"})
PreferredChannel = str


def normalize_preferred_channel(raw: object) -> PreferredChannel:
    value = (raw or "email").strip().lower() if isinstance(raw, str) else "email"
    if value in ("email", "whatsapp", "both"):
        return value
    return "email"


def user_subscription_tier(row: dict[str, Any]) -> str:
    return (row.get("subscription_tier") or "free").strip().lower()


def whatsapp_digest_allowed(row: dict[str, Any]) -> bool:
    return user_subscription_tier(row) in PAID_TIERS


def wants_email_digest(row: dict[str, Any]) -> bool:
    channel = normalize_preferred_channel(row.get("preferred_notification_channel"))
    if channel not in ("email", "both"):
        return False
    if row.get("email_notifications_enabled") is False:
        return False
    email = (row.get("email") or "").strip()
    return bool(email)


def wants_whatsapp_digest(row: dict[str, Any]) -> bool:
    channel = normalize_preferred_channel(row.get("preferred_notification_channel"))
    if channel not in ("whatsapp", "both"):
        return False
    if not whatsapp_digest_allowed(row):
        return False
    if not row.get("whatsapp_verified"):
        return False
    phone = (row.get("whatsapp_number") or row.get("phone") or "").strip()
    return bool(phone)


def validate_channel_update(channel: str, tier: str) -> str:
    """Return normalized channel or raise ValueError for illegal tier/channel pairs."""
    normalized = normalize_preferred_channel(channel)
    if normalized in ("whatsapp", "both") and tier not in PAID_TIERS:
        raise ValueError("WhatsApp digests require Starter plan or higher")
    return normalized
