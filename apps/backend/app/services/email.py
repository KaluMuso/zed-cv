"""Email notifications via Resend.

All sends respect the user's `email_notifications_enabled` flag and silently
no-op when RESEND_API_KEY is unset, so this is safe to deploy before keys are
provisioned. The OTP fallback skips the per-user pref check (it's an auth
delivery channel, not a marketing message).

Daily digests prefer a published Resend template (`resend_daily_digest_template_id`)
with variables USER_NAME, MATCH_COUNT, MATCHES_HTML, APP_URL.
"""
import logging
from html import escape
from typing import Any, Optional

import resend

from app.core.config import get_settings
from app.services.email_delivery import (
    EMAIL_PROVIDER_UNAVAILABLE,
    EmailDeliveryError,
    classify_resend_error,
)

logger = logging.getLogger(__name__)


def _api_ready() -> bool:
    settings = get_settings()
    if not settings.resend_api_key:
        return False
    resend.api_key = settings.resend_api_key
    return True


async def _resolve_recipient(user_id: str, supabase) -> tuple[bool, Optional[str]]:
    """Return (notifications_enabled, email) for a user."""
    res = (
        supabase.table("users")
        .select("email, email_notifications_enabled")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not res.data:
        return False, None
    enabled = res.data.get("email_notifications_enabled", True)
    email = res.data.get("email")
    return bool(enabled and email), email


def _send(to: str, subject: str, html: str, *, idempotency_key: str | None = None) -> bool:
    if not _api_ready():
        logger.info(f"[email skipped: no api key] to={to} subject={subject}")
        return False
    settings = get_settings()
    payload: dict[str, object] = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    try:
        if idempotency_key:
            resend.Emails.send(payload, idempotency_key=idempotency_key)
        else:
            resend.Emails.send(payload)
        return True
    except Exception as e:
        logger.error(f"resend send failed: to={to} subject={subject} err={e}")
        return False


def _send_with_template(
    to: str,
    *,
    template_id: str,
    variables: dict[str, str],
    subject: str,
    idempotency_key: str | None = None,
) -> bool:
    if not _api_ready():
        logger.info(f"[email skipped: no api key] to={to} template={template_id}")
        return False
    settings = get_settings()
    payload: dict[str, object] = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "template": {"id": template_id, "variables": variables},
    }
    try:
        if idempotency_key:
            resend.Emails.send(payload, idempotency_key=idempotency_key)
        else:
            resend.Emails.send(payload)
        return True
    except Exception as e:
        logger.error(
            "resend template send failed: to=%s template=%s err=%s",
            to,
            template_id,
            e,
        )
        return False


def _digest_matches_html(matches: list[dict[str, Any]]) -> str:
    settings = get_settings()
    rows: list[str] = []
    for m in matches[:5]:
        title = escape(str(m.get("job_title") or "Job"))
        company = escape(str(m.get("job_company") or ""))
        score = int(round(float(m.get("final_score") or m.get("score") or 0)))
        href = escape(str(m.get("apply_url") or settings.app_url), quote=True)
        rows.append(
            f'<li><a href="{href}"><strong>{title}</strong></a> at {company} — {score}% match</li>'
        )
    return f"<ol>{''.join(rows)}</ol>"


async def send_welcome_email(user_id: str, supabase) -> bool:
    enabled, email = await _resolve_recipient(user_id, supabase)
    if not enabled or not email:
        return False
    settings = get_settings()
    html = f"""
    <h2>Welcome to Zed CV</h2>
    <p>Your CV is in. Our AI will start matching you to jobs across Zambia within minutes.</p>
    <p>What's next:</p>
    <ul>
      <li>Wait for your first match digest (usually within 24 hours).</li>
      <li>Reply <strong>matches</strong> on WhatsApp to see top matches anytime.</li>
      <li>Visit <a href="{settings.app_url}/matches">your dashboard</a> for full match details.</li>
    </ul>
    <p>— The Zed CV team</p>
    """
    return _send(email, "Welcome to Zed CV", html)


async def send_daily_digest_email(
    user_id: str,
    email: str,
    display_name: str,
    matches: list[dict[str, Any]],
    supabase,
    *,
    digest_date: str,
) -> bool:
    """Daily cron digest via Resend template (falls back to inline HTML)."""
    if not matches or not email:
        return False
    enabled, resolved = await _resolve_recipient(user_id, supabase)
    if not enabled:
        return False
    to = email or resolved
    if not to:
        return False

    settings = get_settings()
    subject = f"{len(matches)} new job matches for you"
    idempotency_key = f"daily-digest-email/{user_id}/{digest_date}"
    template_id = (settings.resend_daily_digest_template_id or "").strip()
    if template_id:
        return _send_with_template(
            to,
            template_id=template_id,
            variables={
                "USER_NAME": display_name,
                "MATCH_COUNT": str(len(matches)),
                "MATCHES_HTML": _digest_matches_html(matches),
                "APP_URL": settings.app_url,
            },
            subject=subject,
            idempotency_key=idempotency_key,
        )

    html = f"""
    <h2>Good morning {escape(display_name)}!</h2>
    <p>Here are your {len(matches)} new matches for today:</p>
    {_digest_matches_html(matches)}
    <p><a href="{settings.app_url}/matches">View all matches</a></p>
    """
    return _send(to, subject, html, idempotency_key=idempotency_key)


async def send_match_digest_email(user_id: str, matches: list[dict], supabase) -> bool:
    if not matches:
        return False
    enabled, email = await _resolve_recipient(user_id, supabase)
    if not enabled or not email:
        return False
    settings = get_settings()
    rows = []
    for m in matches[:5]:
        job = m.get("jobs") or {}
        title = escape(str(m.get("title") or job.get("title") or "Job"))
        company = escape(str(m.get("company") or job.get("company") or ""))
        score = int(round(m.get("score", 0)))
        href = job.get("apply_url") or job.get("source_url") or settings.app_url
        rows.append(
            f'<li><a href="{escape(str(href), quote=True)}"><strong>{title}</strong></a>'
            f" at {company} — {score}% match</li>"
        )
    html = f"""
    <h2>Your latest job matches</h2>
    <p>We found {len(matches)} new matches for you:</p>
    <ol>{''.join(rows)}</ol>
    <p><a href="{settings.app_url}/matches">View all matches</a></p>
    """
    return _send(email, f"{len(matches)} new job matches", html)


async def send_payment_confirmation_email(
    user_id: str, tier: str, amount_ngwee: int, supabase
) -> bool:
    enabled, email = await _resolve_recipient(user_id, supabase)
    if not enabled or not email:
        return False
    settings = get_settings()
    label = {
        "starter": "Starter",
        "professional": "Professional",
        "super_standard": "Super Standard",
    }.get(tier, tier)
    html = f"""
    <h2>Payment confirmed</h2>
    <p>Thanks — we received your payment of <strong>K{amount_ngwee // 100}</strong>.</p>
    <p>Your account is now on the <strong>{label}</strong> plan.</p>
    <p><a href="{settings.app_url}/matches">Go to your dashboard</a></p>
    """
    return _send(email, f"Zed CV — {label} plan activated", html)


async def send_otp_email(email: str, code: str) -> None:
    """Email OTP delivery. Raises EmailDeliveryError on failure (auth returns 503).

    Bypasses email_notifications_enabled — this is an auth channel, not marketing.
    """
    if not email:
        raise EmailDeliveryError(
            EMAIL_PROVIDER_UNAVAILABLE,
            log_message="OTP email requested without recipient address",
        )
    if not _api_ready():
        raise EmailDeliveryError(
            EMAIL_PROVIDER_UNAVAILABLE,
            log_message="RESEND_API_KEY not configured",
        )
    settings = get_settings()
    html = f"""
    <h2>Your Zed CV verification code</h2>
    <p style="font-size:32px;letter-spacing:8px;font-family:monospace;"><strong>{code}</strong></p>
    <p>This code expires in 5 minutes. If you didn't request it, ignore this email.</p>
    """
    payload: dict[str, object] = {
        "from": settings.resend_from_email,
        "to": [email],
        "subject": "Your Zed CV verification code",
        "html": html,
    }
    try:
        resend.Emails.send(payload)
    except Exception as exc:
        code_err = classify_resend_error(exc)
        logger.error(
            "resend OTP send failed: to=%s code=%s err=%s",
            email,
            code_err,
            exc,
        )
        raise EmailDeliveryError(code_err, log_message=str(exc)) from exc
