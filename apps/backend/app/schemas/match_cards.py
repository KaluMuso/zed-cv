"""Pydantic schemas for forwardable match cards."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateMatchShareResponse(BaseModel):
    """Returned from POST /api/v1/matches/{match_id}/share."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., description="Short urlsafe token used in the share URL.")
    share_url: str = Field(..., description="Canonical share URL the sender can forward.")
    is_new: bool = Field(
        default=False,
        description="True if this call created a new share row, False if a prior share was reused.",
    )


class PublicMatchCard(BaseModel):
    """Blurred public preview for the recipient at /m/<token>.

    Intentionally minimal: no contact info, no match_id, no user_id.
    Sender's first name + referral_code are the only attribution data
    surfaced, and they're already public-by-design (referral_code is the
    public invite identifier).
    """

    model_config = ConfigDict(extra="forbid")

    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    score: int = Field(..., ge=0, le=100, description="Match score 0-100.")
    matched_skills_count: int = Field(0, ge=0)
    top_matched_skills: list[str] = Field(default_factory=list, max_length=3)
    sender_first_name: Optional[str] = None
    sender_referral_code: Optional[str] = None
    created_at: Optional[str] = None
