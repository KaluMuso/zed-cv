from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Literal

from app.core.phone import normalize_zambian_e164_phone
from app.schemas.cv_sections import CVSections


class UserProfile(BaseModel):
    id: str
    phone: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    location: Optional[str] = None
    years_experience: int = 0
    skills: list[str] = []
    cv_uploaded: bool = False
    subscription_tier: str = "free"
    role: str = "user"
    # Structured CV body extracted by the parser (task #59). Null for
    # users who haven't uploaded a CV yet, or whose upload pre-dates
    # the structured-parser change (legacy parsed_data without the
    # "sections" key). Frontend treats null as "show empty state".
    cv_sections: Optional[CVSections] = None

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    location: Optional[str] = Field(None, max_length=100)
    years_experience: Optional[int] = Field(None, ge=0)


class NotificationPreferences(BaseModel):
    """Notification toggles — GET/PATCH /api/v1/profile/preferences."""

    whatsapp_alerts: bool = True
    email_notifications_enabled: bool = True
    language: Literal["en", "bem"] = "en"


class NotificationPreferencesUpdate(BaseModel):
    whatsapp_alerts: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None
    language: Optional[Literal["en", "bem"]] = None


PreferredNotificationChannel = Literal["email", "whatsapp", "both"]


class UserPreferences(BaseModel):
    """Dashboard settings — GET/PATCH /api/v1/users/me/preferences."""

    whatsapp_number: Optional[str] = None
    location: Optional[str] = None
    currency: Literal["ZMW", "USD"] = "ZMW"
    alert_frequency: Literal["daily", "weekly", "muted"] = "daily"
    whatsapp_verified: bool = False
    preferred_notification_channel: PreferredNotificationChannel = "email"
    whatsapp_digest_available: bool = False


class UserPreferencesUpdate(BaseModel):
    whatsapp_number: Optional[str] = Field(
        None,
        description="Zambian mobile in E.164 (+260 plus 9 digits). Optional delivery number.",
    )
    location: Optional[str] = Field(None, max_length=100)
    currency: Optional[Literal["ZMW", "USD"]] = None
    alert_frequency: Optional[Literal["daily", "weekly", "muted"]] = None
    preferred_notification_channel: Optional[PreferredNotificationChannel] = None

    @field_validator("whatsapp_number")
    @classmethod
    def _validate_whatsapp_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return normalize_zambian_e164_phone(value)


class NotificationChannels(BaseModel):
    whatsapp: bool = True
    email: bool = True


class AutoMatchPreferences(BaseModel):
    auto_match_enabled: bool = True
    notification_channels: NotificationChannels = Field(default_factory=NotificationChannels)


class AutoMatchPreferencesUpdate(BaseModel):
    auto_match_enabled: Optional[bool] = None
    notification_channels: Optional[NotificationChannels] = None


class ProfileDeleted(BaseModel):
    deleted: bool = True
    user_id: str


Proficiency = Literal["beginner", "intermediate", "advanced", "expert"]


class UserSkill(BaseModel):
    name: str
    proficiency: Proficiency = "intermediate"
    source: Literal["cv_parse", "manual", "assessment"] = "manual"


class UserSkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    proficiency: Proficiency = "intermediate"


class UserSkillUpdate(BaseModel):
    proficiency: Proficiency


class UserSkillsList(BaseModel):
    skills: list[UserSkill]
