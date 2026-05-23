"""Auth routes — OTP via WhatsApp."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from app.core.config import get_settings, Settings
from app.core.deps import get_supabase
from app.core.rate_limit import limiter
from app.schemas.auth import OTPRequest, OTPVerify, AuthTokens
from app.services.whatsapp import ensure_session_started, send_whatsapp_otp

router = APIRouter(prefix="/auth", tags=["Auth"])


def _hash_otp(code: str, phone: str, secret: str) -> str:
    """Return HMAC-SHA256(secret, phone:code) hex digest.

    Task #76: OTP codes are no longer stored in plaintext. The DB column
    `otp_codes.code` now holds this hash. If the DB is leaked, an attacker
    cannot use the captured rows to authenticate as a user — they'd have
    to brute-force the 6-digit OTP space against each row's hash, which
    is rate-limited by our `@limiter.limit` decorators plus the 5-minute
    TTL on the OTP itself.

    Why include `phone` in the HMAC input:
        Without it, a single attacker-observed hash could be reused to
        authenticate to any account that happens to have generated the
        same code. Including phone binds the hash to (code, phone) so
        each row's hash is unique to that user's intended code.

    Why HMAC-SHA256 instead of bcrypt/argon2:
        OTPs are 6 digits — only 10^6 possible inputs. Slow KDFs help
        against offline cracking of high-entropy passwords; for low-
        entropy OTPs the rate-limiter + 5-min TTL is the real defense.
        HMAC is fast, constant-time, and standard.

    Args:
        code: The 6-digit OTP (or whatever otp_code_length the settings
              are configured to).
        phone: The user's phone in E.164 format.
        secret: settings.jwt_secret — single key reused for OTPs.

    Returns:
        Lowercase hex digest.
    """
    message = f"{phone}:{code}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


@router.post("/otp/request")
@limiter.limit("3/minute")
async def request_otp(request: Request, body: OTPRequest, settings: Settings = Depends(get_settings), supabase=Depends(get_supabase)):
    recent = (
        supabase.table("otp_codes").select("created_at").eq("phone", body.phone)
        .gte("created_at", (datetime.now(timezone.utc) - timedelta(seconds=settings.otp_cooldown_seconds)).isoformat())
        .execute()
    )
    if recent.data:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Wait {settings.otp_cooldown_seconds}s between OTP requests")

    code = "".join([str(secrets.randbelow(10)) for _ in range(settings.otp_code_length)])
    # Store the HMAC hash, not the plaintext code. The plaintext is sent
    # to the user via WAHA and then thrown away in process memory.
    code_hash = _hash_otp(code, body.phone, settings.jwt_secret)
    supabase.table("otp_codes").insert({
        "phone": body.phone, "code": code_hash,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)).isoformat(),
    }).execute()
    try:
        # Re-bootstrap WAHA if the session went STOPPED after backend boot
        # (common after `docker compose restart waha` without restarting backend).
        session_ok = await ensure_session_started("default", timeout_seconds=20)
        if not session_ok:
            raise RuntimeError("WAHA session not WORKING")
        await send_whatsapp_otp(body.phone, code)
    except Exception as e:
        # Log but don't fail — the OTP is already stored, user can re-request if they don't get it.
        # Better UX is to return a clear 503 here than to crash with text/plain 500.
        import logging
        logging.getLogger(__name__).error("WAHA send failed for %s: %s", body.phone, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp delivery is temporarily unavailable. Please try again in a minute.",
        )
    return {"message": "OTP sent to your WhatsApp"}


@router.post("/otp/verify", response_model=AuthTokens)
@limiter.limit("10/minute")
async def verify_otp(request: Request, body: OTPVerify, settings: Settings = Depends(get_settings), supabase=Depends(get_supabase)):
    now_iso = datetime.now(timezone.utc).isoformat()
    # Compare the hash of the user-supplied code against the stored hash.
    # Constant-time-equivalent because the DB engine performs a fixed
    # equality check on the indexed column; the SELECT either finds the
    # row or doesn't (no character-by-character compare path).
    body_code_hash = _hash_otp(body.code, body.phone, settings.jwt_secret)
    result = (
        supabase.table("otp_codes").select("*").eq("phone", body.phone).eq("code", body_code_hash)
        .eq("verified", False).gte("expires_at", now_iso)
        .order("created_at", desc=True).limit(1).execute()
    )
    if not result.data:
        # Wrong/expired code: bump attempts on the most-recent unverified OTP for this phone
        # so the brute-force lockout actually engages. Read-then-write race is acceptable —
        # the @limiter.limit above bounds attack rate, and under-counting beats locking out
        # a legitimate user on stale state.
        latest = (
            supabase.table("otp_codes").select("id, attempts").eq("phone", body.phone)
            .eq("verified", False).gte("expires_at", now_iso)
            .order("created_at", desc=True).limit(1).execute()
        )
        if latest.data:
            row = latest.data[0]
            supabase.table("otp_codes").update({"attempts": (row.get("attempts") or 0) + 1}).eq("id", row["id"]).execute()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")

    otp = result.data[0]
    if otp["attempts"] >= settings.max_otp_attempts:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Too many attempts. Request a new OTP.")

    user_result = (
        supabase.table("users")
        .select("id, role, email")
        .eq("phone", body.phone)
        .limit(1)
        .execute()
    )
    if user_result.data:
        # Existing user — they consented at original signup; don't re-prompt.
        user_id = user_result.data[0]["id"]
        supabase.table("otp_codes").update({"verified": True}).eq("id", otp["id"]).execute()
        if body.email and not user_result.data[0].get("email"):
            supabase.table("users").update({"email": str(body.email)}).eq("id", user_id).execute()
    else:
        # New user — require explicit consent before creating the account.
        # Done before the OTP is marked verified so a forgotten checkbox
        # doesn't burn the code; the user can re-submit with consent=true.
        if body.consent_accepted is not True:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consent required")
        if not body.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required to create an account",
            )
        supabase.table("otp_codes").update({"verified": True}).eq("id", otp["id"]).execute()
        # Auto-assign superadmin role if phone matches SUPERADMIN_PHONE env var
        role = "superadmin" if (settings.superadmin_phone and body.phone == settings.superadmin_phone) else "user"
        new_user = supabase.table("users").insert({
            "phone": body.phone,
            "email": str(body.email),
            "role": role,
            "preferred_notification_channel": "email",
        }).execute()
        user_id = new_user.data[0]["id"]

        # Superadmin gets top tier; regular users start on free
        if role == "superadmin":
            supabase.table("subscriptions").insert({"user_id": user_id, "tier": "professional", "status": "active"}).execute()
        else:
            supabase.table("subscriptions").insert({"user_id": user_id, "tier": "free", "status": "active"}).execute()

    now = datetime.now(timezone.utc)
    access_token = jwt.encode({"sub": user_id, "phone": body.phone, "exp": now + timedelta(minutes=settings.jwt_expire_minutes), "iat": now}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    refresh_token = jwt.encode({"sub": user_id, "type": "refresh", "exp": now + timedelta(days=settings.refresh_token_expire_days), "iat": now}, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return AuthTokens(access_token=access_token, refresh_token=refresh_token, user_id=user_id)
