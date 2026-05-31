"""Email notifications via Resend.

All sends respect the user's `email_notifications_enabled` flag and silently
no-op when RESEND_API_KEY is unset, so this is safe to deploy before keys are
provisioned. The OTP fallback skips the per-user pref check (it's an auth
delivery channel, not a marketing message).

Daily digests prefer a published Resend template (`resend_daily_digest_template_id`)
with variables USER_NAME, MATCH_COUNT, MATCHES_HTML, APP_URL.
"""
import logging
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Optional

import resend

from app.core.config import get_settings
from app.core.deps import get_supabase
from app.services.email_delivery import (
    EMAIL_PROVIDER_UNAVAILABLE,
    EmailDeliveryError,
    classify_resend_error,
)

logger = logging.getLogger(__name__)

_WELCOME_TEMPLATE = (
    Path(__file__).resolve().parent.parent / "templates" / "emails" / "welcome.html"
)


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
            resend.Emails.send(payload, {"idempotency_key": idempotency_key})
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
            resend.Emails.send(payload, {"idempotency_key": idempotency_key})
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


def _render_welcome_html(first_name: str) -> str:
    raw = _WELCOME_TEMPLATE.read_text(encoding="utf-8")
    return raw.replace("{{first_name}}", escape(first_name))


async def send_welcome_email(
    user_id: str,
    full_name: str | None,
    email: str | None,
) -> None:
    """Post-signup welcome email. Sets users.welcome_email_sent on success."""
    if not email:
        return

    first_name = (full_name or "").split()[0] if (full_name or "").strip() else "there"
    html = _render_welcome_html(first_name)
    subject = "Welcome to ZedApply"
    ok = _send(
        email,
        subject,
        html,
        idempotency_key=f"welcome-email/{user_id}",
    )
    if not ok:
        logger.warning("welcome email send failed user_id=%s to=%s", user_id, email)
        return

    logger.info("welcome email sent user_id=%s to=%s", user_id, email)
    supabase = get_supabase()
    supabase.table("users").update({"welcome_email_sent": True}).eq("id", user_id).execute()


async def send_renewal_reminder_email(
    user_id: str,
    email: str,
    display_name: str,
    tier_label: str,
    renew_at: datetime,
) -> bool:
    """Remind a paid user their ZedApply plan renews soon."""
    if not email:
        return False
    settings = get_settings()
    first = (display_name or "").split()[0] if (display_name or "").strip() else "there"
    renew_str = renew_at.strftime("%d %B %Y") if isinstance(renew_at, datetime) else str(renew_at)
    pricing_url = f"{settings.app_url.rstrip('/')}/pricing"
    subject = f"Your {tier_label} plan renews on {renew_str}"
    html = (
        f"<p>Hi {escape(first)},</p>"
        f"<p>Your <strong>{escape(tier_label)}</strong> subscription on ZedApply "
        f"is scheduled to renew on <strong>{escape(renew_str)}</strong>.</p>"
        f"<p>No action is needed if you want to continue — your plan will renew automatically "
        f"via your saved payment method.</p>"
        f'<p><a href="{escape(pricing_url, quote=True)}">Manage your plan</a> in Settings if you '
        f"need to update billing.</p>"
        f"<p>— The ZedApply team</p>"
    )
    renew_date = renew_at.date().isoformat() if isinstance(renew_at, datetime) else str(renew_at)[:10]
    return _send(
        email,
        subject,
        html,
        idempotency_key=f"renewal-reminder/{user_id}/{renew_date}",
    )


def _digest_upcoming_html(upcoming: list[dict[str, Any]]) -> str:
    if not upcoming:
        return ""
    rows: list[str] = []
    for item in upcoming[:5]:
        title = escape(str(item.get("job_title") or "Role"))
        company = escape(str(item.get("job_company") or ""))
        when = escape(str(item.get("interview_date") or "soon"))
        rows.append(f"<li><strong>{title}</strong> at {company} — interview {when}</li>")
    return (
        "<h3>Upcoming interviews (next 48h)</h3>"
        f"<ul>{''.join(rows)}</ul>"
    )


async def send_daily_digest_email(
    user_id: str,
    email: str,
    display_name: str,
    matches: list[dict[str, Any]],
    supabase,
    *,
    digest_date: str,
    upcoming_interviews: list[dict[str, Any]] | None = None,
) -> bool:
    """Daily cron digest via Resend template (falls back to inline HTML)."""
    upcoming = upcoming_interviews or []
    if (not matches and not upcoming) or not email:
        return False
    enabled, resolved = await _resolve_recipient(user_id, supabase)
    if not enabled:
        return False
    to = email or resolved
    if not to:
        return False

    settings = get_settings()
    subject_parts: list[str] = []
    if upcoming:
        subject_parts.append(f"{len(upcoming)} upcoming interview(s)")
    if matches:
        subject_parts.append(f"{len(matches)} new job matches")
    subject = " · ".join(subject_parts) if subject_parts else "Your ZedApply digest"
    idempotency_key = f"daily-digest-email/{user_id}/{digest_date}"
    upcoming_html = _digest_upcoming_html(upcoming)
    template_id = (settings.resend_daily_digest_template_id or "").strip()
    if template_id:
        return _send_with_template(
            to,
            template_id=template_id,
            variables={
                "USER_NAME": display_name,
                "MATCH_COUNT": str(len(matches)),
                "MATCHES_HTML": _digest_matches_html(matches),
                "UPCOMING_INTERVIEWS_HTML": upcoming_html,
                "APP_URL": settings.app_url,
            },
            subject=subject,
            idempotency_key=idempotency_key,
        )

    matches_block = (
        f"<p>Here are your {len(matches)} new matches for today:</p>"
        f"{_digest_matches_html(matches)}"
        if matches
        else ""
    )
    html = f"""
    <h2>Good morning {escape(display_name)}!</h2>
    {upcoming_html}
    {matches_block}
    <p><a href="{settings.app_url}/applications">View application board</a> ·
    <a href="{settings.app_url}/matches">View all matches</a></p>
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


    return _send(email, f"Zed CV — {label} plan activated", html)


async def send_renewal_reminder_email(
    *,
    user_id: str,
    tier: str,
    tier_label: str,
    price_ngwee: int,
    period_end: datetime,
    supabase,
) -> bool:
    """Remind a paid user their billing period ends soon — manual renew on /pricing."""
    enabled, email = await _resolve_recipient(user_id, supabase)
    if not enabled or not email:
        return False

    settings = get_settings()
    end_label = period_end.strftime("%d %b %Y")
    kwacha = price_ngwee // 100
    period_end_date = period_end.date().isoformat()
    idempotency_key = f"renewal-reminder-{user_id}-{period_end_date}"

    html = f"""
    <h2>Your Zed Apply plan ends soon</h2>
    <p>Hi,</p>
    <p>Your <strong>{tier_label}</strong> plan is scheduled to end on
    <strong>{end_label}</strong>.</p>
    <p>Zed Apply does not auto-charge mobile money — to keep your paid benefits
    (extra matches, cover letters, interview prep), renew on the pricing page before
    your period ends.</p>
    <p>Renewal price: <strong>K{kwacha:,}/month</strong></p>
    <p><a href="{settings.app_url}/pricing">Renew on Zed Apply</a> ·
    <a href="{settings.app_url}/settings/billing">Billing settings</a></p>
    <p style="font-size:12px;color:#666;">Already cancelled? You can ignore this email —
    your account will revert to the Free plan when the period ends.</p>
    """
    return _send(
        email,
        f"Zed Apply — renew your {tier_label} plan by {end_label}",
        html,
        idempotency_key=idempotency_key,
    )


async def send_invoice_email(invoice: dict, supabase) -> bool:
    """Email HTML invoice/receipt for a completed payment."""
    user_id = invoice.get("user_id")
    if not user_id:
        return False
    enabled, email = await _resolve_recipient(user_id, supabase)
    if not enabled or not email:
        return False

    from app.services.invoice import render_invoice_html

    html = render_invoice_html(invoice)
    inv_no = invoice.get("invoice_number", "receipt")
    tier = invoice.get("tier_label", "plan")
    kwacha = int(invoice.get("amount_kwacha") or 0)
    return _send(
        email,
        f"Zed Apply invoice {inv_no} — {tier} (K{kwacha})",
        html,
    )


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


async def send_employer_consent_email(
    email: str,
    *,
    employer_name: str,
    message_snippet: str,
) -> bool:
    """Mirror WhatsApp consent prompt for employer contact requests."""
    if not _api_ready() or not email:
        return False
    settings = get_settings()
    html = f"""
    <h2>Employer contact request</h2>
    <p><strong>{escape(employer_name)}</strong> wants to reach you via Zed Apply:</p>
    <blockquote>{escape(message_snippet)}</blockquote>
    <p>Reply <strong>YES</strong> on WhatsApp to share your phone and email, or <strong>NO</strong> to decline.</p>
  """
    return _send(email, f"{employer_name} wants to contact you — Zed Apply", html)


async def send_employer_invite_email(
    email: str,
    *,
    company_name: str,
    invite_url: str,
) -> bool:
    if not _api_ready():
        logger.warning("Resend not configured — skipping employer invite email")
        return False
    html = f"""
    <h2>Join {escape(company_name)} on Zed Apply Employer</h2>
    <p>You have been invited to collaborate on candidate search and outreach.</p>
    <p><a href="{escape(invite_url, quote=True)}">Accept invitation</a></p>
    """
    return _send(email, f"Invitation — {company_name} on Zed Apply", html)
