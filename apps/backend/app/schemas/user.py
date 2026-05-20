from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal

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


class UserPreferences(BaseModel):
    whatsapp_alerts: bool = True
    email_notifications_enabled: bool = True
    language: Literal["en", "bem"] = "en"


class UserPreferencesUpdate(BaseModel):
    whatsapp_alerts: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None
    language: Optional[Literal["en", "bem"]] = None


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
