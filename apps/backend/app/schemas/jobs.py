import re as _re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import date, datetime
from typing import Literal, Optional, Any
from enum import Enum

class JobSource(str, Enum):
    manual = "manual"
    scraper = "scraper"
    ocr = "ocr"
    partner = "partner"


# Job-ad structural enums (task #60).
# Stored as text columns on public.jobs. Validation is app-layer Pydantic
# only — per task #28, CHECK constraints in the DB are out of style here
# because they require a migration every time we add a value.
class EmploymentType(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    freelance = "freelance"
    internship = "internship"
    temporary = "temporary"


class WorkArrangement(str, Enum):
    remote = "remote"
    hybrid = "hybrid"
    on_site = "on_site"


# Pay frequency uses Literal rather than Enum because it's only ever
# referenced from the schema-side (no other Python code branches on it),
# and Literal serialises cleanly to a string column without enum wrapping.
PayFrequency = Literal["monthly", "annual", "hourly", "daily"]


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
    # Spelled-out formats commonly emitted by the WhatsApp channel extractor
    # after task #60. The ordinal suffix (st/nd/rd/th) is stripped upstream
    # in _tolerant_parse_date so the same patterns cover "20 May 2026" and
    # "20th May 2026" without separate entries.
    "%d %b %Y",   # 20 May 2026 (after ordinal strip)
    "%d %B %Y",   # 20 December 2026
)

# Matches ordinal suffixes on a day-of-month: "1st", "2nd", "3rd", "20th".
# Stripped before strptime since Python's directives don't understand them.
_ORDINAL_SUFFIX_RE = _re.compile(r"(\d+)(st|nd|rd|th)\b", _re.IGNORECASE)


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
    # Strip ordinal suffix so "20th May 2026" can hit "%d %B %Y" below.
    # Idempotent: rows without ordinals are unchanged.
    s_no_ordinal = _ORDINAL_SUFFIX_RE.sub(r"\1", s)
    # Fallbacks (try both original and ordinal-stripped variants — most
    # formats don't care, but the spelled-out month patterns do).
    candidates = (s, s_no_ordinal) if s_no_ordinal != s else (s,)
    for cand in candidates:
        for fmt in _DATE_FALLBACK_FORMATS:
            try:
                return datetime.strptime(cand, fmt).date()
            except ValueError:
                continue
    return None


# ── Salary text parsing (task #60) ────────────────────────────────────
# Convert free-text salary strings ("K15,000 - K20,000", "ZMW 15000/mo")
# to a (min_ngwee, max_ngwee) tuple. Returns (None, None) when the input
# is unparseable, ambiguous (e.g. "negotiable"), or not denominated in
# Zambian Kwacha — for non-ZMW currencies we leave the ints null and let
# the `currency` column carry the unit. Per AGENTS.md, all stored
# amounts must be ngwee (1 ZMW = 100 ngwee).

# K, ZMW, kwacha (case-insensitive) all indicate Zambian currency.
_ZMW_MARKERS = _re.compile(r"(?:\bk\b|\bzmw\b|\bkwacha\b|^k(?=\d)|\bk(?=\d))", _re.IGNORECASE)

# Non-ZMW currency markers — if ANY of these appears we bail with
# (None, None) so the helper doesn't accidentally treat USD/GBP/etc. as
# ngwee. Word boundaries (\b) around the alpha codes; `$` and `£`/`€`
# need different treatment because they're non-word characters: \b
# doesn't bind around them at start-of-string. The "$ followed by a
# digit" pattern catches "$5000" and "$ 5000" specifically.
_NON_ZMW_MARKERS = _re.compile(
    r"\b(?:usd|eur|gbp|naira|ngn|rand|zar)\b|us\$|\$\s*\d|£|€",
    _re.IGNORECASE,
)

# Pulls a numeric value with optional thousands separators and an
# optional "k"/"K" suffix (15k = 15,000). Two alternatives:
#   1) `\d{1,3}(?:[,\s]\d{3})+...` — REQUIRES at least one comma/space
#      group, matches "15,000" / "1,500,000" properly.
#   2) `\d+(?:\.\d+)?`             — bare digits (and decimals) without
#      separators, matches "15000" / "3.5".
# Alt (1) must require `+` not `*` — otherwise it ALSO matches the
# unseparated case and the regex engine picks the shorter prefix
# (matching "500" of "5000"), which silently filtered out real salaries.
_AMOUNT_RE = _re.compile(
    r"(\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(k|m)?",
    _re.IGNORECASE,
)


def _amount_to_ngwee(num_str: str, suffix: str | None) -> Optional[int]:
    """Parse one captured group into ngwee. Handles thousands separators
    and k/m suffixes ('15k' → 15000 ZMW, '1.5m' → 1,500,000 ZMW)."""
    try:
        raw = float(num_str.replace(",", "").replace(" ", ""))
    except ValueError:
        return None
    if suffix:
        s = suffix.lower()
        if s == "k":
            raw *= 1_000
        elif s == "m":
            raw *= 1_000_000
    if raw <= 0:
        return None
    return int(round(raw * 100))  # ngwee = kwacha × 100


def _parse_salary_to_ngwee(text: str | None) -> tuple[Optional[int], Optional[int]]:
    """Best-effort parse of a free-text salary string into (min, max) ngwee.

    Used as an ingest fallback when the scraper produces a string instead
    of separate min/max ints. Returns (None, None) on:
      - empty / null input
      - "negotiable" / "depends on experience" / "TBD"-style text
      - non-ZMW currency (we don't FX-convert; the caller stores the
        unit in the `currency` column instead)
      - any parse failure

    Accepts: "K15,000", "K15,000 - K20,000", "ZMW 15000-20000/month",
    "15k-20k", "K3.5m". Order-tolerant on min/max — if a single value is
    given, sets BOTH to it (no implicit range expansion).
    """
    if not text or not isinstance(text, str):
        return (None, None)
    s = text.strip()
    if not s:
        return (None, None)
    lower = s.lower()
    # Common non-numeric placeholders — explicit early return so we don't
    # accidentally pull a year out of "negotiable, posted 2026".
    if any(
        phrase in lower
        for phrase in ("negotiable", "depends on experience", "tbd", "to be discussed", "competitive")
    ):
        return (None, None)
    # Any non-ZMW currency marker → bail. We could try to be clever about
    # "$5000 (≈ K100,000)" style notations but the conservative default
    # (drop the row, let the listing surface in /jobs with no salary
    # shown) is preferable to mis-stating compensation. The `currency`
    # column carries the unit; this helper sticks to ngwee.
    if _NON_ZMW_MARKERS.search(s):
        return (None, None)

    matches = _AMOUNT_RE.findall(s)
    if not matches:
        return (None, None)
    # Filter out spurious matches like the year in "posted 2026" — these
    # are typically 4-digit numbers ≥ 1900. Salary inputs lower than
    # K500 are also implausible (lowest legal monthly wage in Zambia is
    # ~K1500 as of 2026); drop them so a "2024" year doesn't get treated
    # as a K2,024 salary.
    parsed: list[int] = []
    for num_str, suffix in matches:
        val = _amount_to_ngwee(num_str, suffix)
        if val is None:
            continue
        kwacha = val // 100
        # 1900-2100 = year-shaped, almost never salary. >= K500 monthly
        # floor weeds out single-digit and very small numbers (page
        # numbers, days-per-month). The 5-digit cap upper limit isn't
        # imposed here so executive salaries (K200k/mo) still parse.
        if 1900 <= kwacha <= 2100:
            continue
        if kwacha < 500:
            continue
        parsed.append(val)

    if not parsed:
        return (None, None)
    if len(parsed) == 1:
        return (parsed[0], parsed[0])
    return (min(parsed), max(parsed))

class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    company: Optional[str] = None
    location: Optional[str] = None
    description: str = Field(..., min_length=20)
    requirements: list[str] = []
    skills_required: list[str] = []
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    source: JobSource | str
    # URL of the source listing on the scraper site (e.g. jobwebzambia.com).
    # Distinct from apply_url, which should ideally point at the employer's
    # own application page when extractable from the description.
    source_url: Optional[str] = None
    closing_date: Optional[date] = None
    # Date the job was originally posted (set by scraper). Falls back to
    # NOW() at insert if not provided.
    posted_at: Optional[date] = None

    # ── task #60: richer job ad shape ─────────────────────────────────
    # All optional so legacy scrapers and the manual /jobs POST keep
    # working unchanged. Caps mirror cv_sections.py — bound LLM output
    # runaway so a misbehaving extractor can't blow up the DB row.
    employment_type: Optional[EmploymentType] = None
    work_arrangement: Optional[WorkArrangement] = None
    benefits: list[str] = Field(default_factory=list)
    application_instructions: Optional[str] = Field(None, max_length=2000)
    interview_process: Optional[str] = Field(None, max_length=1000)
    tools_tech_stack: list[str] = Field(default_factory=list)
    company_description: Optional[str] = Field(None, max_length=2000)
    reference_number: Optional[str] = Field(None, max_length=100)
    currency: Optional[str] = Field(None, max_length=3, min_length=3)
    pay_frequency: Optional[PayFrequency] = None
    experience_min_years: Optional[int] = Field(None, ge=0, le=50)
    seniority_level: Optional[str] = Field(None, max_length=32)
    qualifications_required: list[str] = Field(default_factory=list)

    # Deep-scrape enrichment (migration 045) — optional on create/ingest.
    source_platform: Optional[str] = Field(None, max_length=64)
    original_source_url: Optional[str] = Field(None, max_length=2000)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_whatsapp: Optional[str] = Field(None, max_length=64)
    is_enriched: Optional[bool] = None

    # Set by multi-role splitter during ingest; stored on jobs row.
    parent_listing_signature: Optional[str] = Field(None, max_length=64)

    # INPUT-ONLY (not stored). When the scraper emits a free-text salary
    # string and leaves salary_min/max null, the ingest pipeline runs
    # _parse_salary_to_ngwee on this to derive the integer fields. After
    # ingest the field is dropped from the insert payload. Keep null when
    # the scraper already provides integer min/max so the helper doesn't
    # override perfectly-good data.
    salary_text: Optional[str] = Field(None, max_length=500)

    # Tolerant date parsing — the scraper's AI parsing nodes have been
    # observed emitting non-ISO formats like "11/May/2026". Accept them
    # rather than 422-ing the whole batch.
    @field_validator("source", mode="before")
    @classmethod
    def _coerce_source(cls, v: Any) -> str:
        if isinstance(v, JobSource):
            return v.value
        s = str(v).strip()
        if s in {e.value for e in JobSource}:
            return s
        if s.startswith("whatsapp_"):
            return s[:128]
        raise ValueError(f"Invalid job source: {s!r}")

    @field_validator("posted_at", "closing_date", mode="before")
    @classmethod
    def _parse_dates(cls, v: Any) -> Optional[date]:
        return _tolerant_parse_date(v)

    @field_validator("seniority_level", mode="before")
    @classmethod
    def _normalize_seniority(cls, v: Any) -> Optional[str]:
        from app.services.seniority import normalize_seniority_level
        return normalize_seniority_level(v)

    @field_validator("qualifications_required", mode="after")
    @classmethod
    def _cap_qualifications(cls, v: list[str]) -> list[str]:
        from app.services.seniority import normalize_qualifications
        return normalize_qualifications(v, max_items=20)

    @field_validator("benefits", mode="after")
    @classmethod
    def _cap_benefits(cls, v: list[str]) -> list[str]:
        # Cap list length AND per-item length so a runaway LLM can't blow up
        # a row. Trim empties/whitespace defensively.
        out: list[str] = []
        for item in v:
            if not isinstance(item, str):
                continue
            s = item.strip()
            if not s:
                continue
            out.append(s[:200])
        return out[:20]

    @field_validator("tools_tech_stack", mode="after")
    @classmethod
    def _cap_tools(cls, v: list[str]) -> list[str]:
        # Same shape as benefits but with the user-specified caps (30 / 80).
        # Lowercased + dedup'd case-insensitively for stable filter queries.
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            if not isinstance(item, str):
                continue
            s = item.strip()
            if not s:
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(s[:80])
        return out[:30]

    @field_validator("source_platform", mode="before")
    @classmethod
    def _normalize_source_platform(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip().lower()
            return s or None
        return str(v).strip().lower() or None

    @field_validator("apply_url", mode="before")
    @classmethod
    def _sanitize_apply_url_field(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            return None
        from app.services.job_quality import sanitize_apply_url
        return sanitize_apply_url(v)

    @field_validator("contact_phone", "contact_whatsapp", mode="before")
    @classmethod
    def _normalize_contact_phone_fields(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            return None
        s = v.strip()
        if not s:
            return None
        if s.lower().startswith(("http://", "https://", "wa.me/", "whatsapp.com/")):
            return s[:64]
        from app.services.description_body_extractor import normalize_zambian_phone
        from app.services.job_quality import sanitize_contact_phone

        candidate = normalize_zambian_phone(s) or s
        validated = sanitize_contact_phone(candidate)
        return validated

    @field_validator("contact_email", mode="before")
    @classmethod
    def _normalize_contact_email(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip().lower()
            return s or None
        return v

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, v: Any) -> Any:
        # Common ISO 4217: ZMW/USD/EUR/GBP. Always uppercase. Empty string
        # → null so the column doesn't carry a bogus "" alongside ZMW rows.
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip().upper()
            return s or None
        return v

    @model_validator(mode="after")
    def _inject_internship_skill(self) -> "JobCreate":
        if self.employment_type == EmploymentType.internship:
            if "Internship" not in self.skills_required:
                self.skills_required.append("Internship")
        return self

class Job(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: str
    description_markdown: Optional[str] = None
    deactivation_reason: Optional[str] = None
    parent_listing_signature: Optional[str] = None
    section_responsibilities: Optional[str] = None
    section_requirements: Optional[str] = None
    section_benefits: Optional[str] = None
    section_how_to_apply: Optional[str] = None
    section_about: Optional[str] = None
    description_html: Optional[str] = None
    section_html: Optional[dict[str, str]] = None
    deep_enriched_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    closure_reason: Optional[str] = None
    requirements: list[str] = []
    skills_required: list[str] = []
    skills: list[str] = []  # Alias for frontend compatibility
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    apply_source: Optional[str] = None
    enrichment_attempted_at: Optional[datetime] = None
    source: str
    source_url: Optional[str] = None
    quality_score: int = 0
    closing_date: Optional[date] = None
    posted_at: datetime
    is_active: bool = True
    visibility_status: Optional[
        Literal["open", "recently_closed", "archived"]
    ] = None

    # ── task #60: richer job ad shape (response) ──────────────────────
    # All optional + null-safe so legacy rows (pre-migration 016) still
    # serialize without error. New columns default NULL on insert.
    employment_type: Optional[EmploymentType] = None
    work_arrangement: Optional[WorkArrangement] = None
    benefits: list[str] = Field(default_factory=list)
    application_instructions: Optional[str] = None
    interview_process: Optional[str] = None
    tools_tech_stack: list[str] = Field(default_factory=list)
    company_description: Optional[str] = None
    reference_number: Optional[str] = None
    currency: Optional[str] = None
    pay_frequency: Optional[PayFrequency] = None
    contact_phone: Optional[str] = None
    admin_published: Optional[bool] = None
    scraping_sources: list[dict[str, str]] = Field(default_factory=list)
    source_platform: Optional[str] = None
    original_source_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_whatsapp: Optional[str] = None
    is_enriched: bool = False

    @field_validator("scraping_sources", mode="before")
    @classmethod
    def _coerce_scraping_sources(cls, v: Any) -> list[dict[str, str]]:
        if v is None:
            return []
        if isinstance(v, list):
            return [dict(item) for item in v if isinstance(item, dict)]
        return []

    @field_validator("benefits", "tools_tech_stack", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        """Legacy rows can have null in jsonb-backed list columns. Coerce
        to empty list rather than 500-ing the /jobs/[id] response."""
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if x is not None and str(x).strip()]
        return []


class JobEnrichPatch(BaseModel):
    """PATCH /jobs/{job_id}/enrich — n8n deep-scrape callback payload."""

    source_platform: Optional[str] = Field(None, max_length=64)
    original_source_url: Optional[str] = Field(None, max_length=2000)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_whatsapp: Optional[str] = Field(None, max_length=64)
    apply_url: Optional[str] = Field(None, max_length=2000)
    apply_email: Optional[str] = Field(None, max_length=255)
    is_enriched: Optional[bool] = True

    model_config = ConfigDict(extra="forbid")

    @field_validator("source_platform", mode="before")
    @classmethod
    def _normalize_source_platform(cls, v: Any) -> Optional[str]:
        return JobCreate._normalize_source_platform(v)

    @field_validator("contact_phone", "contact_whatsapp", mode="before")
    @classmethod
    def _normalize_contact_phone_fields(cls, v: Any) -> Optional[str]:
        return JobCreate._normalize_contact_phone_fields(v)

    @field_validator("contact_email", "apply_email", mode="before")
    @classmethod
    def _normalize_email_fields(cls, v: Any) -> Optional[str]:
        return JobCreate._normalize_contact_email(v)

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "JobEnrichPatch":
        if not self.model_fields_set:
            raise ValueError("At least one enrichment field is required")
        meaningful = {
            k
            for k in self.model_fields_set
            if getattr(self, k) is not None and k != "is_enriched"
        }
        if not meaningful and self.is_enriched is not True:
            raise ValueError("At least one enrichment field is required")
        return self


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

    ``jobs`` is validated row-by-row in the ingest handler so one bad
    scraper row never 422s the entire batch.
    """
    api_key: str
    jobs: list[dict[str, Any]]


class JobIngestErrorItem(BaseModel):
    index: int
    title: str
    reason: str


class JobIngestResponse(BaseModel):
    ingested: int
    duplicates: int
    merged: int = 0
    # Rows the server chose to skip without ingesting AND without erroring.
    # Currently used for cross-listing / aggregator-domain filtering, but
    # the field is intentionally generic so future skip reasons can use
    # the same counter without a schema change. n8n surfaces this in the
    # execution view alongside `ingested` and `duplicates`.
    skipped: int = 0
    errors: list[JobIngestErrorItem] = []


class DeepEnrichJobResultItem(BaseModel):
    """Per-job outcome from a deep-enrich tick (sequential, one at a time)."""

    job_id: str
    title: str | None = None
    outcome: Literal["enriched", "split", "failed", "skipped"]
    detail: str | None = None
    review_cleared: bool | None = None


class DeepEnrichTickResponse(BaseModel):
    """POST /jobs/deep-enrich-tick — deep-enrich batch result."""

    enriched: int
    split: int
    failed: int
    skipped: int = 0
    attempted: int = 0
    results: list[DeepEnrichJobResultItem] = Field(default_factory=list)


# ── Admin CRUD (Wave 4 PR 2) ──────────────────────────────────────────
# AdminJobCreate / AdminJobUpdate back the /api/v1/admin/jobs POST and
# PATCH endpoints. They diverge from JobCreate in three ways:
#   1. Stricter bounds on title/description (1-5000) — admin can post
#      short listings; scraper input usually carries more text.
#   2. `extra='forbid'` — typos in the wizard payload should 422, not
#      silently no-op.
#   3. source defaults to JobSource.manual (admin entries are manual).
# Skill-name input flows through `skills_required` (input-only, routed
# through the Wave 2 resolver in the endpoint), NOT through the
# `requirements` text[] column which carries free-text qualifications.

class AdminJobCreate(JobCreate):
    title: str = Field(..., min_length=1, max_length=5000)
    description: str = Field(..., min_length=1, max_length=5000)
    company: Optional[str] = Field(None, max_length=500)
    source: JobSource = JobSource.manual

    model_config = ConfigDict(extra="forbid")

    @field_validator("requirements", "skills_required", mode="after")
    @classmethod
    def _cap_skill_list(cls, v: list[str]) -> list[str]:
        if len(v) > 50:
            raise ValueError("max 50 items")
        for item in v:
            if not isinstance(item, str) or not (1 <= len(item.strip()) <= 500):
                raise ValueError("each item must be 1-500 chars after trim")
        return v

    @model_validator(mode="after")
    def _check_invariants(self) -> "AdminJobCreate":
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must be <= salary_max")
        has_url = bool(self.apply_url and self.apply_url.strip())
        has_email = bool(self.apply_email and self.apply_email.strip())
        has_phone = bool(self.contact_phone and self.contact_phone.strip())
        if not (has_url or has_email or has_phone):
            raise ValueError(
                "At least one of apply_url, apply_email, or contact_phone is required"
            )
        if has_url and has_email:
            raise ValueError(
                "Provide apply_url or apply_email, not both"
            )
        return self


class AdminJobUpdate(BaseModel):
    """PATCH payload — every field optional, `extra='forbid'` rejects typos.

    Only fields explicitly set in the request are written. Use
    `model_fields_set` at the endpoint to detect "no fields to update"
    and raise 422.
    """

    title: Optional[str] = Field(None, min_length=1, max_length=5000)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    company: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = None
    requirements: Optional[list[str]] = None
    skills_required: Optional[list[str]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    source: Optional[JobSource] = None
    source_url: Optional[str] = None
    closing_date: Optional[date] = None
    posted_at: Optional[date] = None
    employment_type: Optional[EmploymentType] = None
    work_arrangement: Optional[WorkArrangement] = None
    benefits: Optional[list[str]] = None
    application_instructions: Optional[str] = Field(None, max_length=2000)
    interview_process: Optional[str] = Field(None, max_length=1000)
    tools_tech_stack: Optional[list[str]] = None
    company_description: Optional[str] = Field(None, max_length=2000)
    reference_number: Optional[str] = Field(None, max_length=100)
    currency: Optional[str] = Field(None, max_length=3, min_length=3)
    pay_frequency: Optional[PayFrequency] = None
    salary_text: Optional[str] = Field(None, max_length=500)
    # is_active lets admin re-activate a soft-deleted job without a
    # second endpoint. DELETE handles deactivation; PATCH handles the
    # reverse and any other ad-hoc state change.
    is_active: Optional[bool] = None
    admin_published: Optional[bool] = None
    source_platform: Optional[str] = Field(None, max_length=64)
    original_source_url: Optional[str] = Field(None, max_length=2000)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_whatsapp: Optional[str] = Field(None, max_length=64)
    is_enriched: Optional[bool] = None
    experience_min_years: Optional[int] = Field(None, ge=0, le=50)
    seniority_level: Optional[str] = Field(None, max_length=32)
    qualifications_required: Optional[list[str]] = None
    parent_listing_signature: Optional[str] = Field(None, max_length=64)

    model_config = ConfigDict(extra="forbid")

    @field_validator("seniority_level", mode="before")
    @classmethod
    def _normalize_seniority(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        from app.services.seniority import normalize_seniority_level
        return normalize_seniority_level(v)

    @field_validator("qualifications_required", mode="after")
    @classmethod
    def _cap_qualifications(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        from app.services.seniority import normalize_qualifications
        return normalize_qualifications(v, max_items=20)

    @field_validator("source_platform", mode="before")
    @classmethod
    def _normalize_source_platform(cls, v: Any) -> Optional[str]:
        return JobCreate._normalize_source_platform(v)

    @field_validator("contact_phone", "contact_whatsapp", mode="before")
    @classmethod
    def _normalize_contact_phone_fields(cls, v: Any) -> Optional[str]:
        return JobCreate._normalize_contact_phone_fields(v)

    @field_validator("contact_email", mode="before")
    @classmethod
    def _normalize_contact_email(cls, v: Any) -> Optional[str]:
        return JobCreate._normalize_contact_email(v)

    @field_validator("requirements", "skills_required", mode="after")
    @classmethod
    def _cap_skill_list(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        if len(v) > 50:
            raise ValueError("max 50 items")
        for item in v:
            if not isinstance(item, str) or not (1 <= len(item.strip()) <= 500):
                raise ValueError("each item must be 1-500 chars after trim")
        return v

    @model_validator(mode="after")
    def _check_salary(self) -> "AdminJobUpdate":
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must be <= salary_max")
        return self
