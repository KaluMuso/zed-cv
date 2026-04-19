"""User profile schemas."""

from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional


class UserProfile(BaseModel):
    id: str
    phone: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    location: Optional[str] = None
    years_experience: int = 0
    skills: list[str] = []
    subscription_tier: str = "mwana"
    created_at: datetime


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    location: Optional[str] = Field(None, max_length=100)
    years_experience: Optional[int] = Field(None, ge=0)
