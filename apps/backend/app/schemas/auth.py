from pydantic import BaseModel, EmailStr, Field

class OTPRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+260[0-9]{9}$", examples=["+260971234567"])

class OTPVerify(BaseModel):
    phone: str = Field(..., pattern=r"^\+260[0-9]{9}$")
    code: str = Field(..., min_length=6, max_length=6)
    email: EmailStr | None = Field(
        None,
        description="Required when creating a new account; used for match digests.",
    )
    # Optional so missing-consent returns a 400 with our own detail
    # rather than a generic 422 from Pydantic. Only enforced for new
    # users in the verify route — existing users already consented at
    # their original signup.
    consent_accepted: bool | None = None

class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
