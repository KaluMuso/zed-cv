"""WhatsApp classifier: promo pre-filter, LLM acceptance, metrics."""
import json
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import FakeSupabaseQuery

from app.services.whatsapp_classifier import (
    WhatsappJobClassification,
    classify_whatsapp_image,
    classify_whatsapp_text,
)
from app.services.whatsapp_classifier_prefilter import promo_prefilter_rejects

GENUINE_JOB = {
    "is_job": True,
    "title": "Accounts Clerk",
    "company": "ZANACO",
    "location": "Lusaka",
    "description": (
        "ZANACO is hiring an Accounts Clerk in Lusaka. "
        "Apply with CV to careers@zanaco.co.zm before closing date."
    ),
    "apply_email": "careers@zanaco.co.zm",
    "skills": ["accounting"],
}

IMAGE_JOB = {
    **GENUINE_JOB,
    "title": "Accountant",
    "ocr_text": "VACANCY: Accountant at ZANACO. Apply careers@zanaco.co.zm",
}


@pytest.fixture
def openrouter_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-openrouter")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class RecordingAiCache:
    """Captures ai_cache inserts for metadata assertions."""

    def __init__(self):
        self.inserted: list[dict] = []

    def select(self, *a, **kw):
        return self

    def eq(self, *a):
        return self

    def limit(self, *a):
        return self

    def insert(self, data):
        if isinstance(data, dict):
            self.inserted.append(data)
        return self

    def execute(self):
        result = MagicMock()
        result.data = []
        return result


@pytest.mark.asyncio
async def test_classifier_rejects_cv_writing_service_promotion(
    openrouter_env, fake_supabase
):
    cache = RecordingAiCache()
    fake_supabase.set_table("ai_cache", cache)
    promo = (
        "Professional CV writing service! Get your CV done for K50 only. "
        "WhatsApp us today for fast turnaround."
    )

    with patch("app.services.whatsapp_classifier._client") as mock_client_fn:
        result = await classify_whatsapp_text(promo, supabase=fake_supabase)

    assert result.is_job is False
    mock_client_fn.assert_not_called()
    assert cache.inserted
    assert cache.inserted[0]["metadata"]["classifier_decision"] == "rejected_as_promo"
    assert cache.inserted[0]["metadata"]["llm_response"] is None


@pytest.mark.asyncio
async def test_classifier_rejects_inbox_us_on_whatsapp_pattern(
    openrouter_env, fake_supabase
):
    cache = RecordingAiCache()
    fake_supabase.set_table("ai_cache", cache)
    promo = (
        "We help job seekers across Zambia! Inbox us on WhatsApp for daily "
        "tips and career coaching packages."
    )

    with patch("app.services.whatsapp_classifier._client") as mock_client_fn:
        result = await classify_whatsapp_text(promo, supabase=fake_supabase)

    assert result.is_job is False
    mock_client_fn.assert_not_called()
    assert cache.inserted[0]["metadata"]["classifier_decision"] == "rejected_as_promo"


@pytest.mark.asyncio
async def test_classifier_accepts_genuine_job_posting_with_email(
    openrouter_env, fake_supabase
):
    cache = RecordingAiCache()
    fake_supabase.set_table("ai_cache", cache)
    body = (
        "VACANCY: Accounts Clerk at ZANACO, Lusaka branch. "
        "Send CV to careers@zanaco.co.zm. Closing Friday."
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=json.dumps(GENUINE_JOB),
                )
            )
        ]
    )

    with patch("app.services.whatsapp_classifier._client", return_value=mock_client):
        result = await classify_whatsapp_text(body, supabase=fake_supabase)

    assert result.is_job is True
    assert result.apply_email == "careers@zanaco.co.zm"
    mock_client.chat.completions.create.assert_called_once()
    assert cache.inserted[0]["metadata"]["classifier_decision"] == "accepted_as_job"
    assert cache.inserted[0]["metadata"]["llm_response"] is not None


@pytest.mark.asyncio
async def test_classifier_accepts_image_job_poster(openrouter_env, fake_supabase):
    cache = RecordingAiCache()
    fake_supabase.set_table("ai_cache", cache)
    image_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 64

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=json.dumps(IMAGE_JOB),
                )
            )
        ]
    )

    with patch("app.services.whatsapp_classifier._client", return_value=mock_client):
        result = await classify_whatsapp_image(
            image_bytes,
            caption="Job poster",
            supabase=fake_supabase,
        )

    assert result.is_job is True
    assert result.ocr_text is not None
    mock_client.chat.completions.create.assert_called_once()
    assert cache.inserted[0]["metadata"]["classifier_decision"] == "accepted_as_job"


@pytest.mark.asyncio
async def test_regex_prefilter_rejects_before_llm_call(openrouter_env, fake_supabase):
    text = "Take advantage of our promotion — CV package K200 per month!"
    assert promo_prefilter_rejects(text) is True

    cache = RecordingAiCache()
    fake_supabase.set_table("ai_cache", cache)

    with patch("app.services.whatsapp_classifier._client") as mock_client_fn:
        await classify_whatsapp_text(text, supabase=fake_supabase)

    mock_client_fn.assert_not_called()
    assert cache.inserted[0]["metadata"]["classifier_decision"] == "rejected_as_promo"


class TestAdminScraperStats:
    def test_scraper_stats_aggregates_metadata(self, client, auth_headers, fake_supabase):
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(data=[{"id": "test-user-id", "role": "admin"}]),
        )
        fake_supabase.set_table(
            "ai_cache",
            FakeSupabaseQuery(
                data=[
                    {
                        "metadata": {"classifier_decision": "accepted_as_job"},
                        "created_at": "2026-05-20T10:00:00+00:00",
                    },
                    {
                        "metadata": {"classifier_decision": "rejected_as_promo"},
                        "created_at": "2026-05-20T11:00:00+00:00",
                    },
                    {
                        "metadata": {"classifier_decision": "rejected_as_other"},
                        "created_at": "2026-05-21T09:00:00+00:00",
                    },
                ]
            ),
        )

        resp = client.get("/api/v1/admin/scraper-stats?days=7", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["accepted_as_job"] == 1
        assert body["rejected_as_promo"] == 1
        assert body["rejected_as_other"] == 1
        assert len(body["days"]) == 2
