"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """All settings are loaded from .env or environment variables."""

    # App
    app_name: str = "Zed CV API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # OpenAI (embeddings)
    openai_api_key: str

    # Anthropic (CV parsing, cover letters)
    anthropic_api_key: str = ""

    # DPO Pay
    dpo_pay_company_token: str = ""
    dpo_pay_service_type: str = ""
    dpo_pay_api_url: str = "https://secure.3gdirectpay.com/API/v6/"

    # WAHA (WhatsApp)
    waha_api_url: str = "http://localhost:3000"
    waha_api_key: str = ""

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Matching
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    min_match_score: float = 50.0

    # Rate limits
    otp_cooldown_seconds: int = 60
    max_otp_attempts: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
