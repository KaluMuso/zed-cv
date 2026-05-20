"""Email notifications via Resend.

All sends respect the user's `email_notifications_enabled` flag and silently
no-op when RESEND_API_KEY is unset, so this is safe to deploy before keys are
provisioned. The OTP fallback skips the per-user pref check (it's an auth
delivery channel, not a marketing message).
"""
import logging
from html import escape
from typing import Optional

import resend

from app.core.config import get_settings

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


def _send(to: str, subject: str, html: str) -> bool:
    if not _api_ready():
        logger.info(f"[email skipped: no api key] to={to} subject={subject}")
        return False
    settings = get_settings()
    try:
        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        logger.error(f"resend send failed: to={to} subject={subject} err={e}")
        return False


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


async def send_otp_email(email: str, code: str) -> bool:
    """Email OTP fallback. Callable from auth flow when WhatsApp delivery fails.

    Bypasses email_notifications_enabled — this is an auth channel, not marketing.
    """
    if not email:
        return False
    html = f"""
    <h2>Your Zed CV verification code</h2>
    <p style="font-size:32px;letter-spacing:8px;font-family:monospace;"><strong>{code}</strong></p>
    <p>This code expires in 5 minutes. If you didn't request it, ignore this email.</p>
    """
    return _send(email, "Your Zed CV verification code", html)
