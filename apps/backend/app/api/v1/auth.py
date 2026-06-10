"""Auth routes — OTP via email/WhatsApp and trusted-device login."""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status

from app.core.errors import ProblemHTTPException
from app.services.email_delivery import EmailDeliveryError
from jose import jwt

from app.core.config import Settings, get_settings
from app.core.deps import get_supabase
from app.core.rate_limit import limiter
from app.schemas.auth import (
    AuthTokens,
    LoginRequest,
    OTPRequest,
    OTPRequestResponse,
    OTPVerify,
)
from app.services.email import send_welcome_email
from app.services.referral import attach_referral_on_signup, generate_referral_code
from app.services.otp import (
    default_otp_channel_for_tier,
    generate_otp_code,
    hash_otp_code,
    is_device_trusted,
    lookup_user_auth_context,
    otp_delivery_message,
    register_trusted_device,
    resolve_otp_channel,
    send_otp,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
log = logging.getLogger(__name__)

# Back-compat for tests importing _hash_otp from this module.
_hash_otp = hash_otp_code


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _device_label(request: Request) -> str | None:
    ua = request.headers.get("user-agent", "")
    return (ua[:120] + "…") if len(ua) > 120 else (ua or None)


def _issue_tokens(user_id: str, phone: str, settings: Settings) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    access_token = jwt.encode(
        {
            "sub": user_id,
            "phone": phone,
            "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
            "iat": now,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    refresh_token = jwt.encode(
        {
            "sub": user_id,
            "type": "refresh",
            "exp": now + timedelta(days=settings.refresh_token_expire_days),
            "iat": now,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return access_token, refresh_token


@router.post("/login", response_model=AuthTokens)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    settings: Settings = Depends(get_settings),
    supabase=Depends(get_supabase),
    x_device_token: str | None = Header(None, alias="X-Device-Token"),
):
    """Trusted-device login: skip OTP when X-Device-Token matches a valid row."""
    ctx = lookup_user_auth_context(body.phone, supabase)
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP required",
        )
    if not is_device_trusted(ctx["id"], x_device_token, supabase):
        tier = ctx.get("tier")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP required",
            headers={
                "X-Needs-Otp": "1",
                "X-User-Tier": tier or "free",
                "X-Default-Otp-Channel": resolve_otp_channel(
                    user_row=ctx,
                    tier=tier,
                    requested_channel=None,
                ),
            },
        )
    access, refresh = _issue_tokens(ctx["id"], body.phone, settings)
    return AuthTokens(
        access_token=access,
        refresh_token=refresh,
        user_id=ctx["id"],
        trusted_device_login=True,
    )


@router.post("/otp/request", response_model=OTPRequestResponse)
@limiter.limit("3/minute")
async def request_otp(
    request: Request,
    body: OTPRequest,
    settings: Settings = Depends(get_settings),
    supabase=Depends(get_supabase),
):
    recent = (
        supabase.table("otp_codes")
        .select("created_at")
        .eq("phone", body.phone)
        .gte(
            "created_at",
            (
                datetime.now(timezone.utc)
                - timedelta(seconds=settings.otp_cooldown_seconds)
            ).isoformat(),
        )
        .execute()
    )
    if recent.data:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Wait {settings.otp_cooldown_seconds}s between OTP requests",
        )

    ctx = lookup_user_auth_context(body.phone, supabase)
    tier = ctx.get("tier") if ctx else None
    channel = resolve_otp_channel(
        user_row=ctx,
        tier=tier,
        requested_channel=body.channel,
    )
    email = (ctx or {}).get("email")
    if channel in ("email", "both") and not email:
        if body.channel == "email":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Add an email to your profile before using email OTP",
            )
        channel = "whatsapp"

    code = generate_otp_code(settings)
    code_hash = hash_otp_code(code, body.phone, settings.jwt_secret)
    supabase.table("otp_codes").insert({
        "phone": body.phone,
        "code": code_hash,
        "expires_at": (
            datetime.now(timezone.utc)
            + timedelta(minutes=settings.otp_expire_minutes)
        ).isoformat(),
    }).execute()

    try:
        await send_otp(phone=body.phone, code=code, channel=channel, email=email)
    except EmailDeliveryError as exc:
        log.error(
            "Email OTP delivery failed for %s: code=%s %s",
            body.phone,
            exc.code,
            exc.log_message,
        )
        raise ProblemHTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            code=exc.code,
            user_message=(
                "Email delivery is temporarily unavailable — please try WhatsApp instead."
            ),
        ) from exc
    except Exception as exc:
        log.error("OTP delivery failed for %s via %s: %s", body.phone, channel, exc)
        if channel in ("whatsapp", "both"):
            raise ProblemHTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                code="whatsapp_delivery_unavailable",
                user_message=(
                    "WhatsApp delivery is temporarily unavailable. "
                    "Please try again in a minute or use email OTP."
                ),
            ) from exc
        raise ProblemHTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            code="otp_delivery_unavailable",
            user_message="OTP delivery is temporarily unavailable. Please try again.",
        ) from exc

    default_ch = default_otp_channel_for_tier(tier)
    return OTPRequestResponse(
        message=otp_delivery_message(channel),
        tier=tier,
        default_channel=default_ch,
    )


@router.post("/otp/verify", response_model=AuthTokens)
@limiter.limit("10/minute")
async def verify_otp(
    request: Request,
    body: OTPVerify,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    supabase=Depends(get_supabase),
):
    now_iso = datetime.now(timezone.utc).isoformat()
    body_code_hash = hash_otp_code(body.code, body.phone, settings.jwt_secret)
    result = (
        supabase.table("otp_codes")
        .select("*")
        .eq("phone", body.phone)
        .eq("code", body_code_hash)
        .eq("verified", False)
        .gte("expires_at", now_iso)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        latest = (
            supabase.table("otp_codes")
            .select("id, attempts")
            .eq("phone", body.phone)
            .eq("verified", False)
            .gte("expires_at", now_iso)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if latest.data:
            row = latest.data[0]
            supabase.table("otp_codes").update({
                "attempts": (row.get("attempts") or 0) + 1,
            }).eq("id", row["id"]).execute()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    otp = result.data[0]
    if otp["attempts"] >= settings.max_otp_attempts:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Too many attempts. Request a new OTP.",
        )

    # PR #315: include whatsapp_number so we can detect and patch missing
    # values on existing-user verify. See the defensive UPDATE below.
    user_result = (
        supabase.table("users")
        .select(
            "id, role, email, full_name, welcome_email_sent, "
            "whatsapp_number, whatsapp_verified"
        )
        .eq("phone", body.phone)
        .limit(1)
        .execute()
    )
    device_token: str | None = None
    newly_created = False
    user_row: dict = {}

    if user_result.data:
        user_row = user_result.data[0]
        user_id = user_row["id"]
        supabase.table("otp_codes").update({"verified": True}).eq("id", otp["id"]).execute()
        if body.email and not user_row.get("email"):
            supabase.table("users").update({"email": str(body.email)}).eq("id", user_id).execute()
            user_row["email"] = str(body.email)

        # PR #315: belt-and-braces — if an existing user has never had their
        # WhatsApp eligibility flipped on (whatsapp_number IS NULL on the
        # users row), set it now using the phone they just OTP-verified.
        # This catches anyone who signed up after the 2026-06-10 SQL backfill
        # but before this PR deployed. Idempotent: if whatsapp_number is
        # already set, the WHERE doesn't match and the UPDATE is a no-op.
        # Always-safe because completing OTP IS the WhatsApp verification in
        # the Zambian market (phone == WhatsApp universally).
        if not user_row.get("whatsapp_number"):
            supabase.table("users").update({
                "whatsapp_number": body.phone,
                "whatsapp_verified": True,
            }).eq("id", user_id).execute()
            user_row["whatsapp_number"] = body.phone
            user_row["whatsapp_verified"] = True
    else:
        newly_created = True
        if body.consent_accepted is not True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Consent required",
            )
        if not body.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required to create an account",
            )
        supabase.table("otp_codes").update({"verified": True}).eq("id", otp["id"]).execute()
        role = (
            "superadmin"
            if (settings.superadmin_phone and body.phone == settings.superadmin_phone)
            else "user"
        )
        otp_pref = "email"
        referral_code = generate_referral_code(supabase)
        new_user = supabase.table("users").insert({
            "phone": body.phone,
            "email": str(body.email),
            "role": role,
            "preferred_notification_channel": "email",
            "otp_channel_preference": otp_pref,
            "referral_code": referral_code,
            "full_name": body.full_name.strip() if body.full_name else None,
            # PR #315: complete WhatsApp eligibility at signup so the
            # daily digest sends to every new user from day one. Without
            # these two fields, 0 of 4 prod users were eligible despite
            # whatsapp_alerts=true on every row — see the 2026-06-10
            # WhatsApp-digest investigation. In Zambia, phone == WhatsApp
            # universally and completing OTP (default channel = WhatsApp
            # on free tier per resolve_otp_channel) IS the verification.
            "whatsapp_number": body.phone,
            "whatsapp_verified": True,
        }).execute()
        user_id = new_user.data[0]["id"]
        attach_referral_on_signup(user_id, body.referral_ref, supabase)

        if role == "superadmin":
            supabase.table("subscriptions").insert({
                "user_id": user_id,
                "tier": "professional",
                "status": "active",
            }).execute()
        else:
            supabase.table("subscriptions").insert({
                "user_id": user_id,
                "tier": "free",
                "status": "active",
            }).execute()
        user_row = {
            "email": str(body.email),
            "full_name": body.full_name.strip() if body.full_name else None,
            "welcome_email_sent": False,
        }

    welcome_email = user_row.get("email") or (
        str(body.email) if body.email else None
    )
    if newly_created and not user_row.get("welcome_email_sent"):
        background_tasks.add_task(
            send_welcome_email,
            user_id,
            user_row.get("full_name"),
            welcome_email,
        )

    if body.remember_device:
        device_token = secrets.token_urlsafe(32)
        register_trusted_device(
            user_id,
            device_token,
            label=_device_label(request),
            ip=_client_ip(request),
            supabase=supabase,
        )

    access, refresh = _issue_tokens(user_id, body.phone, settings)
    return AuthTokens(
        access_token=access,
        refresh_token=refresh,
        user_id=user_id,
        device_token=device_token,
    )
