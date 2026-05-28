"""Request/response models for the manual CV wizard (build-from-scratch)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ScratchBasics(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field("", max_length=20)
    email: str = Field("", max_length=254)
    location: str = Field("", max_length=200)
    headline: str = Field("", max_length=300)


class ScratchExperience(BaseModel):
    title: str = Field(..., max_length=200)
    company: str = Field(..., max_length=200)
    location: str = Field("", max_length=200)
    start_date: str = Field("", max_length=40)
    end_date: str = Field("", max_length=40)
    achievements: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("achievements", mode="before")
    @classmethod
    def _strip_achievements(cls, v):
        if v is None:
            return []
        return [str(x).strip() for x in v if str(x).strip()][:20]


class ScratchEducation(BaseModel):
    degree: str = Field(..., max_length=200)
    institution: str = Field(..., max_length=200)
    location: str = Field("", max_length=200)
    start_date: str = Field("", max_length=40)
    end_date: str = Field("", max_length=40)
    gpa: str = Field("", max_length=20)


class ScratchStyle(BaseModel):
    template: Literal["modern", "classic", "compact"] = "modern"
    accent_color: str = Field("#0E5C3A", max_length=20)
    show_summary: bool = True


class BuildFromScratchBody(BaseModel):
    summary: str = Field("", max_length=5000)
    basics: ScratchBasics
    experience: list[ScratchExperience] = Field(default_factory=list, max_length=15)
    education: list[ScratchEducation] = Field(default_factory=list, max_length=10)
    skills: list[str] = Field(default_factory=list, max_length=50)
    style: ScratchStyle = Field(default_factory=ScratchStyle)


class BuildFromScratchResponse(BaseModel):
    cv_id: str
    pdf_url: str
    storage_path: str
    render_time_ms: int


class SuggestSummaryBody(BaseModel):
    strengths: list[str] = Field(..., min_length=1, max_length=3)
    headline: str = Field("", max_length=300)
    full_name: str = Field("", max_length=200)


class SuggestSummaryResponse(BaseModel):
    summary: str


class SuggestBulletsBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    company: str = Field(..., min_length=1, max_length=200)
    context: str = Field("", max_length=2000)


class SuggestBulletsResponse(BaseModel):
    bullets: list[str]


class SkillSuggestItem(BaseModel):
    name: str


class SkillSuggestResponse(BaseModel):
    skills: list[SkillSuggestItem]
