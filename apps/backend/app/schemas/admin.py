"""Schemas for admin endpoints."""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class AdminScraperStatsDay(BaseModel):
    date: str
    accepted_as_job: int = 0
    rejected_as_promo: int = 0
    rejected_as_other: int = 0


class AdminScraperStats(BaseModel):
    days: list[AdminScraperStatsDay] = Field(default_factory=list)
    accepted_as_job: int = 0
    rejected_as_promo: int = 0
    rejected_as_other: int = 0


class AdminStats(BaseModel):
    users_total: int = 0
    users_active_30d: int = 0
    subscriptions_active: int = 0
    subscriptions_paid: int = 0
    jobs_total: int = 0
    jobs_active: int = 0
    jobs_expired: int = 0
    matches_24h: int = 0
    matches_total: int = 0
    revenue_ngwee_30d: int = 0
    revenue_ngwee_total: int = 0
    pending_review_count: int = 0


class AdminUserRow(BaseModel):
    id: str
    phone: str
    full_name: Optional[str] = None
    location: Optional[str] = None
    subscription_tier: str = "free"
    role: str = "user"
    matches_used: int = 0
    matches_limit: int = 0
    created_at: Optional[datetime] = None


class AdminUserList(BaseModel):
    users: list[AdminUserRow]
    total: int
    page: int
    per_page: int
    pages: int


class AdminJobRow(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    source: str
    quality_score: int = 0
    is_active: bool = True
    closing_date: Optional[str] = None
    posted_at: Optional[datetime] = None


class AdminJobList(BaseModel):
    jobs: list[AdminJobRow]
    total: int
    page: int
    per_page: int
    pages: int


class BulkDeactivateRequest(BaseModel):
    job_ids: list[str] = Field(default_factory=list, max_length=500)
    expired_only: bool = False


class BulkDeactivateResponse(BaseModel):
    deactivated: int


class AdminJobReviewRow(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    reasons: list[str] = []
    created_at: Optional[datetime] = None


class AdminJobReviewQueue(BaseModel):
    jobs: list[AdminJobReviewRow]
    total: int
    page: int
    per_page: int
    pages: int


class AdminJobReviewUpdate(BaseModel):
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    closing_date: Optional[date] = None
    application_instructions: Optional[str] = Field(None, max_length=2000)


class AdminPaymentRow(BaseModel):
    id: str
    user_id: str
    user_phone: Optional[str] = None
    amount: int
    currency: str = "ZMW"
    payment_method: str
    provider: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AdminPaymentList(BaseModel):
    payments: list[AdminPaymentRow]
    total: int
    page: int
    per_page: int
    pages: int
    total_completed_ngwee: int = 0


class AdminMatchRow(BaseModel):
    id: str
    user_id: str
    user_phone: Optional[str] = None
    job_id: str
    job_title: str
    job_company: Optional[str] = None
    score: float
    status: Optional[str] = None
    created_at: Optional[datetime] = None


class AdminMatchList(BaseModel):
    matches: list[AdminMatchRow]
    total: int
    page: int
    per_page: int
    pages: int


class AdminTierBreakdown(BaseModel):
    free: int = 0
    starter: int = 0
    professional: int = 0
    super_standard: int = 0
    total_active: int = 0


class AdminSubscriptionRow(BaseModel):
    user_id: str
    user_phone: Optional[str] = None
    full_name: Optional[str] = None
    tier: str
    status: str
    matches_used: int = 0
    matches_limit: int = 0
    current_period_end: Optional[datetime] = None
    created_at: Optional[datetime] = None


class AdminSubscriptionList(BaseModel):
    breakdown: AdminTierBreakdown
    subscriptions: list[AdminSubscriptionRow]
    total: int
    page: int
    per_page: int
    pages: int


class AdminSubscriptionUpdate(BaseModel):
    tier: str = Field(..., pattern="^(free|starter|professional|super_standard)$")
