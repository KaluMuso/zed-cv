"""Application tracking models for saved jobs Kanban."""

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.jobs import Job


class ApplicationStatus(str, Enum):
    saved = "saved"
    applied = "applied"
    interviewing = "interviewing"
    offered = "offered"
    closed_won = "closed_won"
    closed_lost = "closed_lost"


ApplicationStatusLiteral = Literal[
    "saved",
    "applied",
    "interviewing",
    "offered",
    "closed_won",
    "closed_lost",
]


class SavedJobApplication(BaseModel):
    job: Job
    application_status: ApplicationStatus = ApplicationStatus.saved
    status_updated_at: datetime | None = None
    application_notes: str | None = None
    interview_date: date | None = None


class SavedJobsList(BaseModel):
    jobs: list[Job]
    applications: list[SavedJobApplication] = Field(default_factory=list)


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    notes: str | None = None
    interview_date: date | None = None


class ApplicationStatusResponse(BaseModel):
    job_id: str
    application_status: ApplicationStatus
    status_updated_at: datetime | None = None
    application_notes: str | None = None
    interview_date: date | None = None
