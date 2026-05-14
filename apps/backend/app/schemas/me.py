"""Pydantic schemas for the data-subject-rights endpoints (task #63)."""
from typing import Optional
from pydantic import BaseModel, Field


class AccountDeletionRequest(BaseModel):
    """Request body for DELETE /api/v1/me.

    The `confirm_phone` field is compared byte-for-byte against the
    authenticated user's phone in the DB. A mismatch returns 400.

    AI-safety: this value MUST NOT be passed through any LLM. The
    comparison is a constant-time bytes equality check in the route
    handler — no parsing, no normalisation, no model in the loop.
    """

    confirm_phone: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description=(
            "Caller types their full phone number, including the +260 "
            "country code, to confirm the destructive action."
        ),
    )


class AccountDeletionResult(BaseModel):
    """Response body for DELETE /api/v1/me."""

    deleted: bool
    already_deleted: bool = False
    user_id: Optional[str] = None
