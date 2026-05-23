"""Pydantic models for canonical_skills and raw_skill_mappings."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CanonicalSkill(BaseModel):
    id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    parent_skill: str | None = Field(default=None, max_length=200)
    notes: str | None = None
    created_at: datetime | None = None


class RawSkillMapping(BaseModel):
    id: UUID
    raw_name: str = Field(..., min_length=1, max_length=200)
    canonical_id: UUID | None = None
    occurrences: int = Field(..., ge=1)


class PendingRawSkillRow(BaseModel):
    id: UUID
    raw_name: str
    occurrences: int


class PendingRawSkillsResponse(BaseModel):
    pending: list[PendingRawSkillRow]


class MergeRawSkillRequest(BaseModel):
    raw_skill_id: UUID
    canonical_skill_name: str = Field(..., min_length=1, max_length=200)


class MergeRawSkillResponse(BaseModel):
    raw_skill_id: UUID
    canonical_skill: CanonicalSkill
    mapping: RawSkillMapping
