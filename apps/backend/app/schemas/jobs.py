"""Job-related Pydantic schemas."""

from pydantic import BaseModel, Field, HttpUrl
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
    closing_date: Optional[date] = None


class Job(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: str
    requirements: list[str] = []
    skills_required: list[str] = []
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    source: str
    quality_score: int = 0
    closing_date: Optional[date] = None
    posted_at: datetime
    is_active: bool = True


class JobList(BaseModel):
    jobs: list[Job]
    total: int
    page: int
    per_page: int
