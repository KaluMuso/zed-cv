"""Tests for the /contact relay endpoint (task #65)."""
import os
from unittest.mock import patch, MagicMock


def _valid_body(**overrides) -> dict:
    body = {
        "name": "Mwila K.",
        "email": "mwila@example.com",
        "message": "Hello, I have a question about my matches.",
    }
    body.update(overrides)
    return body


class TestContactValidation:
    """Pydantic-level validation. None of these should reach Resend."""

    def test_missing_name_is_422(self, client):
        body = _valid_body()
        del body["name"]
        resp = client.post("/api/v1/contact", json=body)
        assert resp.status_code == 422

    def test_invalid_email_is_422(self, client):
        resp = client.post("/api/v1/contact", json=_valid_body(email="not-an-email"))
        assert resp.status_code == 422

    def test_short_message_is_422(self, client):
        resp = client.post("/api/v1/contact", json=_valid_body(message="hi"))
        assert resp.status_code == 422

    def test_long_message_is_422(self, client):
        # 5,000-char limit per the schema. 5,001 should fail.
        resp = client.post(
            "/api/v1/contact", json=_valid_body(message="x" * 5001)
        )
        assert resp.status_code == 422

    def test_invalid_phone_shape_is_422(self, client):
        """Phone is optional, but if provided must match +260XXXXXXXXX."""
        # Within Pydantic's max_length=20 so we exercise the route's
        # OWN +260 regex check, not the generic length validator.
        resp = client.post(
            "/api/v1/contact", json=_valid_body(phone="+14155552671")
        )
        assert resp.status_code == 422
        assert "+260" in resp.json()["detail"]


class TestContactDelivery:
    def test_success_with_resend_configured(self, client, monkeypatch):
        """Happy path — submission relays via Resend and returns 200."""
        monkeypatch.setenv("RESEND_API_KEY", "fake-resend-key")

        # Clear settings cache so the new env var takes effect.
        from app.core.config import get_settings
        get_settings.cache_clear()

        fake_send = MagicMock()
        # `resend` is imported INSIDE the route handler, not at module
        # level, so we patch the attribute on the resend module after
        # the first import would happen. importlib gets us a handle
        # without needing resend to already be in sys.modules.
        import resend
        monkeypatch.setattr(resend.Emails, "send", fake_send)

        resp = client.post("/api/v1/contact", json=_valid_body())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert "way" in body["message"]  # "your message is on its way"

        # Resend was called once with the right shape
        fake_send.assert_called_once()
        payload = fake_send.call_args[0][0]
        assert payload["reply_to"] == "mwila@example.com"
        assert payload["to"] == ["convergeozambia@gmail.com"]
        assert "ZedApply contact" in payload["subject"]
        # User-supplied message lands in the body (HTML-escaped but
        # readable). The literal name appears in the rendered HTML.
        assert "Mwila K." in payload["html"]

    def test_html_escaping_in_message(self, client, monkeypatch):
        """A hostile user can't inject <script> into the operator inbox."""
        monkeypatch.setenv("RESEND_API_KEY", "fake-resend-key")
        from app.core.config import get_settings
        get_settings.cache_clear()

        fake_send = MagicMock()
        import resend
        monkeypatch.setattr(resend.Emails, "send", fake_send)

        hostile = _valid_body(
            name="<script>alert(1)</script>",
            message="hi <img src=x onerror=alert(2)> there",
        )
        resp = client.post("/api/v1/contact", json=hostile)
        assert resp.status_code == 200

        html_body = fake_send.call_args[0][0]["html"]
        # The raw tags MUST NOT survive — they should be entity-escaped.
        assert "<script>" not in html_body
        assert "<img" not in html_body
        # The escaped form must be present (so the operator can still
        # see the original input verbatim).
        assert "&lt;script&gt;" in html_body
        assert "&lt;img" in html_body

    def test_503_when_resend_not_configured(self, client, monkeypatch):
        """Fail loud — don't silently drop the user's message."""
        monkeypatch.setenv("RESEND_API_KEY", "")
        from app.core.config import get_settings
        get_settings.cache_clear()

        resp = client.post("/api/v1/contact", json=_valid_body())
        assert resp.status_code == 503
        # The error message tells the user how to reach us directly so
        # they aren't stranded.
        assert "convergeozambia@gmail.com" in resp.json()["detail"]

    def test_503_when_resend_raises(self, client, monkeypatch):
        """A Resend outage returns 503 with a generic message — we don't
        echo the upstream error verbatim (could leak internal addresses
        or API response shape)."""
        monkeypatch.setenv("RESEND_API_KEY", "fake-resend-key")
        from app.core.config import get_settings
        get_settings.cache_clear()

        import resend
        monkeypatch.setattr(
            resend.Emails,
            "send",
            MagicMock(side_effect=RuntimeError("resend API exploded")),
        )

        resp = client.post("/api/v1/contact", json=_valid_body())
        assert resp.status_code == 503
        # Upstream error message NOT surfaced
        detail = resp.json()["detail"]
        assert "resend API exploded" not in detail
        assert "exploded" not in detail


class TestContactRateLimit:
    """The route is decorated with @limiter.limit('2/hour'). Conftest
    disables the limiter for normal tests; we flip it back on here."""

    def test_third_call_in_hour_is_429(self, client, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "fake-resend-key")
        from app.core.config import get_settings
        get_settings.cache_clear()

        import resend
        monkeypatch.setattr(resend.Emails, "send", MagicMock())

        from app.core.rate_limit import limiter
        prev = limiter.enabled
        limiter.enabled = True
        try:
            limiter.reset()
        except Exception:
            pass
        try:
            r1 = client.post("/api/v1/contact", json=_valid_body())
            r2 = client.post("/api/v1/contact", json=_valid_body())
            r3 = client.post("/api/v1/contact", json=_valid_body())
            assert r1.status_code == 200
            assert r2.status_code == 200
            # 3rd call within the hour is over the 2/hour cap
            assert r3.status_code == 429, r3.text
        finally:
            limiter.enabled = prev
            try:
                limiter.reset()
            except Exception:
                pass
