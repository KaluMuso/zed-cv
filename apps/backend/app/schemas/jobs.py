from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from enum import Enum

class JobSource(str, Enum):
    manual = "manual"
    scraper = "scraper"
    ocr = "ocr"
    partner = "partner"

class JobCreate(BaseModel):
    title: str = Field(..., min_length=5)
    company: Optional[str] = None
    location: Optional[str] = None
    description: str = Field(..., min_length=20)
    requirements: list[str] = []
    skills_required: list[str] = []
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    source: JobSource
    # URL of the source listing on the scraper site (e.g. jobwebzambia.com).
    # Distinct from apply_url, which should ideally point at the employer's
    # own application page when extractable from the description.
    source_url: Optional[str] = None
    closing_date: Optional[date] = None
    # Date the job was originally posted (set by scraper). Falls back to
    # NOW() at insert if not provided.
    posted_at: Optional[date] = None

class Job(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: str
    requirements: list[str] = []
    skills_required: list[str] = []
    skills: list[str] = []  # Alias for frontend compatibility
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    quality_score: int = 0
    closing_date: Optional[date] = None
    posted_at: datetime
    is_active: bool = True

class JobList(BaseModel):
    jobs: list[Job]
    total: int
    page: int
    per_page: int
    pages: int = 0


# ── Bulk ingest (scraper) ─────────────────────────────────────────────
class JobIngestRequest(BaseModel):
    """Payload from n8n's Zambia Job Scraper workflow.

    Auth is by shared secret in the body (settings.ingest_api_key) rather
    than a header so the n8n HTTP Request node can use Predefined
    Credential Type = None and just send JSON.
    """
    api_key: str
    jobs: list[JobCreate]


class JobIngestErrorItem(BaseModel):
    index: int
    title: str
    reason: str


class JobIngestResponse(BaseModel):
    ingested: int
    duplicates: int
    errors: list[JobIngestErrorItem] = []
