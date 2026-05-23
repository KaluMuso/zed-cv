from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone
from typing import Any, Optional
from app.schemas.jobs import Job


# v2 component caps (50/20/15/10/5)
SEMANTIC_SCORE_MAX = 50.0
SKILLS_SCORE_MAX = 20.0
EXPERIENCE_SCORE_MAX = 15.0
LOCATION_SCORE_MAX = 10.0
RECENCY_SCORE_MAX = 5.0


class MatchResult(BaseModel):
    id: str
    job: Job
    score: float = Field(..., ge=0, le=100)
    semantic_score: float = Field(
        0, ge=0, le=SEMANTIC_SCORE_MAX, description="Semantic similarity (0–50)"
    )
    skills_score: float = Field(
        0, ge=0, le=SKILLS_SCORE_MAX, description="Required skills overlap (0–20)"
    )
    experience_score: float = Field(
        0, ge=0, le=EXPERIENCE_SCORE_MAX, description="Experience fit (0–15)"
    )
    location_score: float = Field(
        0, ge=0, le=LOCATION_SCORE_MAX, description="Location / remote fit (0–10)"
    )
    recency_score: float = Field(
        0, ge=0, le=RECENCY_SCORE_MAX, description="Job posting recency (0–5)"
    )
    bonus_score: float = Field(
        0,
        ge=0,
        description="Legacy: location_score + recency_score for older clients",
    )
    vector_score: float = Field(
        0, ge=0, description="Alias of semantic_score for legacy clients"
    )
    skill_score: float = Field(
        0, ge=0, description="Alias of skills_score for legacy clients"
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
        legacy_bonus = self.location_score + self.recency_score
        if self.bonus_score == 0 and legacy_bonus > 0:
            object.__setattr__(self, "bonus_score", legacy_bonus)
        return self

    @classmethod
    def from_stored_row(
        cls,
        *,
        job: Job,
        row: dict[str, Any],
        adjusted_score: float | None = None,
        adjusted_bonus: float | None = None,
        explanation: str | None = None,
    ) -> "MatchResult":
        semantic = float(row.get("vector_score") or 0)
        skills = float(row.get("skill_score") or 0)
        experience = float(row.get("experience_score") or 0)
        location = float(row.get("location_score") or 0)
        recency = float(row.get("recency_score") or 0)
        if location == 0 and recency == 0:
            legacy_bonus = float(row.get("bonus_score") or 0)
            location = legacy_bonus
        total = adjusted_score if adjusted_score is not None else float(row.get("score") or 0)
        bonus = adjusted_bonus if adjusted_bonus is not None else location + recency
        return cls(
            id=str(row["id"]),
            job=job,
            score=total,
            semantic_score=semantic,
            skills_score=skills,
            experience_score=experience,
            location_score=location,
            recency_score=recency,
            bonus_score=bonus,
            vector_score=semantic,
            skill_score=skills,
            matched_skills=list(row.get("matched_skills") or []),
            missing_skills=list(row.get("missing_skills") or []),
            explanation=explanation or row.get("explanation"),
            created_at=row["created_at"],
        )

    @classmethod
    def from_rpc_row(
        cls,
        *,
        job: Job,
        row: dict[str, Any],
        match_id: str | None = None,
        created_at: datetime | None = None,
        explanation: str | None = None,
        adjusted_score: float | None = None,
        adjusted_bonus: float | None = None,
    ) -> "MatchResult":
        semantic = float(row.get("semantic_score") or row.get("vector_score") or 0)
        skills = float(row.get("skills_score") or row.get("skill_score") or 0)
        experience = float(row.get("experience_score") or 0)
        location = float(row.get("location_score") or 0)
        recency = float(row.get("recency_score") or 0)
        if location == 0 and recency == 0:
            legacy_bonus = float(row.get("bonus_score") or 0)
            location = legacy_bonus
        total = adjusted_score if adjusted_score is not None else float(
            row.get("score") or row.get("final_score") or 0
        )
        bonus = adjusted_bonus if adjusted_bonus is not None else location + recency
        return cls(
            id=match_id or str(row["job_id"]),
            job=job,
            score=total,
            semantic_score=semantic,
            skills_score=skills,
            experience_score=experience,
            location_score=location,
            recency_score=recency,
            bonus_score=bonus,
            vector_score=semantic,
            skill_score=skills,
            matched_skills=list(row.get("matched_skills") or []),
            missing_skills=list(row.get("missing_skills") or []),
            explanation=explanation or row.get("explanation"),
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
