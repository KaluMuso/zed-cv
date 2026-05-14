"""DPO Pay webhook signature / token verification.

Mirrors the layout of lenco_webhook.py so the two payment providers
follow a parallel pattern. DPO's authenticity model differs from
Lenco's though:

- Lenco signs each webhook delivery with HMAC-SHA512 over the raw body
  (header `x-lenco-signature`). Symmetric shared secret.
- DPO doesn't (currently) emit an HMAC signature header. Authenticity
  is established by:
    1. The CompanyToken embedded in the XML body — a shared secret
       configured both in our env (`settings.dpo_pay_company_token`)
       and in the DPO merchant dashboard. An attacker who doesn't
       have it cannot forge a payload.
    2. A callback to DPO's `verifyToken` API endpoint with the
       TransactionToken from the body — the API only returns "paid"
       for transactions DPO actually processed. This is the
       defense-in-depth layer.
- If/when DPO adds an HMAC signature header, the `verify_hmac_signature`
  helper below will accept it via `settings.dpo_pay_webhook_secret`.
  Currently that env var is empty by default so the HMAC path is opt-in.

This module is intentionally kept separate from the route handler so
the cryptographic verification logic can be unit-tested without
spinning up FastAPI.
"""
from __future__ import annotations

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def verify_company_token(parsed_company_token: str, expected_token: str) -> bool:
    """Constant-time compare of the webhook's CompanyToken vs our configured one.

    The CompanyToken is the shared secret between us and DPO. DPO embeds
    our merchant token in every webhook body. A request without the
    matching token is either misrouted (different tenant) or forged.

    Args:
        parsed_company_token: Value extracted from the XML body's
            <CompanyToken>...</CompanyToken> element.
        expected_token: `settings.dpo_pay_company_token` — our configured
            merchant token.

    Returns:
        True iff the tokens match exactly (constant-time compare to
        prevent timing-based extraction). Empty / missing either side
        returns False — never short-circuits to True.
    """
    if not parsed_company_token or not expected_token:
        return False
    return hmac.compare_digest(
        parsed_company_token.strip().encode("utf-8"),
        expected_token.strip().encode("utf-8"),
    )


def verify_hmac_signature(
    raw_body: bytes,
    provided_signature: str,
    webhook_secret: str,
) -> bool:
    """Optional HMAC-SHA256 verification for DPO webhook deliveries.

    DPO doesn't currently sign webhooks, so this is a future-proof
    helper. If DPO begins emitting a signature header (e.g.
    `x-dpo-signature`), the route will pass the value here and we'll
    verify against `settings.dpo_pay_webhook_secret`. Until then,
    `webhook_secret` is empty by default and this function always
    returns False — callers should fall back to `verify_company_token`.

    Args:
        raw_body: Raw request body bytes (NOT a parsed dict). The hash
            is computed over the bytes-as-received; any reformatting
            breaks the comparison.
        provided_signature: Hex digest from whatever signature header
            DPO settles on.
        webhook_secret: `settings.dpo_pay_webhook_secret`. Empty by
            default = HMAC verification disabled.

    Returns:
        True iff the secret is configured AND the signature matches.
    """
    if not provided_signature or not webhook_secret:
        return False

    expected = hmac.new(
        webhook_secret.strip().encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, provided_signature.strip().lower())
