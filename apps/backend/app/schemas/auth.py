from pydantic import BaseModel, EmailStr, Field

class OTPRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+260[0-9]{9}$", examples=["+260971234567"])
    channel: str | None = Field(
        None,
        description="Override OTP delivery: email, whatsapp, or both",
    )
    full_name: str | None = Field(
        None,
        min_length=2,
        max_length=128,
        description="User's full name, required in frontend for personalization",
    )
    email: EmailStr | None = Field(
        None,
        description="Optional email provided from the signup form to support email OTP for new users.",
    )

class OTPVerify(BaseModel):
    phone: str = Field(..., pattern=r"^\+260[0-9]{9}$")
    code: str = Field(..., min_length=6, max_length=6)
    email: EmailStr | None = Field(
        None,
        description="Required when creating a new account; used for match digests.",
    )
    consent_accepted: bool | None = None
    remember_device: bool = False
    referral_ref: str | None = Field(
        None,
        max_length=64,
        description="Invite ref from link (?ref=) — user id or referral_code.",
    )
    full_name: str | None = Field(
        None,
        min_length=2,
        max_length=128,
        description="User's full name, supplied on verify to set on initial creation",
    )

class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+260[0-9]{9}$", examples=["+260971234567"])

class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    device_token: str | None = Field(
        None,
        description="Present when remember_device was true on verify; store in localStorage",
    )
    trusted_device_login: bool = False

class OTPRequestResponse(BaseModel):
    message: str
    tier: str | None = None
    default_channel: str | None = None

class LoginChallengeResponse(BaseModel):
    needs_otp: bool = True
    tier: str | None = None
    default_channel: str | None = None
