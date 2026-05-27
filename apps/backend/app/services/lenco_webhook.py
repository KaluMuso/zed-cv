"""Lenco v2 webhook signature verification + event extraction.

Lenco signs each delivery with HMAC-SHA512 over the raw request body. The
signing key is derived from the API secret — not a separate webhook secret:

  webhook_hash_key = sha256(LENCO_API_KEY).hexdigest()
  expected_sig = hmac_sha512(webhook_hash_key, raw_body)

See https://lenco-api.readme.io/v2.0/reference/webhooks
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

logger = logging.getLogger(__name__)


def derive_lenco_webhook_hash_key(
    *,
    webhook_secret: str = "",
    api_key: str = "",
) -> str:
    """Return Lenco's webhook HMAC key (sha256 of API token)."""
    if webhook_secret:
        return webhook_secret.strip()
    if api_key:
        return hashlib.sha256(api_key.encode()).hexdigest()
    return ""


def verify_lenco_signature(
    raw_body: bytes,
    signature: str,
    *,
    webhook_secret: str = "",
    api_key: str = "",
) -> bool:
    """Verify X-Lenco-Signature using Lenco's sha256(api_key) derivation."""
    if not signature:
        return False

    webhook_hash_key = derive_lenco_webhook_hash_key(
        webhook_secret=webhook_secret,
        api_key=api_key,
    )
    if not webhook_hash_key:
        return False

    expected = hmac.new(
        webhook_hash_key.encode(),
        raw_body,
        hashlib.sha512,
    ).hexdigest()
    provided = signature.strip().lower()
    return hmac.compare_digest(expected, provided)


def mask_lenco_webhook_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact reference/amount for Sentry breadcrumbs (last 4 chars visible)."""
    if not isinstance(payload, dict):
        return {"payload_type": type(payload).__name__}

    data = payload.get("data")
    masked: dict[str, Any] = {"event": payload.get("event")}
    if not isinstance(data, dict):
        return masked

    ref = data.get("reference") or data.get("companyRef")
    if ref is not None:
        ref_s = str(ref)
        masked["reference"] = (
            f"***{ref_s[-4:]}" if len(ref_s) > 4 else "****"
        )

    amount = data.get("amount")
    if amount is not None:
        amount_s = str(amount)
        masked["amount"] = (
            f"***{amount_s[-4:]}" if len(amount_s) > 4 else "****"
        )

    status = data.get("status")
    if status is not None:
        masked["status"] = status

    return masked


def add_lenco_webhook_breadcrumb(
    payload: dict[str, Any],
    *,
    success: bool,
    detail: str,
) -> None:
    """Record a Sentry breadcrumb for every Lenco webhook delivery."""
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            category="lenco.webhook",
            message=detail,
            level="info" if success else "warning",
            data=mask_lenco_webhook_payload(payload),
        )
    except Exception:
        logger.debug("Sentry breadcrumb skipped for Lenco webhook", exc_info=True)


def extract_event_fields(payload: dict) -> dict[str, Any]:
    """Normalise the Lenco v2 webhook payload into the fields we care about.

    Primary events:
      - collection.successful — activate subscription (idempotent with verify-payment)
      - collection.failed — mark payment failed
      - collection.settled — settlement audit only (optional)
    """
    if not isinstance(payload, dict):
        return {}

    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    event = (payload.get("event") or "").lower()
    status = (data.get("status") or "").lower()

    is_paid = (
        event == "collection.successful"
        or status in {"successful", "success", "completed", "paid"}
        or event.endswith(".successful")
        or event.endswith(".success")
    )
    is_failed = (
        event == "collection.failed"
        or status in {"failed", "declined", "reversed"}
        or event.endswith(".failed")
    )
    is_settled = event == "collection.settled"

    return {
        "event": event or None,
        "company_ref": data.get("reference") or data.get("companyRef"),
        "lenco_ref": data.get("transactionRef") or data.get("id"),
        "status_raw": data.get("status"),
        "is_paid": is_paid,
        "is_failed": is_failed,
        "is_settled": is_settled,
        "amount_ngwee": _coerce_amount(data.get("amount")),
        "currency": (data.get("currency") or "ZMW").upper(),
        "raw": payload,
    }


def _coerce_amount(v: Any) -> int | None:
    """Coerce Lenco amount to int ngwee. Accepts int, float, or str."""
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(round(v))
    if isinstance(v, str):
        try:
            return int(round(float(v)))
        except (TypeError, ValueError):
            return None
    return None
