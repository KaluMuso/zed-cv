"""Unit tests for the Sentry before_send PII redactor (task #77).

These tests poke the redactor directly with event-shaped dicts — no SDK
boot, no Sentry transport. The point is to pin the regex contracts so a
later refactor can't quietly let our domain PII leak into Sentry.
"""
import copy

from app.core.sentry_redaction import (
    before_send,
    redact_string,
    _walk,
)


# ── string-level redaction ──────────────────────────────────────────


class TestRedactString:
    def test_phone_redacted(self):
        s = "User +260971234567 failed verification"
        assert "+260971234567" not in redact_string(s)
        assert "[phone-redacted]" in redact_string(s)

    def test_email_redacted(self):
        s = "Sent welcome email to user@example.com"
        out = redact_string(s)
        assert "user@example.com" not in out
        assert "[email-redacted]" in out

    def test_jwt_redacted(self):
        # Realistic JWT shape: 3 base64url segments separated by dots.
        jwt = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0"
            ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        s = f"Bearer {jwt} rejected at /api/v1/profile"
        out = redact_string(s)
        assert jwt not in out
        assert "[jwt-redacted]" in out

    def test_all_three_in_one_string(self):
        s = (
            "Auth failed for +260971234567 (john@example.com) "
            "token=eyJhbGciOiJIUzI1NiJ9."
            "eyJzdWIiOiIxIn0."
            "abcd1234"
        )
        out = redact_string(s)
        assert "+260971234567" not in out
        assert "john@example.com" not in out
        assert "eyJ" not in out
        assert out.count("[phone-redacted]") == 1
        assert out.count("[email-redacted]") == 1
        assert out.count("[jwt-redacted]") == 1

    def test_non_pii_unaffected(self):
        """Numbers that aren't Zambian phones, words that aren't emails,
        and dotted tokens that aren't JWT-shaped must pass through."""
        s = "Request 2026-05-14 18:42:01 → /api/v1/jobs (200, 142ms, x.y.z=1)"
        assert redact_string(s) == s

    def test_non_zambian_phone_preserved(self):
        """The redactor is intentionally narrow — it only knows the +260
        format the platform actually issues. A US phone shouldn't be
        zapped (would be a false positive that erases useful debugging
        context)."""
        s = "Caller-ID +14155552671 routed to fallback"
        assert "+14155552671" in redact_string(s)

    def test_idempotent(self):
        """Running the redactor on already-redacted text is a no-op —
        the placeholder tokens don't match any of the patterns."""
        once = redact_string("phone +260971234567 email u@x.com")
        twice = redact_string(once)
        assert once == twice


# ── deep walker over event-shaped dicts ─────────────────────────────


class TestWalk:
    def test_walks_nested_dict(self):
        event = {
            "exception": {
                "values": [
                    {"value": "User +260971234567 hit error"}
                ]
            }
        }
        _walk(event)
        assert (
            event["exception"]["values"][0]["value"]
            == "User [phone-redacted] hit error"
        )

    def test_walks_lists_of_strings(self):
        event = {"tags": ["user:+260971234567", "env:prod"]}
        _walk(event)
        assert event["tags"][0] == "user:[phone-redacted]"
        assert event["tags"][1] == "env:prod"

    def test_walks_breadcrumbs(self):
        event = {
            "breadcrumbs": {
                "values": [
                    {
                        "message": (
                            "POST /auth/otp/verify with "
                            '{"phone":"+260971234567","code":"123456"}'
                        ),
                        "category": "http",
                    }
                ]
            }
        }
        _walk(event)
        bc = event["breadcrumbs"]["values"][0]
        assert "+260971234567" not in bc["message"]
        assert "[phone-redacted]" in bc["message"]
        # Non-PII fields untouched
        assert bc["category"] == "http"

    def test_non_string_values_pass_through(self):
        """Numbers, booleans, None must not be munged."""
        event = {"level": "error", "timestamp": 1715712000, "fatal": True, "user": None}
        _walk(event)
        assert event == {
            "level": "error",
            "timestamp": 1715712000,
            "fatal": True,
            "user": None,
        }


# ── before_send entry point ─────────────────────────────────────────


class TestBeforeSend:
    def test_returns_event_not_none(self):
        """Dropping the event would lose the breadcrumb trail. The hook
        must always return the (redacted) event."""
        event = {"message": "User +260971234567 timed out"}
        result = before_send(event, hint=None)
        assert result is event  # in-place

    def test_full_realistic_event(self):
        """End-to-end on a Sentry-shaped event with PII sprinkled across
        the surfaces we know to leak: exception value, request body,
        breadcrumbs, extras."""
        event = {
            "exception": {
                "values": [
                    {
                        "type": "HTTPException",
                        "value": (
                            "401 for +260971234567 "
                            "token=eyJhbGciOiJIUzI1NiJ9."
                            "eyJzdWIiOiJ1MSJ9."
                            "abcdefghij"
                        ),
                    }
                ]
            },
            "request": {
                "data": {
                    "phone": "+260971234567",
                    "email": "applicant@example.com",
                }
            },
            "breadcrumbs": {
                "values": [
                    {
                        "message": "verify_otp called for +260971234567",
                        "category": "auth",
                    }
                ]
            },
            "extra": {
                "user_id": "abc-123",  # not PII — must survive
                "support_email": "support@vergeo.company",
            },
        }
        before_send(event, hint=None)

        # Exception value: phone + JWT both gone
        ev_val = event["exception"]["values"][0]["value"]
        assert "+260971234567" not in ev_val
        assert "eyJ" not in ev_val
        assert "[phone-redacted]" in ev_val
        assert "[jwt-redacted]" in ev_val

        # Request body: phone and email both gone
        assert event["request"]["data"]["phone"] == "[phone-redacted]"
        assert event["request"]["data"]["email"] == "[email-redacted]"

        # Breadcrumb: phone gone, category preserved
        bc = event["breadcrumbs"]["values"][0]
        assert "+260971234567" not in bc["message"]
        assert bc["category"] == "auth"

        # Extras: user_id (random string, no PII) untouched, email-shaped
        # support address redacted (the redactor doesn't second-guess
        # whether the email is "ours" vs "theirs" — that distinction
        # belongs in the policy, not the regex).
        assert event["extra"]["user_id"] == "abc-123"
        assert event["extra"]["support_email"] == "[email-redacted]"

    def test_does_not_crash_on_missing_keys(self):
        """A minimal event must still be returned successfully."""
        event = {}
        assert before_send(event, hint=None) == {}

    def test_does_not_mutate_input_shape(self):
        """before_send mutates string VALUES but never adds, removes,
        renames, or reshapes keys. The Sentry SDK relies on the shape
        being preserved; a refactor that wraps the event in {"redacted":
        ...} would silently break the wire format."""
        event = {
            "level": "error",
            "exception": {"values": [{"value": "u@x.com hit limit"}]},
        }
        original_keys = set(event.keys())
        original_exception_keys = set(event["exception"].keys())
        original_value_keys = set(event["exception"]["values"][0].keys())

        before_send(copy.deepcopy(event), hint=None)

        # Re-run on the actual event so the assertions below operate on
        # the redacted version.
        before_send(event, hint=None)

        assert set(event.keys()) == original_keys
        assert set(event["exception"].keys()) == original_exception_keys
        assert (
            set(event["exception"]["values"][0].keys()) == original_value_keys
        )
