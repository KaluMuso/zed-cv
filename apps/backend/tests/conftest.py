"""Shared fixtures for Zed CV backend tests.

Overrides all external dependencies (Supabase, OpenAI, WhatsApp) so tests
run without network access or real credentials.
"""
import os, sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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
# Legacy/back-compat — some older tests or services may still read these.
# Cheap to keep; safe to remove in a follow-up cleanup.
os.environ.setdefault("SUPABASE_ANON_KEY", "fake-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake-service-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake")

# Ensure the app package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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

    def lte(self, *a):
        return self

    def ilike(self, *a):
        return self

    def or_(self, *a):
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
        return self._tables.get(name, FakeSupabaseQuery())

    def set_table(self, name, query: "FakeSupabaseQuery"):
        self._tables[name] = query

    def rpc(self, *a, **kw):
        return FakeSupabaseQuery(data=[True])


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

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    get_settings.cache_clear()
