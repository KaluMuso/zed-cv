"""Pydantic models for deletion, export, and consent (Bucket 9)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ConsentType = Literal[
    "terms_of_service",
    "privacy_policy",
    "marketing_email",
    "marketing_whatsapp",
    "analytics_cookies",
    "third_party_data_sharing",
]


class SensitiveActionBody(BaseModel):
    """OTP step-up required for delete/export requests."""

    otp_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class DeletionRequestResponse(BaseModel):
    request_id: Optional[str] = None
    status: str
    scheduled_at: str


class DeletionCancelResponse(BaseModel):
    request_id: str
    status: str


class ExportRequestResponse(BaseModel):
    request_id: Optional[str] = None
    status: str


class ExportStatusResponse(BaseModel):
    request_id: str
    status: str
    download_url: Optional[str] = None
    download_expires_at: Optional[str] = None
    generated_at: Optional[str] = None
    failure_reason: Optional[str] = None


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
