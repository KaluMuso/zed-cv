"""Pin DPO webhook authenticity verification (task #75).

The /webhooks/dpo route MUST reject webhooks whose CompanyToken doesn't
match settings.dpo_pay_company_token. Without that check the route
would accept any well-formed XML — an attacker who guessed the route
shape could send a forged "paid" notification and trigger a tier
upgrade (the verify_payment callback would still catch them most of
the time, but defense-in-depth matters).

These tests don't spin up FastAPI — they unit-test the verification
helpers in app/services/dpo_webhook.py directly. End-to-end coverage
through the route would need conftest's TestClient + mocked Supabase
+ mocked DPO API; that's task #84 (staging env).
"""
from app.services.dpo_webhook import verify_company_token, verify_hmac_signature


class TestVerifyCompanyToken:
    def test_matching_tokens_accepted(self):
        assert verify_company_token("merchant-token-abc", "merchant-token-abc") is True

    def test_mismatched_tokens_rejected(self):
        assert verify_company_token("attacker-guess", "real-merchant-token") is False

    def test_empty_parsed_token_rejected(self):
        """A webhook body without CompanyToken can never pass."""
        assert verify_company_token("", "real-merchant-token") is False

    def test_empty_expected_token_rejected(self):
        """A misconfigured server (no token set) must NOT short-circuit to True.

        This is the most important test in the file. If we left expected
        unset and the function returned True on empty-vs-empty match,
        the whole verification layer would be a no-op the moment someone
        forgot to set the env var.
        """
        assert verify_company_token("any-attacker-supplied", "") is False
        assert verify_company_token("", "") is False

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace tolerated (XML pretty-printing artifact)."""
        assert verify_company_token("  merchant-token  ", "merchant-token") is True

    def test_constant_time_compare_used(self):
        """Sanity: the helper imports hmac and uses compare_digest.

        Catches a refactor that accidentally swaps in == comparison
        (which would leak token length via timing side-channels).
        """
        import inspect
        import app.services.dpo_webhook as mod
        src = inspect.getsource(mod.verify_company_token)
        assert "compare_digest" in src, (
            "verify_company_token MUST use hmac.compare_digest, not ==. "
            "Plain == leaks the length-prefix of the secret via timing."
        )


class TestVerifyHmacSignature:
    """HMAC path is currently opt-in (settings.dpo_pay_webhook_secret defaults
    to empty). These tests pin the behaviour for when it gets enabled."""

    def test_no_secret_no_signature_rejected(self):
        """Both missing → False. Caller must fall back to CompanyToken."""
        assert verify_hmac_signature(b"some body", "", "") is False

    def test_secret_set_no_signature_rejected(self):
        """Opting into HMAC means demanding the header. Missing header → reject."""
        assert verify_hmac_signature(b"some body", "", "secret-xyz") is False

    def test_signature_set_no_secret_rejected(self):
        """Caller didn't enable HMAC; signature header is ignored."""
        assert verify_hmac_signature(b"some body", "abc123", "") is False

    def test_valid_signature_accepted(self):
        """The happy path — sig matches HMAC-SHA256(secret, body)."""
        import hmac as _hmac
        import hashlib

        body = b'<API3G><CompanyToken>x</CompanyToken></API3G>'
        secret = "test-secret"
        expected = _hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        assert verify_hmac_signature(body, expected, secret) is True

    def test_wrong_signature_rejected(self):
        assert verify_hmac_signature(
            b"some body",
            "0" * 64,  # well-formed but wrong digest
            "secret-xyz",
        ) is False

    def test_signature_case_insensitive(self):
        """Hex digest comparison should not be case-sensitive — different
        providers emit different casing."""
        import hmac as _hmac
        import hashlib

        body = b'body'
        secret = "s"
        expected_lower = _hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        expected_upper = expected_lower.upper()
        assert verify_hmac_signature(body, expected_upper, secret) is True


class TestParserExtractsCompanyToken:
    """parse_dpo_webhook_xml must surface CompanyToken into the dict.

    Without this the route's verify_company_token call sees empty string
    and rejects everything. This pins the parser contract.
    """

    def test_company_token_extracted_from_xml(self):
        from app.services.dpo_pay import parse_dpo_webhook_xml

        body = (
            b'<?xml version="1.0"?>'
            b'<API3G>'
            b'<CompanyToken>abc-merchant-123</CompanyToken>'
            b'<TransactionToken>txn-xyz</TransactionToken>'
            b'<CompanyRef>payment-1</CompanyRef>'
            b'</API3G>'
        )
        parsed = parse_dpo_webhook_xml(body)
        assert parsed["company_token"] == "abc-merchant-123"
        assert parsed["transaction_token"] == "txn-xyz"
        assert parsed["company_ref"] == "payment-1"

    def test_missing_company_token_returns_empty_string(self):
        """Webhook without CompanyToken: parser returns empty string,
        verify_company_token will then reject."""
        from app.services.dpo_pay import parse_dpo_webhook_xml

        body = b'<API3G><TransactionToken>txn-1</TransactionToken></API3G>'
        parsed = parse_dpo_webhook_xml(body)
        assert parsed["company_token"] == ""
