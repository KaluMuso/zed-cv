"""Structured email delivery failures for auth OTP and admin health checks."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from email.utils import parseaddr
from typing import Any

logger = logging.getLogger(__name__)

# Machine-readable codes returned in RFC 7807 `detail` for OTP 503s.
EMAIL_PROVIDER_UNAVAILABLE = "email_provider_unavailable"
EMAIL_SEND_FAILED = "email_send_failed"
EMAIL_DOMAIN_UNVERIFIED = "email_domain_unverified"
EMAIL_TEMPLATE_MISSING = "email_template_missing"


class EmailDeliveryError(Exception):
    """Resend could not deliver (OTP path fails loud instead of returning False)."""

    def __init__(self, code: str, *, log_message: str | None = None) -> None:
        self.code = code
        self.log_message = log_message or code
        super().__init__(self.log_message)


def classify_resend_error(exc: Exception) -> str:
    """Map Resend API errors to stable problem codes for Sentry/admin."""
    msg = str(exc).lower()
    if "template" in msg and ("not found" in msg or "missing" in msg):
        return EMAIL_TEMPLATE_MISSING
    if "domain" in msg and ("verify" in msg or "not verified" in msg):
        return EMAIL_DOMAIN_UNVERIFIED
    if "domain" in msg or "from" in msg:
        return EMAIL_DOMAIN_UNVERIFIED
    return EMAIL_SEND_FAILED


def from_address_domain(from_email: str) -> str | None:
    """Extract domain from `Name <addr@domain.com>` or bare address."""
    _, addr = parseaddr(from_email.strip())
    if "@" not in addr:
        return None
    return addr.rsplit("@", 1)[-1].lower()


@dataclass
class ResendHealthReport:
    status: str  # ok | degraded | error
    code: str | None
    message: str
    api_key_configured: bool
    from_email: str
    from_domain: str | None
    domain_verified: bool | None
    domains_listed: int | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "status": self.status,
            "message": self.message,
            "api_key_configured": self.api_key_configured,
            "from_email": self.from_email,
            "from_domain": self.from_domain,
            "domain_verified": self.domain_verified,
        }
        if self.code:
            out["code"] = self.code
        if self.domains_listed is not None:
            out["domains_listed"] = self.domains_listed
        return out


def check_resend_health(
    *,
    resend_api_key: str,
    resend_from_email: str,
) -> ResendHealthReport:
    """Ping Resend (domains list) without sending mail — admin diagnostics."""
    from_domain = from_address_domain(resend_from_email)
    if not resend_api_key:
        return ResendHealthReport(
            status="error",
            code=EMAIL_PROVIDER_UNAVAILABLE,
            message="RESEND_API_KEY is not set",
            api_key_configured=False,
            from_email=resend_from_email,
            from_domain=from_domain,
            domain_verified=None,
        )

    try:
        import resend

        resend.api_key = resend_api_key
        listed = resend.Domains.list()
        rows = getattr(listed, "data", None) or listed
        if not isinstance(rows, list):
            rows = list(rows) if rows else []
        domain_verified: bool | None = None
        if from_domain:
            for row in rows:
                name = (
                    row.get("name")
                    if isinstance(row, dict)
                    else getattr(row, "name", None)
                )
                status = (
                    row.get("status")
                    if isinstance(row, dict)
                    else getattr(row, "status", None)
                )
                if name and str(name).lower() == from_domain:
                    domain_verified = str(status).lower() == "verified"
                    break
            if domain_verified is None and rows:
                domain_verified = False

        if domain_verified is False:
            return ResendHealthReport(
                status="degraded",
                code=EMAIL_DOMAIN_UNVERIFIED,
                message=f"Sender domain {from_domain!r} is not verified in Resend",
                api_key_configured=True,
                from_email=resend_from_email,
                from_domain=from_domain,
                domain_verified=False,
                domains_listed=len(rows),
            )

        return ResendHealthReport(
            status="ok",
            code=None,
            message="Resend API reachable; sender domain looks healthy",
            api_key_configured=True,
            from_email=resend_from_email,
            from_domain=from_domain,
            domain_verified=domain_verified,
            domains_listed=len(rows),
        )
    except Exception as exc:
        logger.warning("Resend health check failed: %s", exc)
        return ResendHealthReport(
            status="error",
            code=classify_resend_error(exc),
            message=str(exc)[:300],
            api_key_configured=True,
            from_email=resend_from_email,
            from_domain=from_domain,
            domain_verified=None,
        )
