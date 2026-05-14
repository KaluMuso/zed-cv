"""Tests for the DPO Pay webhook handler and the subscription/pay no-Lenco guard.

Covers slice 2D-1c hardening:
- Idempotency: a webhook for an already-completed payment must NOT re-upgrade.
- Period-end safety: stack 30 days on top of remaining paid days, never truncate.
- Tier mapping: exact-price reverse-lookup against TIER_PRICES + TIER_LIMITS.
- Unknown-amount fallback: log a warning and stamp webhook_data with the
  resolved tier for human review.
- Subscription/pay rejects payment_method values starting with 'lenco_'
  (the live Lenco initiation path was reverted in this slice).
"""
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import FakeSupabaseQuery


class _UpdateSpyQuery(FakeSupabaseQuery):
    """FakeSupabaseQuery that records every update() call's payload.

    Use to assert which writes the route did or did not make. Modeled on the
    same subclass-and-extend discipline as test_subscription.py's _SingleQuery
    (intentionally inline — keeps conftest.py untouched).
    """

    def __init__(self, data=None):
        super().__init__(data=data)
        self.update_calls: list = []

    def update(self, data):
        self.update_calls.append(data)
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        result = MagicMock()
        if getattr(self, "_single", False) and self._data:
            result.data = self._data[0] if isinstance(self._data, list) else self._data
        else:
            result.data = self._data
        result.count = getattr(self, "_count", None)
        return result


def _patch_dpo_helpers(parsed_token: str = "TOK-123", is_paid: bool = True):
    """Return (parse_patch, verify_patch) decorators wired to standard responses."""
    parse = patch(
        "app.services.dpo_pay.parse_dpo_webhook_xml",
        return_value={
            "company_ref": "",
            # task #75: the route now verifies this matches
            # settings.dpo_pay_company_token. Conftest sets the env to
            # "test-dpo-merchant-token" so the mock must emit the same.
            "company_token": "test-dpo-merchant-token",
            "transaction_token": parsed_token,
            "transaction_ref": "REF-1",
            "transaction_amount": "125.00",
            "transaction_currency": "ZMW",
            "result_code": "000",
            "result_explanation": "ok",
            "customer_phone": "+260971234567",
        },
    )
    verify = patch(
        "app.services.dpo_pay.verify_payment",
        new_callable=AsyncMock,
        return_value={
            "is_paid": is_paid,
            "result_code": "000" if is_paid else "002",
            "result_explanation": "ok" if is_paid else "declined",
            "transaction_ref": "REF-1",
            "customer_phone": "+260971234567",
            "amount": "125.00",
            "currency": "ZMW",
        },
    )
    return parse, verify


def _payment_row(amount: int, status: str = "pending", existing_end: str | None = None):
    return {
        "id": "pay-001",
        "user_id": "test-user-id",
        "amount": amount,
        "status": status,
        "subscriptions": {
            "id": "sub-1",
            "user_id": "test-user-id",
            "tier": "free",
            "current_period_end": existing_end,
        },
    }


def _post_dpo(client):
    return client.post("/api/v1/webhooks/dpo", content=b"<API3G/>")


# ── 1. Idempotency ───────────────────────────────────────────────────────


def test_dpo_webhook_idempotency(client, fake_supabase):
    """A webhook for an already-completed payment returns already_processed
    and does NOT touch the subscription."""
    fake_supabase.set_table(
        "payments", _UpdateSpyQuery(data=[_payment_row(amount=12500, status="completed")])
    )
    sub_spy = _UpdateSpyQuery(data=[{"id": "sub-1", "user_id": "test-user-id"}])
    fake_supabase.set_table("subscriptions", sub_spy)
    fake_supabase.set_table("users", _UpdateSpyQuery(data=[{"phone": "+260971234567"}]))

    parse, verify = _patch_dpo_helpers()
    with parse, verify, patch(
        "app.api.v1.webhooks.send_whatsapp_message", new_callable=AsyncMock
    ), patch(
        "app.api.v1.webhooks.send_payment_confirmation_email", new_callable=AsyncMock
    ):
        resp = _post_dpo(client)

    assert resp.status_code == 200
    assert resp.json() == {"status": "already_processed"}
    assert sub_spy.update_calls == []  # subscription must not be re-upgraded


# ── 2. Period-end safety ─────────────────────────────────────────────────


def test_dpo_webhook_period_end_safety(client, fake_supabase):
    """When a webhook arrives mid-cycle, new period_end stacks on top of the
    remaining paid time rather than truncating to now+30d."""
    now = datetime.now(timezone.utc)
    existing_end = now + timedelta(days=20)

    fake_supabase.set_table(
        "payments",
        _UpdateSpyQuery(
            data=[_payment_row(amount=12500, existing_end=existing_end.isoformat())]
        ),
    )
    sub_spy = _UpdateSpyQuery(data=[{"id": "sub-1", "user_id": "test-user-id"}])
    fake_supabase.set_table("subscriptions", sub_spy)
    fake_supabase.set_table("users", _UpdateSpyQuery(data=[{"phone": "+260971234567"}]))

    parse, verify = _patch_dpo_helpers()
    with parse, verify, patch(
        "app.api.v1.webhooks.send_whatsapp_message", new_callable=AsyncMock
    ), patch(
        "app.api.v1.webhooks.send_payment_confirmation_email", new_callable=AsyncMock
    ):
        resp = _post_dpo(client)

    assert resp.status_code == 200
    assert len(sub_spy.update_calls) == 1
    end_iso = sub_spy.update_calls[0]["current_period_end"]
    new_end = datetime.fromisoformat(end_iso)
    delta = new_end - now
    # Expected ≈ 50 days (20 remaining + 30 new). Wide jitter window absorbs
    # test runtime; the assertion that fails the *old* code is delta > 31d.
    assert timedelta(days=49) < delta < timedelta(days=51), (
        f"Expected ~50d (20 remaining + 30 new), got {delta}"
    )


# ── 3. Tier mapping by exact price ───────────────────────────────────────


@pytest.mark.parametrize(
    "amount,expected_tier,expected_limit",
    [
        (12500, "starter", 50),
        (25000, "professional", 125),
        (50000, "super_standard", 99999),
    ],
)
def test_dpo_webhook_tier_mapping_exact_price(
    client, fake_supabase, amount, expected_tier, expected_limit
):
    """Each canonical price maps to the canonical tier + TIER_LIMITS quota."""
    fake_supabase.set_table(
        "payments", _UpdateSpyQuery(data=[_payment_row(amount=amount)])
    )
    sub_spy = _UpdateSpyQuery(data=[{"id": "sub-1", "user_id": "test-user-id"}])
    fake_supabase.set_table("subscriptions", sub_spy)
    fake_supabase.set_table("users", _UpdateSpyQuery(data=[{"phone": "+260971234567"}]))

    parse, verify = _patch_dpo_helpers()
    with parse, verify, patch(
        "app.api.v1.webhooks.send_whatsapp_message", new_callable=AsyncMock
    ), patch(
        "app.api.v1.webhooks.send_payment_confirmation_email", new_callable=AsyncMock
    ):
        resp = _post_dpo(client)

    assert resp.status_code == 200
    assert resp.json() == {"status": "completed"}
    assert len(sub_spy.update_calls) == 1
    assert sub_spy.update_calls[0]["tier"] == expected_tier
    assert sub_spy.update_calls[0]["matches_limit"] == expected_limit


def test_dpo_webhook_tier_mapping_unknown_amount_logs_warning(
    client, fake_supabase, caplog
):
    """An off-price amount logs a warning and falls back defensively to the
    highest tier whose price is <= amount (17500 → starter)."""
    fake_supabase.set_table(
        "payments", _UpdateSpyQuery(data=[_payment_row(amount=17500)])
    )
    sub_spy = _UpdateSpyQuery(data=[{"id": "sub-1", "user_id": "test-user-id"}])
    fake_supabase.set_table("subscriptions", sub_spy)
    fake_supabase.set_table("users", _UpdateSpyQuery(data=[{"phone": "+260971234567"}]))

    parse, verify = _patch_dpo_helpers()
    with caplog.at_level(logging.WARNING), parse, verify, patch(
        "app.api.v1.webhooks.send_whatsapp_message", new_callable=AsyncMock
    ), patch(
        "app.api.v1.webhooks.send_payment_confirmation_email", new_callable=AsyncMock
    ):
        resp = _post_dpo(client)

    assert resp.status_code == 200
    assert "unknown amount 17500" in caplog.text
    assert sub_spy.update_calls[0]["tier"] == "starter"
    assert sub_spy.update_calls[0]["matches_limit"] == 50


# ── 4. Subscription/pay now accepts lenco method (Lenco-frontend slice) ──


def test_subscription_pay_accepts_lenco_method(client, auth_headers, fake_supabase):
    """Lenco initiation was re-enabled when the signed webhook handler
    shipped. The /pay route should now create a pending payment row with
    provider='lenco' and return 200 even when LENCO_API_KEY isn't set
    (the service degrades gracefully and the row stays pending until
    manual intervention)."""
    fake_supabase.set_table(
        "subscriptions",
        _UpdateSpyQuery(data=[{"id": "sub-1"}]),
    )
    fake_supabase.set_table(
        "payments",
        FakeSupabaseQuery(data=[{"id": "pay-lenco-1"}]),
    )
    resp = client.post(
        "/api/v1/subscription/pay",
        headers=auth_headers,
        json={
            "tier": "starter",
            "payment_method": "lenco",
            "phone": "+260971234567",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["transaction_id"] == "pay-lenco-1"


# ── Slice F: WhatsApp channel ingest ─────────────────────────────────────


CHANNEL_ID = "120363401234567890@newsletter"

SAMPLE_CHANNEL_BODY = """
*ACCOUNTANT*

Position: Accountant
Company: ZANACO
Location: Lusaka

Requirements:
- ZICA Licentiate or higher
- 3+ years experience in financial reporting
- Strong Excel and IFRS knowledge
- Experience with Sage Evolution preferred

How to apply: send CV to careers@zanaco.co.zm
Closing date: 2026-06-15
""".strip()


def _mock_extractor_response(extracted_payload: dict):
    """Build a MagicMock that mimics an OpenAI client returning the given
    payload as the assistant message content. Avoids hitting OpenRouter."""
    import json as _json
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = _json.dumps(extracted_payload)
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def test_whatsapp_channel_branch_off_by_default(client, fake_supabase, monkeypatch):
    """When whatsapp_jobs_ingest_enabled is False, the channel branch is
    NOT taken — even for messages from the configured channel ID. The
    feature is strictly opt-in via the env flag."""
    monkeypatch.setenv("WHATSAPP_CHANNEL_JOBS_ID", CHANNEL_ID)
    # Note: WHATSAPP_JOBS_INGEST_ENABLED intentionally NOT set.
    from app.core.config import get_settings
    get_settings.cache_clear()

    # Mock both downstream paths the message COULD hit:
    #   - the extractor (Slice F branch — must NOT fire)
    #   - send_whatsapp_message (existing fall-through branch — will fire
    #     because the message body isn't a known command)
    with patch(
        "app.services.job_extractor.extract_job_from_message",
        new_callable=AsyncMock,
    ) as mock_extract, patch(
        "app.api.v1.webhooks.send_whatsapp_message", new_callable=AsyncMock
    ):
        resp = client.post(
            "/api/v1/webhooks/whatsapp",
            json={
                "event": "message",
                "payload": {
                    "from": CHANNEL_ID,
                    "id": "msg-123",
                    "body": SAMPLE_CHANNEL_BODY,
                },
            },
        )

    get_settings.cache_clear()

    assert resp.status_code == 200
    # The critical assertion: with the flag off, the extractor was never
    # called — the message fell through to the existing user-command path.
    mock_extract.assert_not_called()


def test_whatsapp_channel_branch_routes_to_extractor(
    client, fake_supabase, monkeypatch
):
    """Flag on + matching chatId → extractor runs and feeds _ingest_one_job."""
    monkeypatch.setenv("WHATSAPP_CHANNEL_JOBS_ID", CHANNEL_ID)
    monkeypatch.setenv("WHATSAPP_JOBS_INGEST_ENABLED", "true")
    # Bust the lru_cache so the new env vars are seen.
    from app.core.config import get_settings
    get_settings.cache_clear()

    # Fresh fingerprint table → first ingest goes through.
    fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
    fake_supabase.set_table(
        "jobs", FakeSupabaseQuery(data=[{"id": "job-from-channel-1"}])
    )

    payload = {
        "title": "Accountant",
        "company": "ZANACO",
        "location": "Lusaka",
        "description": (
            "ZICA Licentiate or higher. 3+ years experience in financial "
            "reporting. Strong Excel and IFRS knowledge."
        ),
        "apply_url": None,
        "apply_email": "careers@zanaco.co.zm",
        "closing_date": "2026-06-15",
        "skills_required": ["accounting", "ifrs", "excel"],
        "confidence": 85,
    }

    with patch(
        "app.services.job_extractor._client",
        return_value=_mock_extractor_response(payload),
    ), patch(
        "app.api.v1.jobs.generate_embedding", new_callable=AsyncMock
    ) as mock_embed:
        mock_embed.return_value = [0.1] * 768
        resp = client.post(
            "/api/v1/webhooks/whatsapp",
            json={
                "event": "message",
                "payload": {
                    "from": CHANNEL_ID,
                    "id": "msg-456",
                    "body": SAMPLE_CHANNEL_BODY,
                },
            },
        )

    get_settings.cache_clear()  # Restore for any later tests.

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["ingest_result"] == "ingested"
    assert body["title"] == "Accountant"
    mock_embed.assert_called_once()


def test_whatsapp_channel_rebroadcast_returns_duplicate(
    client, fake_supabase, monkeypatch
):
    """The smoke-test requirement: a second paste of the same message
    must short-circuit at the fingerprint dedup, not re-insert. The
    extractor sees the same body and either (a) hits ai_cache or (b)
    re-runs, but either way the resulting JobCreate fingerprints to the
    same hash as the first round — so _ingest_one_job returns 'duplicate'."""
    monkeypatch.setenv("WHATSAPP_CHANNEL_JOBS_ID", CHANNEL_ID)
    monkeypatch.setenv("WHATSAPP_JOBS_INGEST_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()

    # Pre-seeded fingerprint table simulates "the job was already ingested
    # from yesterday's broadcast".
    fake_supabase.set_table(
        "job_fingerprints",
        FakeSupabaseQuery(data=[{"job_id": "job-from-yesterday"}]),
    )

    payload = {
        "title": "Accountant",
        "company": "ZANACO",
        "location": "Lusaka",
        "description": "ZICA Licentiate or higher. Strong Excel and IFRS knowledge.",
        "apply_email": "careers@zanaco.co.zm",
        "closing_date": "2026-06-15",
        "skills_required": ["accounting"],
        "confidence": 85,
    }

    with patch(
        "app.services.job_extractor._client",
        return_value=_mock_extractor_response(payload),
    ), patch(
        "app.api.v1.jobs.generate_embedding", new_callable=AsyncMock
    ) as mock_embed:
        resp = client.post(
            "/api/v1/webhooks/whatsapp",
            json={
                "event": "message",
                "payload": {
                    "from": CHANNEL_ID,
                    "id": "msg-789",
                    "body": SAMPLE_CHANNEL_BODY,
                },
            },
        )

    get_settings.cache_clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["ingest_result"] == "duplicate"
    # Critical: dedup short-circuited BEFORE the expensive embedding call.
    mock_embed.assert_not_called()


def test_whatsapp_channel_low_confidence_not_ingested(
    client, fake_supabase, monkeypatch
):
    """Extractor confidence below the floor (60) → drop quietly. No write,
    no error. Keeps channel chitchat ('Good morning everyone!') from
    polluting the jobs table."""
    monkeypatch.setenv("WHATSAPP_CHANNEL_JOBS_ID", CHANNEL_ID)
    monkeypatch.setenv("WHATSAPP_JOBS_INGEST_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()

    payload = {
        "title": "Something maybe",
        "description": "This message is probably not a job posting at all.",
        "skills_required": [],
        "confidence": 15,
    }

    with patch(
        "app.services.job_extractor._client",
        return_value=_mock_extractor_response(payload),
    ), patch(
        "app.api.v1.jobs.generate_embedding", new_callable=AsyncMock
    ) as mock_embed:
        resp = client.post(
            "/api/v1/webhooks/whatsapp",
            json={
                "event": "message",
                "payload": {
                    "from": CHANNEL_ID,
                    "id": "msg-noise",
                    "body": (
                        "Good morning everyone! Just a reminder we have "
                        "more job posts coming this afternoon."
                    ),
                },
            },
        )

    get_settings.cache_clear()

    assert resp.status_code == 200
    assert resp.json()["status"] == "not_a_job"
    mock_embed.assert_not_called()
