"""Business profile schemas for /business-profile CRUD (PR N1).

A business_profiles row is one-to-one with users (same primary key) so a user
has at most one business profile. Used by /tenders/matches RPC to embed the
user's company description and match against tender embeddings.
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class BusinessProfileBase(BaseModel):
    """Shared fields used across Create/Update/Response."""

    company_name: str = Field(..., min_length=2, max_length=200)
    phone_number: str = Field(..., min_length=10, max_length=20)
    industry_tags: list[str] = Field(default_factory=list, max_length=20)
    operating_provinces: list[str] = Field(default_factory=list, max_length=10)
    company_bio: str | None = Field(None, max_length=2000)


class BusinessProfileCreate(BusinessProfileBase):
    """Payload for PUT /business-profile when no row exists yet.

    Required fields enforced via base class. The user's UUID is taken from
    the auth token, not the payload, so attackers can't spoof a profile
    for someone else.
    """
    model_config = ConfigDict(extra="forbid")


class BusinessProfileUpdate(BaseModel):
    """Payload for PUT /business-profile when a row already exists.

    Every field optional — partial updates allowed. `extra='forbid'` so
    typos surface as 422 rather than silent no-ops.
    """

    company_name: str | None = Field(None, min_length=2, max_length=200)
    phone_number: str | None = Field(None, min_length=10, max_length=20)
    industry_tags: list[str] | None = Field(None, max_length=20)
    operating_provinces: list[str] | None = Field(None, max_length=10)
    company_bio: str | None = Field(None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class BusinessProfileResponse(BusinessProfileBase):
    """Returned shape from GET / PUT."""

    id: str  # UUID — same as user.id
    created_at: datetime
    updated_at: datetime
