from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional, Any
from enum import Enum

class JobSource(str, Enum):
    manual = "manual"
    scraper = "scraper"
    ocr = "ocr"
    partner = "partner"


# Date formats the scraper has been observed to emit. ISO 8601 is the
# canonical form; the rest are fallbacks for scraper-AI outputs that
# don't yet normalize. Failure on all formats returns None — the DB
# column has a now() / null default and we don't want to fail the whole
# row over a malformed date string.
_DATE_FALLBACK_FORMATS = (
    "%d/%b/%Y",   # 11/May/2026
    "%d/%B/%Y",   # 11/December/2026
    "%d-%b-%Y",   # 11-May-2026
    "%d-%B-%Y",
    "%d/%m/%Y",   # 11/05/2026
    "%d-%m-%Y",
    "%Y/%m/%d",   # 2026/05/11
    "%b %d, %Y",  # May 11, 2026
    "%B %d, %Y",
)


def _tolerant_parse_date(v: Any) -> Optional[date]:
    """Accept ISO dates (canonical), datetimes, and common scraper-AI
    fallback formats. Return None on failure so the DB default applies."""
    if v is None or isinstance(v, date):
        return v if not isinstance(v, datetime) else v.date()
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    # Strict ISO first
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    # Fallbacks
    for fmt in _DATE_FALLBACK_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

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

    # Tolerant date parsing — the scraper's AI parsing nodes have been
    # observed emitting non-ISO formats like "11/May/2026". Accept them
    # rather than 422-ing the whole batch.
    @field_validator("posted_at", "closing_date", mode="before")
    @classmethod
    def _parse_dates(cls, v: Any) -> Optional[date]:
        return _tolerant_parse_date(v)

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
