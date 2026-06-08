"""Shared fixtures for Zed CV backend tests.

Overrides all external dependencies (Supabase, OpenRouter, WhatsApp) so tests
run without network access or real credentials.
"""
import os, sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# -- Mock weasyprint for environments missing GTK/GObject (like Windows dev) -
try:
    import weasyprint
except Exception:
    mock_weasyprint = MagicMock()
    mock_weasyprint.CSS = MagicMock()
    mock_weasyprint.HTML = MagicMock()
    sys.modules["weasyprint"] = mock_weasyprint

import pytest
from fastapi.testclient import TestClient

# -- Fake env vars so Settings() doesn't blow up -------------------------
# Settings (app/core/config.py) requires: SUPABASE_URL, SUPABASE_KEY,
# GEMINI_API_KEY, JWT_SECRET. CI's workflow injects these names directly
# at job level (.github/workflows/ci.yml). Local pytest needs them here.
os.environ["SUPABASE_URL"] = "https://fake.supabase.co"
os.environ["SUPABASE_KEY"] = "fake-service-key"
os.environ["GEMINI_API_KEY"] = "fake-gemini-key"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
# Shared secret for POST /api/v1/jobs/ingest tests
os.environ["INGEST_API_KEY"] = "test-ingest-key"
# DPO Pay merchant token for /webhooks/dpo CompanyToken verification.
# Task #75 added route-level CompanyToken matching; tests must mock the
# parser to emit this exact string so the verify path passes.
os.environ.setdefault("DPO_PAY_COMPANY_TOKEN", "test-dpo-merchant-token")
# Legacy/back-compat — some older tests or services may still read these.
# Cheap to keep; safe to remove in a follow-up cleanup.
os.environ.setdefault("SUPABASE_ANON_KEY", "fake-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake-service-key")
os.environ.setdefault("OPENROUTER_API_KEY", "sk-fake-openrouter")

# Ensure the app package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Windows compatibility: stub weasyprint (requires libgobject unavailable on Windows).
# Must happen BEFORE any import of `app.services.cv_pdf_renderer` fires the weasyprint import.
# On Linux CI, weasyprint is fully installed and this stub is never used.
try:
    import weasyprint
except Exception:
    if "weasyprint" not in sys.modules:
        _wp_stub = MagicMock()
        sys.modules["weasyprint"] = _wp_stub
        sys.modules["weasyprint.CSS"] = _wp_stub
        sys.modules["weasyprint.HTML"] = _wp_stub



# -- Mock Supabase client -------------------------------------------------
class FakeSupabaseQuery:
    """Chainable mock that mimics supabase.table(...).select(...).eq(...) etc."""

    def __init__(self, data=None, count=None):
        self._data = data or []
        self._count = count

    def select(self, *a, **kw):
        return self

    def insert(self, data):
        if self._data:
            return self
        if isinstance(data, dict) and "id" not in data:
            data["id"] = "fake-uuid-001"
        self._data = [data] if isinstance(data, dict) else data
        return self

    def update(self, data):
        return self

    def upsert(self, data, **kw):
        return self

    def delete(self):
        return self

    def eq(self, *a):
        return self

    def neq(self, *a):
        return self

    def gte(self, *a):
        return self

    def lt(self, *a):
        return self

    def lte(self, *a):
        return self

    def ilike(self, *a):
        return self

    def like(self, *a):
        return self

    def or_(self, *a):
        return self

    def in_(self, *a, **kw):
        return self

    def is_(self, *a, **kw):
        return self

    # `.not_.is_("col", "null")` — supabase-py exposes negation as an
    # attribute that proxies the next filter call. Mirror that here so
    # backend code using `query.not_.is_(...)` doesn't AttributeError.
    @property
    def not_(self):
        return self

    def order(self, *a, **kw):
        return self

    def limit(self, *a):
        return self

    def range(self, *a):
        return self

    def single(self):
        return self

    def execute(self):
        result = MagicMock()
        result.data = self._data
        result.count = self._count
        return result


class FakeSupabase:
    """Minimal mock Supabase client."""

    def __init__(self):
        self._tables = {}
        self.storage = MagicMock()
        self.storage.from_ = MagicMock(return_value=MagicMock())

    def table(self, name):
        if name == "jobs_user_facing" and name not in self._tables:
            return self._tables.get("jobs", FakeSupabaseQuery())
        return self._tables.get(name, FakeSupabaseQuery())

    def set_table(self, name, query: "FakeSupabaseQuery"):
        self._tables[name] = query

    def rpc(self, name, args=None, **kw):
        payload = args if args is not None else kw
        if name == "activate_subscription_after_payment":
            return _ActivateSubscriptionRpc(self, payload)
        return FakeSupabaseQuery(data=[True])


class _ActivateSubscriptionRpc:
    """Simulates activate_subscription_after_payment for webhook integration tests."""

    def __init__(self, client: "FakeSupabase", args: dict):
        self._client = client
        self._args = args

    def execute(self):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        period_days = int(self._args.get("p_period_days") or 30)
        existing_raw = self._args.get("p_existing_period_end")
        existing = None
        if existing_raw:
            try:
                existing = datetime.fromisoformat(str(existing_raw).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                existing = None
        base = existing if (existing and existing > now) else now
        period_end = base + timedelta(days=period_days)
        sub_id = self._args.get("p_subscription_id") or "sub-rpc-1"
        user_id = self._args["p_user_id"]
        tier = self._args["p_new_tier"]

        subs = self._client._tables.setdefault("subscriptions", FakeSupabaseQuery())
        if hasattr(subs, "update_calls"):
            subs.update_calls.append(
                {
                    "id": sub_id,
                    "tier": tier,
                    "status": "active",
                    "current_period_start": now.isoformat(),
                    "current_period_end": period_end.isoformat(),
                    "started_at": now.isoformat(),
                    "lenco_subscription_ref": self._args.get("p_lenco_subscription_ref"),
                }
            )
        users = self._client._tables.setdefault("users", FakeSupabaseQuery())
        if hasattr(users, "update_calls"):
            users.update_calls.append(
                {
                    "subscription_tier": tier,
                    "subscription_started_at": now.isoformat(),
                    "subscription_expires_at": period_end.isoformat(),
                    "subscription_renews_at": period_end.isoformat(),
                }
            )

        result = MagicMock()
        result.data = {
            "subscription_id": sub_id,
            "period_start": now.isoformat(),
            "period_end": period_end.isoformat(),
        }
        return result


@pytest.fixture
def fake_supabase():
    return FakeSupabase()


# -- JWT helper ------------------------------------------------------------
@pytest.fixture
def auth_token():
    """Return a valid JWT for user_id='test-user-id'."""
    from jose import jwt

    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "test-user-id",
            "phone": "+260971234567",
            "exp": now + timedelta(hours=24),
            "iat": now,
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_token():
    """Return a valid JWT for admin user."""
    from jose import jwt

    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "admin-user-id",
            "phone": "+260971111111",
            "exp": now + timedelta(hours=24),
            "iat": now,
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# -- App client with mocked deps ------------------------------------------
@pytest.fixture
def client(fake_supabase):
    """TestClient with Supabase and external services mocked out."""
    from app.core.config import get_settings
    from app.core.deps import get_supabase
    from main import app

    # Clear any cached settings so test env vars take effect
    get_settings.cache_clear()

    app.dependency_overrides[get_supabase] = lambda: fake_supabase

    # Also override rate limiter if it exists
    try:
        from app.core.rate_limit import limiter

        limiter.enabled = False
    except (ImportError, AttributeError):
        pass

    # TrustedHostMiddleware rejects TestClient's default host without this.
    default_headers = {"Host": "api.zedapply.com"}
    with TestClient(app, headers=default_headers) as c:
        yield c

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def debug_app(fake_supabase, monkeypatch):
    """Fresh app with DEBUG=true (OpenAPI + /docs enabled)."""
    from app.core.config import get_settings
    from app.core.deps import get_supabase
    from main import create_app

    monkeypatch.setenv("DEBUG", "true")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_supabase] = lambda: fake_supabase
    yield app
    app.dependency_overrides.clear()
    get_settings.cache_clear()
