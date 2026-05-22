from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone
from typing import Any, Optional
from app.schemas.jobs import Job


class MatchResult(BaseModel):
    id: str
    job: Job
    score: float = Field(..., ge=0, le=100)
    semantic_score: float = Field(
        0, ge=0, description="Semantic similarity component (0–60 under 60/30/10 RPC)"
    )
    skills_score: float = Field(
        0, ge=0, description="Skills overlap component (0–30 under 60/30/10 RPC)"
    )
    bonus_score: float = Field(
        0, ge=0, description="Location/salary bonus (0–10 under 60/30/10 RPC)"
    )
    vector_score: float = Field(
        0, ge=0, description="Alias of semantic_score for legacy clients"
    )
    skill_score: float = Field(
        0, ge=0, description="Alias of skills_score for legacy clients"
    )
    experience_score: Optional[float] = Field(
        None, ge=0.5, le=1.0, description="Experience-gap multiplier (informational)"
    )
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    explanation: Optional[str] = None
    created_at: datetime

    @model_validator(mode="after")
    def _sync_score_aliases(self) -> "MatchResult":
        if self.vector_score == 0 and self.semantic_score:
            object.__setattr__(self, "vector_score", self.semantic_score)
        if self.skill_score == 0 and self.skills_score:
            object.__setattr__(self, "skill_score", self.skills_score)
        if self.semantic_score == 0 and self.vector_score:
            object.__setattr__(self, "semantic_score", self.vector_score)
        if self.skills_score == 0 and self.skill_score:
            object.__setattr__(self, "skills_score", self.skill_score)
        return self

    @classmethod
    def from_rpc_row(
        cls,
        *,
        job: Job,
        row: dict[str, Any],
        match_id: str | None = None,
        created_at: datetime | None = None,
        explanation: str | None = None,
    ) -> "MatchResult":
        semantic = float(row.get("vector_score") or 0)
        skills = float(row.get("skill_score") or 0)
        bonus = float(row.get("bonus_score") or 0)
        total = float(row.get("final_score") or (semantic + skills + bonus))
        return cls(
            id=match_id or str(row["job_id"]),
            job=job,
            score=total,
            semantic_score=semantic,
            skills_score=skills,
            bonus_score=bonus,
            vector_score=semantic,
            skill_score=skills,
            experience_score=row.get("experience_score"),
            matched_skills=list(row.get("matched_skills") or []),
            missing_skills=list(row.get("missing_skills") or []),
            explanation=explanation,
            created_at=created_at or datetime.now(timezone.utc),
        )

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
