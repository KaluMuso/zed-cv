"""Production middleware and RFC 7807 error response tests."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.deps import get_supabase
from main import TRUSTED_HOSTS, create_app

API_HOST = {"Host": "api.zedapply.com"}


@pytest.fixture
def middleware_client(fake_supabase):
    """TestClient with trusted Host header for middleware tests."""
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_supabase] = lambda: fake_supabase
    try:
        from app.core.rate_limit import limiter

        limiter.enabled = False
    except (ImportError, AttributeError):
        pass
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def prod_app(fake_supabase, monkeypatch):
    monkeypatch.setenv("DEBUG", "false")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_supabase] = lambda: fake_supabase
    yield app
    app.dependency_overrides.clear()
    get_settings.cache_clear()


class TestTrustedHost:
    def test_trusted_host_rejects_unknown_host(self, middleware_client):
        resp = middleware_client.get(
            "/api/v1/health",
            headers={"Host": "evil.com"},
        )
        assert resp.status_code == 400

    @patch("app.services.whatsapp.check_waha_health", new_callable=AsyncMock)
    def test_trusted_host_accepts_api_zedapply(
        self, mock_waha, middleware_client
    ):
        mock_waha.return_value = True
        resp = middleware_client.get("/api/v1/health", headers=API_HOST)
        assert resp.status_code == 200

    def test_trusted_hosts_include_production_and_dev(self):
        assert "api.zedapply.com" in TRUSTED_HOSTS
        assert "zedcv-backend" in TRUSTED_HOSTS


class TestProblemDetail:
    @patch("app.services.whatsapp.check_waha_health", new_callable=AsyncMock)
    def test_problem_detail_format_on_500(self, mock_waha, debug_app):
        mock_waha.return_value = True
        with TestClient(debug_app, raise_server_exceptions=False) as client:
            resp = client.get("/api/v1/test-error", headers=API_HOST)
        assert resp.status_code == 500
        assert resp.headers["content-type"].startswith(
            "application/problem+json"
        )
        body = resp.json()
        assert body["type"] == (
            "https://api.zedapply.com/errors/internal_server_error"
        )
        assert body["title"] == "Internal Server Error"
        assert body["status"] == 500
        assert "request_id" in body
        assert body["request_id"] in body["detail"]
        assert body["instance"] == "/api/v1/test-error"
        for field in ("type", "title", "status", "detail", "instance"):
            assert field in body

    def test_request_id_propagates_to_response_header(self, middleware_client):
        custom_id = "550e8400-e29b-41d4-a716-446655440000"
        resp = middleware_client.get(
            "/api/v1/health",
            headers={**API_HOST, "X-Request-ID": custom_id},
        )
        assert resp.headers.get("X-Request-ID") == custom_id


class TestCorsPreflight:
    """Preview deploys must pass OPTIONS before POST /auth/login."""

    @pytest.mark.parametrize(
        "origin",
        [
            "https://zed-kvqba36cx-vergeo-projects.vercel.app",
            "https://zed-cv-abc123-vergeo-projects.vercel.app",
            "https://www.zedapply.com",
        ],
    )
    def test_auth_login_preflight_allows_known_origins(
        self, middleware_client, origin: str
    ):
        resp = middleware_client.options(
            "/api/v1/auth/login",
            headers={
                **API_HOST,
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == origin

    def test_auth_login_preflight_rejects_unknown_origin(
        self, middleware_client
    ):
        origin = "https://evil.example.com"
        resp = middleware_client.options(
            "/api/v1/auth/login",
            headers={
                **API_HOST,
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.headers.get("access-control-allow-origin") != origin


class TestSecurityHeaders:
    def test_security_headers_present(self, middleware_client):
        resp = middleware_client.get("/api/v1/health", headers=API_HOST)
        assert (
            resp.headers.get("Strict-Transport-Security")
            == "max-age=31536000; includeSubDomains"
        )
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert (
            resp.headers.get("Referrer-Policy")
            == "strict-origin-when-cross-origin"
        )
        assert (
            resp.headers.get("Permissions-Policy")
            == "camera=(), microphone=(), geolocation=()"
        )
        assert resp.headers.get("X-Request-ID")


class TestDocsGating:
    def test_docs_returns_404_when_debug_false(self, prod_app):
        with TestClient(prod_app) as client:
            assert client.get("/docs", headers=API_HOST).status_code == 404
            assert (
                client.get("/openapi.json", headers=API_HOST).status_code == 404
            )

    def test_docs_returns_200_when_debug_true(self, debug_app):
        with TestClient(debug_app) as client:
            assert client.get("/docs", headers=API_HOST).status_code == 200
            assert (
                client.get("/openapi.json", headers=API_HOST).status_code == 200
            )
