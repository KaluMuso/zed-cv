"""Schemas for admin endpoints."""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.core.phone import normalize_zambian_e164_phone


class AdminScraperStatsDay(BaseModel):
    date: str
    accepted_as_job: int = 0
    rejected_as_promo: int = 0
    rejected_as_other: int = 0


class AdminParserStats(BaseModel):
    parser: str
    attempted: int = 0
    found_email: int = 0
    found_phone: int = 0
    failed: int = 0


class AdminScraperStats(BaseModel):
    days: list[AdminScraperStatsDay] = Field(default_factory=list)
    accepted_as_job: int = 0
    rejected_as_promo: int = 0
    rejected_as_other: int = 0
    parsers: list[AdminParserStats] = Field(default_factory=list)


class AdminLlmCostByModel(BaseModel):
    model: str
    cost_usd: float = 0.0
    request_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class AdminLlmCostByFeature(BaseModel):
    feature: str
    cost_usd: float = 0.0
    request_count: int = 0


class AdminLlmCostDay(BaseModel):
    date: str
    cost_usd: float = 0.0


class AdminLlmCostStats(BaseModel):
    """Rolling LLM inference cost (OpenRouter + Gemini + OpenAI)."""

    days: int = 7
    total_cost_usd: float = 0.0
    total_requests: int = 0
    by_model: list[AdminLlmCostByModel] = Field(default_factory=list)
    by_feature: list[AdminLlmCostByFeature] = Field(default_factory=list)
    daily: list[AdminLlmCostDay] = Field(default_factory=list)


class AdminStats(BaseModel):
    users_total: int = 0
    users_active_30d: int = 0
    subscriptions_active: int = 0
    subscriptions_paid: int = 0
    jobs_total: int = 0
    jobs_active: int = 0
    jobs_expired: int = 0
    jobs_deactivated: int = 0
    jobs_need_review: int = 0
    jobs_active_public: int = 0
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
    welcome_match_bonus: Optional[int] = None
    welcome_match_bonus_until: Optional[datetime] = None
    created_at: Optional[datetime] = None


class AdminWelcomeBonusUpdate(BaseModel):
    welcome_match_bonus: Optional[int] = Field(None, ge=1, le=999)
    welcome_match_bonus_until: Optional[datetime] = None


class AdminRepairDeliveryRequest(BaseModel):
    reset_month_credits: bool = Field(
        True,
        description="Clear credited_at for this billing month, then re-credit up to tier limit.",
    )
    apply_welcome: bool = Field(
        True,
        description="For free tier: set welcome bonus 7 and extend window if missing/expired.",
    )


class AdminRepairDeliveryResponse(BaseModel):
    user_id: str
    tier: str
    matches_limit: int
    credited_before: int
    credited_after: int
    credits_reset_this_month: int
    newly_credited_job_ids: list[str] = Field(default_factory=list)
    welcome_bonus_updated: bool = False


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
    source_url: Optional[str] = None
    apply_url: Optional[str] = None
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


class AdminScrapeLinkRequest(BaseModel):
    url: str = Field(..., max_length=1000)


class AdminScrapeLinkResponse(BaseModel):
    jobs_found: int
    jobs_ingested: int
    details: list[str]


class BulkDeactivateResponse(BaseModel):
    deactivated: int


class AdminJobReviewRow(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    description: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    reasons: list[str] = []
    is_active: bool = False
    created_at: Optional[datetime] = None


class AdminJobReviewQueue(BaseModel):
    jobs: list[AdminJobReviewRow]
    total: int
    page: int
    per_page: int
    pages: int


class AdminReviewQueueOverview(BaseModel):
    """Counters for admin review backlog vs customer-visible jobs."""

    need_review: int = 0
    deactivated: int = 0
    active_public: int = 0
    auto_dismiss_hidden_eligible: int = 0
    dismiss_expired_eligible: int = 0
    dismiss_junk_eligible: int = 0
    active_no_deadline_pending: int = 0


class AdminJobReviewUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    company: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, min_length=20)
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
    provider_ref: Optional[str] = None
    invoice_number: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AdminPaymentDetail(AdminPaymentRow):
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    webhook_summary: Optional[dict] = None
    tier_inferred: Optional[str] = None


class AdminBillingHealth(BaseModel):
    lenco_environment: str
    lenco_api_url: str
    lenco_api_key_set: bool
    lenco_public_key_set: bool
    lenco_webhook_secret_set: bool
    lenco_verify_signatures: bool
    lenco_production_ready: bool
    webhook_url_expected: str
    payments_pending: int
    payments_failed_24h: int
    payments_completed_24h: int
    lenco_completed_24h: int
    subscriptions_cancelling: int
    checked_at: datetime


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
    cancelled_at: Optional[datetime] = None
    lenco_subscription_ref: Optional[str] = None
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


class AdminContactFixJobRow(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    source_url: Optional[str] = None
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    contact_phone: Optional[str] = None
    posted_at: Optional[datetime] = None


class AdminContactFixJobList(BaseModel):
    jobs: list[AdminContactFixJobRow]
    total: int
    page: int
    per_page: int
    pages: int
    fixed_count: int = Field(
        0,
        description="Jobs no longer in queue (approx. total_at_start - total remaining)",
    )


class AdminJobContactPatch(BaseModel):
    apply_url: Optional[str] = Field(None, max_length=2000)
    apply_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)
    mark_uncontactable: bool = False
    reason: Optional[str] = Field(
        None,
        max_length=120,
        description="Optional note when mark_uncontactable=true",
    )

    @field_validator("contact_phone", mode="before")
    @classmethod
    def _normalize_phone(cls, value: object) -> Optional[str]:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return normalize_zambian_e164_phone(str(value))


class AdminSubscriptionMetrics(BaseModel):
    mrr_kwacha: float = Field(
        description="Monthly recurring revenue (ZMW) from active subs × tier_config.price_ngwee",
    )
    mrr_ngwee: int = 0
    active_subscriptions: int = 0
    cancelled_this_month: int = 0
    active_at_month_start: int = 0
    churn_rate: float = Field(
        0.0,
        description="cancelled_this_month / active_at_month_start (0–1)",
    )
    month_start: str


class DailyDigestMessage(BaseModel):
    user_id: str
    phone: str
    message: str

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, value: object) -> str:
        return normalize_zambian_e164_phone(str(value))


class DailyDigestBatchResponse(BaseModel):
    messages: list[DailyDigestMessage] = Field(default_factory=list)


class DailyDigestSendResponse(BaseModel):
    """Summary after the backend sends a daily digest batch (email or WhatsApp)."""

    sent: int = 0
    skipped: int = 0
    failed: int = 0
    quiet_hours_skipped: int = 0


class RenewalReminderSendResponse(BaseModel):
    sent: int = 0
    skipped: int = 0
    failed: int = 0
