"""Structured CV section models.

These extend the original `CVParseResult` (in `app.services.cv_parser`) with
the richer shape a Zambian job seeker's CV typically carries: work history
with achievements, education with thesis, certifications, languages,
projects, achievements, publications, memberships, volunteer work, and
references.

All sections are optional. List caps bound LLM output runaway. Date fields
are stored as `YYYY-MM` strings rather than `date` objects to avoid
timezone footguns on JSONB roundtrip — the frontend formats them per
locale.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


# Reasonable upper bounds. Each cap exists because we've seen LLMs
# helpfully invent extra entries when source content runs thin.
MAX_WORK_EXPERIENCE = 15
MAX_ACHIEVEMENTS_PER_ROLE = 20
MAX_EDUCATION = 10
MAX_CERTIFICATIONS = 25
MAX_LANGUAGES = 10
MAX_PROJECTS = 15
MAX_ACHIEVEMENTS = 20
MAX_PUBLICATIONS = 20
MAX_MEMBERSHIPS = 15
MAX_VOLUNTEER = 10
MAX_REFERENCES = 6
MAX_PROJECT_TECHNOLOGIES = 20


def _coerce_optional_date(v: Any) -> Optional[str]:
    """Normalize LLM date shapes to YYYY-MM / YYYY strings."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return str(int(v))[:20]
    if isinstance(v, dict):
        year = v.get("year")
        month = v.get("month")
        if year is not None:
            if month is not None:
                try:
                    return f"{int(year):04d}-{int(month):02d}"[:20]
                except (TypeError, ValueError):
                    return str(year)[:20]
            return str(year)[:20]
        return None
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        if s.lower() in ("present", "current", "now", "ongoing"):
            return None
        return s[:20]
    return str(v).strip()[:20] or None


class CVHeader(BaseModel):
    """Contact / link fields above the body of the CV.

    `full_name`, `email`, `phone`, `location` already live on `users` —
    they're not duplicated here. This section is for the URL block that
    sits under the name on most modern CVs.
    """
    linkedin_url: Optional[HttpUrl] = None
    portfolio_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None


class ProfessionalSummary(BaseModel):
    """A 1-3 sentence elevator pitch at the top of the CV."""
    # 5000 covers the long-form summaries we've actually seen from
    # Zambian consultants and academics; 1000 was too tight and was
    # 503'ing /cv/upload on real CVs.
    text: str = Field("", max_length=5000)


class WorkExperience(BaseModel):
    """One role in the work history.

    `end_date` is `None` for the current role. `achievements` is a list of
    short bullet strings — the LLM is asked to surface impact statements
    here, not duties.
    """
    title: str = Field(..., max_length=200)
    company: str = Field(..., max_length=200)
    # `location` / `start_date` are Optional so the LLM can legitimately
    # send JSON null when the source CV omits them — previously typed as
    # plain `str` with a default of "", which Pydantic v2 rejects with a
    # `string_type` error on explicit null. Frontend type already declares
    # `location?: string` / `start_date?: string`.
    location: Optional[str] = Field(None, max_length=200)
    start_date: Optional[str] = Field(None, max_length=20)
    end_date: Optional[str] = Field(None, max_length=20)
    achievements: list[str] = Field(default_factory=list)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _coerce_dates(cls, v: Any) -> Optional[str]:
        return _coerce_optional_date(v)

    @field_validator("achievements", mode="before")
    @classmethod
    def _trim_achievements(cls, v) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for item in v:
            s = (item if isinstance(item, str) else str(item or "")).strip()
            if s:
                out.append(s[:500])
        return out[:MAX_ACHIEVEMENTS_PER_ROLE]


class Education(BaseModel):
    degree: str = Field(..., max_length=200)
    institution: str = Field(..., max_length=200)
    # See WorkExperience: Optional so JSON null from the LLM validates.
    location: Optional[str] = Field(None, max_length=200)
    start_date: Optional[str] = Field(None, max_length=20)
    end_date: Optional[str] = Field(None, max_length=20)
    gpa: Optional[str] = Field(None, max_length=20)
    thesis: Optional[str] = Field(None, max_length=500)


class Certification(BaseModel):
    name: str = Field(..., max_length=200)
    # Optional so JSON null from the LLM validates (issuer is often
    # missing on self-issued or non-accredited certs).
    issuer: Optional[str] = Field(None, max_length=200)
    year: Optional[str] = Field(None, max_length=10)
    expiry: Optional[str] = Field(None, max_length=20)


class Language(BaseModel):
    name: str = Field(..., max_length=80)
    proficiency: Literal["native", "fluent", "conversational", "basic"] = "conversational"


class Project(BaseModel):
    """Side project, OSS contribution, or notable build.

    `outcome` is the one-line "what did it deliver" — keeps these from
    becoming yet another job-history entry.
    """
    name: str = Field(..., max_length=200)
    role: str = Field("", max_length=200)
    technologies: list[str] = Field(default_factory=list)
    outcome: str = Field("", max_length=500)

    @field_validator("technologies", mode="before")
    @classmethod
    def _normalize_tech(cls, v) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            return []
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            s = (item if isinstance(item, str) else str(item or "")).strip()
            if not s:
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(s[:80])
        return out[:MAX_PROJECT_TECHNOLOGIES]


class Achievement(BaseModel):
    """Award, scholarship, ranking, or other notable accomplishment."""
    title: str = Field(..., max_length=300)
    year: Optional[str] = Field(None, max_length=10)


class Publication(BaseModel):
    """Paper, article, or other published work.

    Fields chosen for the Zambian context — most local CVs cite
    journals/conferences by name and skip DOI; `url` is preserved when
    available for online-first publications.
    """
    title: str = Field(..., max_length=300)
    venue: str = Field("", max_length=200)
    year: Optional[str] = Field(None, max_length=10)
    url: Optional[HttpUrl] = None


class Membership(BaseModel):
    """Professional body or association membership.

    EIZ, ZICA, LAZ etc. are common on Zambian CVs and recruiters look for
    them. `role` covers "Member / Fellow / Board / Treasurer".
    """
    organisation: str = Field(..., max_length=200)
    role: str = Field("Member", max_length=80)
    year_started: Optional[str] = Field(None, max_length=10)
    year_ended: Optional[str] = Field(None, max_length=10)


class VolunteerWork(BaseModel):
    organisation: str = Field(..., max_length=200)
    role: str = Field("", max_length=200)
    start_date: str = Field("", max_length=20)
    end_date: Optional[str] = Field(None, max_length=20)
    description: str = Field("", max_length=500)


class Reference(BaseModel):
    """Professional reference.

    Many Zambian CVs list 2-3 named references with phone + email. When
    the CV says only "References available on request", the templates
    emit that line as a fallback (see Reference list handling).
    """
    name: str = Field(..., max_length=200)
    title: str = Field("", max_length=200)
    organisation: str = Field("", max_length=200)
    phone: Optional[str] = Field(None, max_length=64)
    email: Optional[str] = Field(None, max_length=320)


class CVSections(BaseModel):
    """Wrapper for the structured CV body.

    All fields are optional with safe empty defaults so legacy parsed_data
    rows without these keys still validate without error.
    """
    header: Optional[CVHeader] = None
    professional_summary: Optional[ProfessionalSummary] = None
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    achievements: list[Achievement] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    memberships: list[Membership] = Field(default_factory=list)
    volunteer_work: list[VolunteerWork] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)

    @field_validator("work_experience", mode="before")
    @classmethod
    def _coerce_work_experience_entries(cls, v: Any) -> Any:
        if v is None:
            return []
        if not isinstance(v, list):
            return []
        out: list[Any] = []
        for item in v:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append({"title": s, "company": ""})
            elif isinstance(item, dict):
                out.append(item)
        return out

    @field_validator("education", mode="before")
    @classmethod
    def _coerce_education_entries(cls, v: Any) -> Any:
        if v is None:
            return []
        if not isinstance(v, list):
            return []
        out: list[Any] = []
        for item in v:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append({"degree": s, "institution": ""})
            elif isinstance(item, dict):
                out.append(item)
        return out

    @field_validator("references", mode="before")
    @classmethod
    def _coerce_reference_entries(cls, v: Any) -> Any:
        if v is None:
            return []
        if not isinstance(v, list):
            return []
        out: list[Any] = []
        for item in v:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append({"name": s})
            elif isinstance(item, dict):
                out.append(item)
        return out

    @field_validator("work_experience", mode="after")
    @classmethod
    def _cap_work_experience(cls, v: list[WorkExperience]) -> list[WorkExperience]:
        return v[:MAX_WORK_EXPERIENCE]

    @field_validator("education", mode="after")
    @classmethod
    def _cap_education(cls, v: list[Education]) -> list[Education]:
        return v[:MAX_EDUCATION]

    @field_validator("certifications", mode="after")
    @classmethod
    def _cap_certifications(cls, v: list[Certification]) -> list[Certification]:
        return v[:MAX_CERTIFICATIONS]

    @field_validator("languages", mode="after")
    @classmethod
    def _cap_languages(cls, v: list[Language]) -> list[Language]:
        return v[:MAX_LANGUAGES]

    @field_validator("projects", mode="after")
    @classmethod
    def _cap_projects(cls, v: list[Project]) -> list[Project]:
        return v[:MAX_PROJECTS]

    @field_validator("achievements", mode="after")
    @classmethod
    def _cap_achievements(cls, v: list[Achievement]) -> list[Achievement]:
        return v[:MAX_ACHIEVEMENTS]

    @field_validator("publications", mode="after")
    @classmethod
    def _cap_publications(cls, v: list[Publication]) -> list[Publication]:
        return v[:MAX_PUBLICATIONS]

    @field_validator("memberships", mode="after")
    @classmethod
    def _cap_memberships(cls, v: list[Membership]) -> list[Membership]:
        return v[:MAX_MEMBERSHIPS]

    @field_validator("volunteer_work", mode="after")
    @classmethod
    def _cap_volunteer(cls, v: list[VolunteerWork]) -> list[VolunteerWork]:
        return v[:MAX_VOLUNTEER]

    @field_validator("references", mode="after")
    @classmethod
    def _cap_references(cls, v: list[Reference]) -> list[Reference]:
        return v[:MAX_REFERENCES]
