"""Job-search preference schemas.

Backs the `user_preferences` table (migration 026) and the
/api/v1/preferences endpoints. Kept in a dedicated module rather than
extending `app.schemas.user` because the existing `UserPreferences` in
that file covers notification prefs (whatsapp_alerts, language) — these
are job-search prefs and the two shouldn't share a name.

Wire-shape contract: the API names exported here (JobPreferences,
JobPreferencesUpdate, PreferredLanguage, IndustryExperience) are mirrored
1:1 in docs/openapi.yaml and apps/frontend/src/lib/api.ts. The
ci_openapi_ts_guard runs on every PR and will fail if the three drift.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# Caps live in the schema so they're visible to anyone reading the
# Pydantic models. Mirrored in the migration COMMENTs and in the
# frontend input components. Changing one requires changing all three.
MAX_TARGET_ROLES = 10
MAX_LANGUAGES = 8
MAX_INDUSTRIES = 8
MAX_REGIONS = 6

# 1 ZMW = 100 ngwee. The upper bound is roughly K10M/month which is a
# generous ceiling — anything above is almost certainly a unit error
# (user typed kwacha instead of ngwee). We reject rather than silently
# coerce so the frontend can show "did you mean K…?".
MAX_SALARY_NGWEE = 1_000_000_000


LanguageProficiency = Literal["native", "fluent", "intermediate", "basic"]
SalaryFrequency = Literal["monthly", "annual", "hourly", "daily"]
WorkArrangement = Literal["remote", "hybrid", "onsite", "any"]
TargetRolesSource = Literal["user_provided", "cv_inferred", "mixed"]


class PreferredLanguage(BaseModel):
    """One entry in user_preferences.languages.

    Distinct from the CV-section `Language` model (cv_sections.py) — that
    one has a different proficiency vocabulary ("conversational"), this
    one matches the wider self-rating UI the form uses ("intermediate").
    """

    language: str = Field(..., min_length=1, max_length=80)
    proficiency: LanguageProficiency = "intermediate"

    @field_validator("language", mode="before")
    @classmethod
    def _strip(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class IndustryExperience(BaseModel):
    """One entry in user_preferences.industries."""

    industry: str = Field(..., min_length=1, max_length=120)
    years_experience: int = Field(0, ge=0, le=80)

    @field_validator("industry", mode="before")
    @classmethod
    def _strip(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class JobPreferences(BaseModel):
    """Read shape for GET /api/v1/preferences.

    All fields are optional / have safe defaults so a freshly-created
    empty row serialises cleanly (no None-vs-missing ambiguity for the
    frontend).
    """

    target_roles: list[str] = Field(default_factory=list)
    target_roles_source: TargetRolesSource = "user_provided"

    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "ZMW"
    salary_frequency: Optional[SalaryFrequency] = None

    preferred_work_arrangement: Optional[WorkArrangement] = None
    willing_to_relocate: bool = False
    acceptable_regions: list[str] = Field(default_factory=list)

    languages: list[PreferredLanguage] = Field(default_factory=list)
    industries: list[IndustryExperience] = Field(default_factory=list)

    extras: dict[str, Any] = Field(default_factory=dict)

    auto_populated_at: Optional[datetime] = None
    manually_updated_at: Optional[datetime] = None

    # Per-field hint for the UI: which fields were filled by the
    # CV-upload auto-populate path and have not been manually edited
    # since. Lets the frontend stamp the "Auto-populated from CV"
    # badge without keeping its own client-side bookkeeping. Computed
    # by the API layer; not persisted as a column.
    auto_populated_fields: list[str] = Field(default_factory=list)


class JobPreferencesUpdate(BaseModel):
    """Write shape for PATCH /api/v1/preferences.

    Every field is optional — clients PATCH whatever they changed. None
    explicitly means "don't touch", not "set to NULL"; the empty list /
    empty dict means "clear". This matches the auto-save-on-blur
    pattern in the Preferences tab (each blur sends only the field that
    changed).
    """

    target_roles: Optional[list[str]] = None
    salary_min: Optional[int] = Field(None, ge=0, le=MAX_SALARY_NGWEE)
    salary_max: Optional[int] = Field(None, ge=0, le=MAX_SALARY_NGWEE)
    salary_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    salary_frequency: Optional[SalaryFrequency] = None
    preferred_work_arrangement: Optional[WorkArrangement] = None
    willing_to_relocate: Optional[bool] = None
    acceptable_regions: Optional[list[str]] = None
    languages: Optional[list[PreferredLanguage]] = None
    industries: Optional[list[IndustryExperience]] = None
    extras: Optional[dict[str, Any]] = None

    @field_validator("target_roles", mode="after")
    @classmethod
    def _cap_roles(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        return _dedup_strip(v)[:MAX_TARGET_ROLES]

    @field_validator("acceptable_regions", mode="after")
    @classmethod
    def _cap_regions(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        return _dedup_strip(v)[:MAX_REGIONS]

    @field_validator("languages", mode="after")
    @classmethod
    def _cap_languages(
        cls, v: Optional[list[PreferredLanguage]]
    ) -> Optional[list[PreferredLanguage]]:
        if v is None:
            return None
        return v[:MAX_LANGUAGES]

    @field_validator("industries", mode="after")
    @classmethod
    def _cap_industries(
        cls, v: Optional[list[IndustryExperience]]
    ) -> Optional[list[IndustryExperience]]:
        if v is None:
            return None
        return v[:MAX_INDUSTRIES]

    @model_validator(mode="after")
    def _salary_invariant(self) -> "JobPreferencesUpdate":
        """salary_min must be <= salary_max when both are provided.

        Skipped when one or both are None — a user typing salary_max
        first should not be blocked while salary_min is still empty.
        """
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError(
                    "salary_min must be less than or equal to salary_max"
                )
        return self


def _dedup_strip(items: list[str]) -> list[str]:
    """Trim + case-insensitive dedup, preserving first-occurrence order.

    Used for target_roles and acceptable_regions where the display form
    is mixed-case ("Lusaka") but two entries that differ only in case
    are still duplicates.
    """
    seen: set[str] = set()
    out: list[str] = []
    for s in items:
        if not isinstance(s, str):
            continue
        trimmed = s.strip()
        if not trimmed:
            continue
        key = trimmed.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(trimmed)
    return out
