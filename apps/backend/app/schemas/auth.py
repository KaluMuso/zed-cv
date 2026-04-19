"""Auth-related Pydantic schemas — mirrors OpenAPI spec."""

from pydantic import BaseModel, Field
import re


class OTPRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+260[0-9]{9}$", examples=["+260971234567"])


class OTPVerify(BaseModel):
    phone: str = Field(..., pattern=r"^\+260[0-9]{9}$")
    code: str = Field(..., min_length=6, max_length=6)


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
