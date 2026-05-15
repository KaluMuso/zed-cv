"""Contact-form endpoint (task #65).

Receives the /contact form, delivers it as an email to the operator
inbox via Resend, and rate-limits at 2/hour per IP so a single visitor
can't flood the founder mailbox.

Public, auth-free — it has to be, since the form lives on a marketing
page. The 2/hour cap + body-length limits keep abuse bounded; anything
more aggressive belongs behind a CAPTCHA (separate slice).
"""
# NOTE: deliberately NOT using `from __future__ import annotations` here.
# FastAPI inspects parameter types at runtime to wire request-body vs
# query-param vs dependency. Stringified annotations turn into ForwardRefs
# that FastAPI can't resolve, and ContactRequest ends up parsed as a
# query parameter — every POST fails at validation setup.

import html
import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["Contact"])


# E.164 Zambian phone shape — same regex used elsewhere in the app
# (auth flow, schemas). Optional on the contact form, so we only
# validate it when the user provided a value.
_PHONE_RE = re.compile(r"^\+260\d{9}$")


class ContactRequest(BaseModel):
    """Body for POST /api/v1/contact."""

    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    # Optional. When present, must be the platform's standard +260 shape.
    phone: Optional[str] = Field(None, max_length=20)
    # 5,000 chars is generous for a contact form and bounds the email
    # body we'll relay. Anything longer is almost certainly junk.
    message: str = Field(..., min_length=10, max_length=5000)


class ContactResponse(BaseModel):
    success: bool
    message: str


def _render_email_html(req: ContactRequest) -> str:
    """Render the relay email body.

    All user-supplied strings are HTML-escaped before interpolation so
    a hostile message can't smuggle <script> or <img onerror=> into the
    operator inbox. Newlines in the message become <br> so the relay
    preserves the user's formatting.
    """
    name_esc = html.escape(req.name)
    email_esc = html.escape(req.email)
    phone_esc = html.escape(req.phone) if req.phone else "—"
    msg_esc = html.escape(req.message).replace("\n", "<br>")
    return f"""
    <h2>New /contact submission</h2>
    <p><strong>From:</strong> {name_esc} &lt;{email_esc}&gt;</p>
    <p><strong>Phone:</strong> {phone_esc}</p>
    <hr>
    <p>{msg_esc}</p>
    """


@router.post("", response_model=ContactResponse)
@limiter.limit("2/hour")
async def submit_contact(
    request: Request,
    body: ContactRequest,
    settings: Settings = Depends(get_settings),
) -> ContactResponse:
    """Relay a contact-form submission to the operator inbox.

    Returns 200 on success, 422 on validation, 429 on rate-limit, 503
    if Resend isn't configured (fail loud rather than silently dropping
    user messages on the floor).
    """
    # Validate phone format when provided. EmailStr already validates email.
    if body.phone and not _PHONE_RE.match(body.phone):
        raise HTTPException(
            status_code=422,
            detail=(
                "Phone must be in +260XXXXXXXXX format if provided. "
                "Leave it blank if you'd rather skip it."
            ),
        )

    # Resend dispatch. Imported + configured lazily so a missing API
    # key returns 503 here rather than crashing module import — the
    # rest of the app should keep working even when contact is down.
    if not settings.resend_api_key:
        logger.warning(
            "contact form submission could not be relayed — RESEND_API_KEY not set"
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Our email relay isn't configured right now. Please reach us "
                f"directly at {settings.contact_email}."
            ),
        )

    try:
        import resend

        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [settings.contact_email],
                # Reply-To set to the submitter so the operator can hit
                # Reply in Gmail and land in the user's inbox, not the
                # noreply mailbox.
                "reply_to": body.email,
                "subject": f"[ZedApply contact] {body.name}",
                "html": _render_email_html(body),
            }
        )
    except Exception as exc:  # noqa: BLE001
        # Don't echo the upstream error verbatim — could leak API
        # response shape / keys / internal addresses. Log it for ops
        # and return a generic 503 so the user can try again later.
        logger.error("Resend relay failed for /contact: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                "Your message couldn't be sent right now. Please try again "
                "in a few minutes."
            ),
        )

    return ContactResponse(
        success=True,
        message="Thanks — your message is on its way. We'll be in touch.",
    )
