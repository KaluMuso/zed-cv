"""Matching-related Pydantic schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from app.schemas.jobs import Job


class MatchResult(BaseModel):
    id: str
    job: Job
    score: float = Field(..., ge=0, le=100)
    vector_score: float = 0
    skill_score: float = 0
    bonus_score: float = 0
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    explanation: Optional[str] = None
    created_at: datetime


class MatchList(BaseModel):
    matches: list[MatchResult]
    remaining_quota: int
