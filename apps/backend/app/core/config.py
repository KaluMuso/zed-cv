"""Application configuration from environment variables."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Zed CV API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Supabase
    supabase_url: str
    supabase_key: str  # service_role key for backend

    # AI: Embeddings (Google Gemini)
    # gemini-embedding-001 is the current modern model (native 3072 dim,
    # supports Matryoshka truncation via outputDimensionality). The older
    # text-embedding-004 was retired from v1beta in 2026-05; do not set
    # EMBEDDING_MODEL to text-embedding-* on production.
    gemini_api_key: str
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768

    # AI: LLM via OpenRouter
    # Stable OpenRouter slug for Gemini 2.0 Flash. The shorthand
    # 'google/gemini-flash-2.0' (without version suffix) is rejected by
    # OpenRouter with 400 BadRequestError. Use ':free' suffix for the
    # zero-cost experimental tier, or the -001 stable model below.
    openrouter_api_key: str = ""
    llm_model: str = "google/gemini-2.0-flash-001"

    # Payments
    dpo_pay_company_token: str = ""
    dpo_pay_service_type: str = ""
    dpo_pay_api_url: str = "https://secure.3gdirectpay.com/API/v6/"
    lenco_api_key: str = ""
    # Default to v2 sandbox so a fresh dev env points at the right URL. Prod
    # overrides via .env on OCI. Lenco v2 deprecates the v1 path; the email
    # received 2026-05-12 only ships v2 sandbox URLs.
    lenco_api_url: str = "https://sandbox.lenco.co/access/v2"
    # Optional dedicated webhook signing secret. If empty, the webhook
    # handler falls back to verifying signatures with `lenco_api_key`,
    # which matches Lenco's documented signing behaviour when no
    # dedicated secret is provisioned in the dashboard.
    lenco_webhook_secret: str = ""

    # WhatsApp (WAHA)
    waha_api_url: str = "http://localhost:3001"
    waha_api_key: str = ""

    # WhatsApp channel ingest (Slice F).
    # When `whatsapp_jobs_ingest_enabled` is True and a webhook message's
    # chatId/from contains `whatsapp_channel_jobs_id`, the message body is
    # routed to job_extractor.py (Gemini structured output) instead of the
    # user-command handler. The extracted JobCreate is fed through the same
    # ingest pipeline as the n8n scraper. Default OFF so the feature can be
    # A/B'd against real channel traffic before flipping it on.
    # The ID format is `<id>@newsletter` for WhatsApp channels; we match by
    # substring so the env var can be set to either the full chatId or just
    # the numeric prefix.
    whatsapp_channel_jobs_id: str = ""
    whatsapp_jobs_ingest_enabled: bool = False

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Matching
    min_match_score: float = 50.0

    # Scraper / Ingest
    # Shared secret in JSON body of POST /api/v1/jobs/ingest.
    # n8n's "Zambia Job Scraper" workflow includes this as `api_key`.
    # Leave empty in dev to disable the ingest endpoint entirely.
    ingest_api_key: str = ""
    # Comma-separated list of aggregator/cross-listing domains to filter
    # at the /ingest boundary. The scraper sometimes pulls in jobs that
    # were originally listed elsewhere (e.g. a Zambian-tagged role on
    # zimbojobs.com that points its apply_url at a Zimbabwean board);
    # those are noise for our matching. Comma-separated rather than a
    # list because pydantic-settings does not parse list[str] from env
    # vars without a JSON wrapper. Matched substring-style against both
    # apply_url and source_url, case-insensitive.
    aggregator_domains_blacklist: str = "zimbojobs.com,zimworx.com,zimworx.co.zw"

    # OTP
    otp_cooldown_seconds: int = 60
    max_otp_attempts: int = 5
    # OTP code is N decimal digits, generated with secrets.randbelow(10).
    # Changing this is a schema-friendly change but invalidates any
    # already-issued unverified codes the moment the new build deploys.
    otp_code_length: int = 6
    otp_expire_minutes: int = 5
    # Refresh JWT TTL. Bumped/lowered here without touching auth.py.
    refresh_token_expire_days: int = 30
    # Length of a paid subscription cycle in days. Drives DPO + Lenco
    # webhook upgrade flows. Used twice in webhooks.py so kept here to
    # avoid drift between providers.
    subscription_period_days: int = 30
    # Highest job index a user can reply with on WhatsApp ("reply 1-5").
    # Aligned with send_match_digest which renders the top 5 matches.
    whatsapp_reply_max_index: int = 5

    # Superadmin phone (initial bootstrap)
    superadmin_phone: str = ""

    # Email (Resend)
    resend_api_key: str = ""
    resend_from_email: str = "Zed CV <noreply@zedcv.com>"
    app_url: str = "https://zedcv.com"

    # Observability (Sentry)
    # If sentry_dsn is empty, Sentry init is a no-op. Set in prod env only.
    sentry_dsn: str = ""
    sentry_environment: str = "production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
