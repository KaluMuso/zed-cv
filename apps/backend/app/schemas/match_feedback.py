"""User feedback when hiding a job match."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

MatchDismissReason = Literal[
    "not_relevant",
    "wrong_location",
    "salary_too_low",
    "experience_mismatch",
    "already_applied",
    "other",
]

VALID_DISMISS_REASONS = frozenset(
    {
        "not_relevant",
        "wrong_location",
        "salary_too_low",
        "experience_mismatch",
        "already_applied",
        "other",
    }
)


class MatchDismissRequest(BaseModel):
    reason: Optional[MatchDismissReason] = Field(
        None,
        description="Optional not-interested reason for product tuning.",
    )


class MatchDismissResponse(BaseModel):
    match_id: str
    status: str = "dismissed"
    reason: Optional[str] = None
