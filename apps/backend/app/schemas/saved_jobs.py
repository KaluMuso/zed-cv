"""Saved jobs API models — re-exports application tracking schemas."""

from app.schemas.application_status import (
    ApplicationStatus,
    ApplicationStatusResponse,
    ApplicationStatusUpdate,
    SavedJobApplication,
    SavedJobsList,
)
from app.schemas.saved_jobs_legacy import SaveJobResponse

__all__ = [
    "ApplicationStatus",
    "ApplicationStatusResponse",
    "ApplicationStatusUpdate",
    "SaveJobResponse",
    "SavedJobApplication",
    "SavedJobsList",
]
