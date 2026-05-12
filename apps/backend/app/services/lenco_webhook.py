"""Lenco v2 webhook signature verification + event processing.

Kept as a separate module so the webhook route in api/v1/webhooks.py stays
small (just transport handling) and the signature/idempotency logic can
be unit-tested without spinning up FastAPI.

Lenco v2 signs each webhook delivery with HMAC-SHA512 over the raw request
body. The signing key is one of:
  1. A dedicated webhook secret you generate in the Lenco dashboard
     (Lenco Pay → Webhooks → Generate signing secret), passed to us via
     `settings.lenco_webhook_secret`.
  2. Your API Secret Key (`settings.lenco_api_key`) — Lenco uses this by
     default when no dedicated secret is provisioned.

`verify_signature` accepts either. Constant-time compare prevents timing
side-channels. We never log or echo the signing key.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

logger = logging.getLogger(__name__)


def verify_signature(
    raw_body: bytes,
    provided_signature: str,
    webhook_secret: str = "",
    api_key: str = "",
) -> bool:
    """Verify a Lenco webhook's HMAC-SHA512 signature.

    Args:
        raw_body: The raw request body bytes (NOT a parsed dict). Lenco
            signs the bytes-as-received; any reformatting breaks the hash.
        provided_signature: Hex digest from the `x-lenco-signature` header.
        webhook_secret: Dedicated webhook secret if configured. Tried first.
        api_key: API Secret Key. Used as fallback when webhook_secret is empty.

    Returns:
        True iff the signature matches at least one of the two keys.

    Both keys are tried (when both are set) so a deployment that's mid-
    migration from API-key-signing to dedicated-secret-signing doesn't drop
    deliveries. Failure to verify is a soft False — never raises.
    """
    if not provided_signature:
        return False

    candidates = [k.strip() for k in (webhook_secret, api_key) if k and k.strip()]
    if not candidates:
        logger.error("verify_signature: no signing keys configured")
        return False

    # Normalise the provided signature: Lenco sends lowercase hex, but be
    # generous about whitespace and case.
    provided_norm = provided_signature.strip().lower()

    for key in candidates:
        expected = hmac.new(
            key.encode("utf-8"),
            raw_body,
            hashlib.sha512,
        ).hexdigest()
        if hmac.compare_digest(expected, provided_norm):
            return True

    return False


def extract_event_fields(payload: dict) -> dict[str, Any]:
    """Normalise the Lenco v2 webhook payload into the fields we care about.

    Lenco v2 events come in a few shapes depending on the source: collection
    webhooks, payment-status webhooks, transfer notifications. We extract
    the union of fields that map to our `payments` table and return a tidy
    dict. Missing fields are None — callers should always null-check.

    Expected shape (v2, observed in Lenco docs as of 2026-05):
      {
        "event": "collection.successful" | "payment.successful" | ...,
        "data": {
          "reference": "ZEDCV-xxxx" (our company_ref, set when initiating),
          "transactionRef": "LEN-xxxx" (Lenco's own ref),
          "status": "successful" | "failed" | "pending",
          "amount": 12500 (in ngwee — confirm at integration time),
          "currency": "ZMW",
          ...
        }
      }

    If Lenco's actual shape diverges (the API doc URL is the source of
    truth), update this single function — the caller doesn't need to know
    the wire format.
    """
    if not isinstance(payload, dict):
        return {}

    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    event = (payload.get("event") or "").lower()
    status = (data.get("status") or "").lower()

    # Treat "successful" as the canonical paid signal. Lenco uses
    # "successful" for collections; "completed" for some transfer events.
    # Cast a wide net so we don't miss a paid status because of casing.
    is_paid = status in {"successful", "success", "completed", "paid"} or (
        event.endswith(".successful") or event.endswith(".success")
    )
    is_failed = status in {"failed", "declined", "reversed"} or event.endswith(".failed")

    # Reference fields. Prefer `reference` (our company-supplied ref when
    # initiating the payment) because that's how we look up the row in
    # `payments`; transactionRef is Lenco's internal ID and only useful
    # for support tickets.
    return {
        "event": event or None,
        "company_ref": data.get("reference") or data.get("companyRef"),
        "lenco_ref": data.get("transactionRef") or data.get("id"),
        "status_raw": data.get("status"),
        "is_paid": is_paid,
        "is_failed": is_failed,
        # Lenco v2 amounts are in the smallest currency unit (ngwee for ZMW)
        # per their docs. Be defensive — if it's a float decimal we coerce
        # to int ngwee.
        "amount_ngwee": _coerce_amount(data.get("amount")),
        "currency": (data.get("currency") or "ZMW").upper(),
        # Pass the raw payload through for storage in payments.webhook_data
        # so any field we DON'T extract is still recoverable for audits.
        "raw": payload,
    }


def _coerce_amount(v: Any) -> int | None:
    """Coerce Lenco's amount field to int ngwee. Accepts int, float, or str."""
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
