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
    experience_score: Optional[float] = Field(
        None, ge=0.5, le=1.0, description="Experience-gap multiplier at match time"
    )
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    explanation: Optional[str] = None
    created_at: datetime

class MatchList(BaseModel):
    matches: list[MatchResult]
    remaining_quota: int
    credited_count: int = 0
    matches_limit: int = 10


class CronTickResponse(BaseModel):
    users_processed: int
    new_matches_total: int


class NotificationDigestResponse(BaseModel):
    users_processed: int
    notifications_sent: int
