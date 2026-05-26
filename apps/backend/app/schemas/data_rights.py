"""Pydantic models for consent audit log (privacy settings)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

ConsentType = Literal[
    "terms_of_service",
    "privacy_policy",
    "marketing_email",
    "marketing_whatsapp",
    "analytics_cookies",
    "third_party_data_sharing",
]


class ConsentUpdateBody(BaseModel):
    consent_type: ConsentType
    granted: bool


class ConsentRecordResponse(BaseModel):
    consent_type: ConsentType
    granted: bool
    granted_at: str
    legal_doc_version: Optional[str] = None


class ConsentUpdateResponse(BaseModel):
    consent: ConsentRecordResponse


class ConsentStatusResponse(BaseModel):
    """Latest granted flag per consent type (defaults when no log row)."""

    consents: dict[str, bool]
    last_updated: dict[str, str]
