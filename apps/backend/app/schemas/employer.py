"""Pydantic models for the employer portal API."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class EmployerSizeBand(str, Enum):
    s1_10 = "1-10"
    s11_50 = "11-50"
    s51_200 = "51-200"
    s201_1000 = "201-1000"
    s1000_plus = "1000+"


class EmployerUserRole(str, Enum):
    owner = "owner"
    admin = "admin"
    recruiter = "recruiter"
    viewer = "viewer"


class EmployerTier(str, Enum):
    lite = "lite"
    pro = "pro"


class ContactChannel(str, Enum):
    whatsapp = "whatsapp"
    email = "email"
    both = "both"


# Prices in ngwee (K500 = 50000, K2500 = 250000).
EMPLOYER_TIER_PRICES: dict[str, int] = {
    "lite": 50000,
    "pro": 250000,
}

EMPLOYER_CONTACT_LIMITS: dict[str, int] = {
    "lite": 5,
    "pro": 99999,
}


class EmployerRegisterBody(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200)
    industry: Optional[str] = Field(None, max_length=120)
    size_band: Optional[EmployerSizeBand] = None
    website: Optional[str] = Field(None, max_length=500)


class EmployerSummary(BaseModel):
    id: str
    company_name: str
    industry: Optional[str] = None
    size_band: Optional[str] = None
    website: Optional[str] = None
    verified: bool = False
    created_at: Optional[datetime] = None


class EmployerSeat(BaseModel):
    id: str
    user_id: str
    role: EmployerUserRole
    invited_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    invite_email: Optional[str] = None


class EmployerMeResponse(BaseModel):
    employer: EmployerSummary
    seats: list[EmployerSeat]
    my_role: EmployerUserRole


class EmployerInviteBody(BaseModel):
    email: EmailStr
    role: EmployerUserRole = EmployerUserRole.recruiter


class EmployerInviteResponse(BaseModel):
    seat_id: str
    email: str
    role: EmployerUserRole
    message: str


class CandidatePreview(BaseModel):
    candidate_id: str
    headline: Optional[str] = None
    location: Optional[str] = None
    years_experience: Optional[int] = None
    skills: list[str] = Field(default_factory=list)
    match_hint: Optional[str] = None


class CandidateSearchResponse(BaseModel):
    results: list[CandidatePreview]
    total: int


class ContactRequestBody(BaseModel):
    message_text: str = Field(..., min_length=10, max_length=2000)
    channel: ContactChannel = ContactChannel.both


class ContactRequestRow(BaseModel):
    id: str
    candidate_user_id: str
    message_text: str
    channel: str
    sent_at: Optional[datetime] = None
    candidate_responded_at: Optional[datetime] = None
    candidate_consented: Optional[bool] = None
    status: str
    candidate_phone: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None


class ContactStatusSummary(BaseModel):
    pending: int = 0
    consented: int = 0
    declined: int = 0
    expired: int = 0
    draft: int = 0
    unavailable: int = 0
    total: int = 0


class EmployerContactsResponse(BaseModel):
    contacts: list[ContactRequestRow]
    total: int
    summary: ContactStatusSummary


class EmployerSubscriptionResponse(BaseModel):
    tier: Optional[EmployerTier] = None
    status: str
    active: bool
    current_period_end: Optional[datetime] = None
    contacts_used: int = 0
    contacts_limit: int = 0
    price_ngwee: int = 0


class EmployerCheckoutBody(BaseModel):
    tier: EmployerTier


class EmployerCheckoutResponse(BaseModel):
    reference: str
    amount_ngwee: int
    tier: EmployerTier
    public_key: str
    label: str = "ZedApply Employer"


class EmployerVerifyPaymentBody(BaseModel):
    reference: str = Field(..., min_length=8, max_length=128)
    tier: EmployerTier


class EmployerVerifyPaymentResponse(BaseModel):
    status: str
    tier: str
    reference: str
    message: str
