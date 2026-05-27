"""Tests for Lenco production fail-fast startup and sandbox allowances."""
from __future__ import annotations

import hashlib
import os

import pytest


def _clear_settings_cache() -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_lenco_env(monkeypatch):
    """Keep Lenco env neutral unless a test overrides it."""
    monkeypatch.delenv("LENCO_ENVIRONMENT", raising=False)
    monkeypatch.delenv("LENCO_VERIFY_SIGNATURES", raising=False)
    monkeypatch.delenv("LENCO_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("LENCO_API_KEY", raising=False)
    monkeypatch.delenv("LENCO_PUBLIC_KEY", raising=False)
    _clear_settings_cache()
    yield
    _clear_settings_cache()


class TestLencoProductionStartup:
    def test_production_missing_webhook_secret_refuses_startup(self, monkeypatch):
        from main import create_app

        monkeypatch.setenv("LENCO_ENVIRONMENT", "production")
        monkeypatch.setenv("LENCO_VERIFY_SIGNATURES", "true")
        monkeypatch.setenv("LENCO_WEBHOOK_SECRET", "")
        monkeypatch.setenv("LENCO_API_KEY", "prod-api-key")
        monkeypatch.setenv("LENCO_PUBLIC_KEY", "pub-prod-key")
        _clear_settings_cache()

        with pytest.raises(AssertionError, match="WEBHOOK_SECRET"):
            create_app()

    def test_production_missing_verify_signatures_refuses_startup(self, monkeypatch):
        from main import create_app

        api_key = "prod-api-key"
        webhook_secret = hashlib.sha256(api_key.encode()).hexdigest()
        monkeypatch.setenv("LENCO_ENVIRONMENT", "production")
        monkeypatch.setenv("LENCO_VERIFY_SIGNATURES", "false")
        monkeypatch.setenv("LENCO_WEBHOOK_SECRET", webhook_secret)
        monkeypatch.setenv("LENCO_API_KEY", api_key)
        monkeypatch.setenv("LENCO_PUBLIC_KEY", "pub-prod-key")
        _clear_settings_cache()

        with pytest.raises(AssertionError, match="VERIFY_SIGNATURES"):
            create_app()

    def test_sandbox_allows_empty_webhook_secret(self, monkeypatch):
        from main import create_app

        monkeypatch.setenv("LENCO_ENVIRONMENT", "sandbox")
        monkeypatch.setenv("LENCO_WEBHOOK_SECRET", "")
        monkeypatch.setenv("LENCO_VERIFY_SIGNATURES", "true")
        _clear_settings_cache()

        app = create_app()
        assert app.title == "Zed CV API"

    def test_production_with_full_config_starts(self, monkeypatch):
        from main import create_app

        api_key = "prod-api-key"
        webhook_secret = hashlib.sha256(api_key.encode()).hexdigest()
        monkeypatch.setenv("LENCO_ENVIRONMENT", "production")
        monkeypatch.setenv("LENCO_VERIFY_SIGNATURES", "true")
        monkeypatch.setenv("LENCO_WEBHOOK_SECRET", webhook_secret)
        monkeypatch.setenv("LENCO_API_KEY", api_key)
        monkeypatch.setenv("LENCO_PUBLIC_KEY", "pub-prod-key")
        _clear_settings_cache()

        app = create_app()
        assert app.title == "Zed CV API"


class TestLencoProductionStartupCli:
    """Simulate `LENCO_ENVIRONMENT=production` with empty secret at import."""

    def test_local_production_empty_secret_refuses_start(self, monkeypatch):
        from app.core.config import Settings
        from app.core.lenco_startup import assert_lenco_production_ready

        monkeypatch.setenv("LENCO_ENVIRONMENT", "production")
        monkeypatch.setenv("LENCO_VERIFY_SIGNATURES", "true")
        monkeypatch.setenv("LENCO_WEBHOOK_SECRET", "")
        monkeypatch.setenv("LENCO_API_KEY", "key")
        monkeypatch.setenv("LENCO_PUBLIC_KEY", "pub")
        _clear_settings_cache()

        settings = Settings(
            supabase_url=os.environ["SUPABASE_URL"],
            supabase_key=os.environ["SUPABASE_KEY"],
            gemini_api_key=os.environ["GEMINI_API_KEY"],
            jwt_secret=os.environ["JWT_SECRET"],
        )
        with pytest.raises(AssertionError, match="WEBHOOK_SECRET"):
            assert_lenco_production_ready(settings)
