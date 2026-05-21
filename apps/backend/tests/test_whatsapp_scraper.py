"""Track 4c: WhatsApp channel scraper + Wave 2.5 skill resolver on ingest."""
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import FakeSupabaseQuery

CHANNEL_A = "120363401234567890@newsletter"
CHANNEL_B = "120363987654321098@newsletter"
WEBHOOK_TOKEN = "test-scraper-webhook-token"

JOB_TEXT = (
    "Hiring: Software Engineer at Tech Co Ltd, Lusaka. "
    "Apply: jobs@techco.zm. Required: 3+ years Python, Django"
)

CLASSIFIED_JOB = {
    "is_job": True,
    "title": "Software Engineer",
    "company": "Tech Co Ltd",
    "location": "Lusaka",
    "description": (
        "Software Engineer role at Tech Co Ltd in Lusaka. "
        "Requires 3+ years experience with Python and Django. "
        "Apply via email jobs@techco.zm."
    ),
    "apply_url": None,
    "apply_email": "jobs@techco.zm",
    "employment_type": None,
    "work_arrangement": None,
    "experience_min_years": 3,
    "seniority_level": "mid",
    "qualifications_required": [],
    "skills": ["python", "django"],
    "ocr_text": None,
}

NOT_JOB = {"is_job": False}


@pytest.fixture(autouse=True)
def scraper_env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_SCRAPE_CHANNELS", CHANNEL_A)
    monkeypatch.setenv("WHATSAPP_SCRAPER_WEBHOOK_TOKEN", WEBHOOK_TOKEN)
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _payload(*, body: str = "", msg_id: str = "wa-msg-001", channel: str = CHANNEL_A, has_media: bool = False, media: dict | None = None):
    p = {
        "id": msg_id,
        "from": channel,
        "body": body,
        "hasMedia": has_media,
        "fromMe": False,
    }
    if media:
        p["media"] = media
    return {"event": "message", "payload": p}


def _headers():
    return {"X-Webhook-Token": WEBHOOK_TOKEN}


class TestWhatsappScraperWebhook:
    @patch("app.api.v1.whatsapp_scraper_webhook.ingest_whatsapp_classification", new_callable=AsyncMock)
    @patch(
        "app.api.v1.whatsapp_scraper_webhook.classify_whatsapp_text",
        new_callable=AsyncMock,
    )
    def test_whatsapp_text_message_classified_as_job(
        self, mock_classify, mock_ingest, client, fake_supabase
    ):
        from app.services.whatsapp_classifier import WhatsappJobClassification

        mock_classify.return_value = WhatsappJobClassification.model_validate(
            CLASSIFIED_JOB
        )
        mock_ingest.return_value = {
            "status": "ok",
            "ingest_result": "ingested",
            "title": "Software Engineer",
        }

        resp = client.post(
            "/api/v1/whatsapp/scraper-webhook",
            headers=_headers(),
            json=_payload(body=JOB_TEXT, msg_id="wa-msg-job-1"),
        )
        assert resp.status_code == 200
        assert resp.json()["ingest_result"] == "ingested"
        mock_classify.assert_called_once()
        mock_ingest.assert_called_once()

    @patch(
        "app.api.v1.whatsapp_scraper_webhook.ingest_whatsapp_classification",
        new_callable=AsyncMock,
    )
    @patch(
        "app.api.v1.whatsapp_scraper_webhook.classify_whatsapp_text",
        new_callable=AsyncMock,
    )
    def test_whatsapp_text_message_classified_as_not_job_no_ingest(
        self, mock_classify, mock_ingest, client, fake_supabase
    ):
        from app.services.whatsapp_classifier import WhatsappJobClassification

        mock_classify.return_value = WhatsappJobClassification.model_validate(NOT_JOB)
        mock_ingest.return_value = {"status": "not_a_job"}

        resp = client.post(
            "/api/v1/whatsapp/scraper-webhook",
            headers=_headers(),
            json=_payload(body="Hello, good morning to the group", msg_id="wa-chit-1"),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_a_job"
        mock_ingest.assert_called_once()

    @patch(
        "app.api.v1.whatsapp_scraper_webhook.classify_whatsapp_text",
        new_callable=AsyncMock,
    )
    def test_whatsapp_dedup_via_message_id(
        self, mock_classify, client, fake_supabase
    ):
        from app.services.whatsapp_classifier import WhatsappJobClassification

        mock_classify.return_value = WhatsappJobClassification.model_validate(
            CLASSIFIED_JOB
        )
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(
                data=[{"id": "job-wa-1", "whatsapp_message_id": "wa-dedup-1"}]
            ),
        )

        resp = client.post(
            "/api/v1/whatsapp/scraper-webhook",
            headers=_headers(),
            json=_payload(body=JOB_TEXT, msg_id="wa-dedup-1"),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "duplicate_message_id"

    @patch("app.api.v1.jobs.enrich_job", new_callable=AsyncMock)
    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    @patch("app.api.v1.jobs.resolve_skill_ids", new_callable=AsyncMock)
    @patch(
        "app.api.v1.whatsapp_scraper_webhook.classify_whatsapp_text",
        new_callable=AsyncMock,
    )
    def test_whatsapp_dedup_via_fingerprint_cross_channel(
        self, mock_classify, mock_resolve, mock_embed, mock_enrich, client, fake_supabase, monkeypatch
    ):
        from app.services.whatsapp_classifier import WhatsappJobClassification

        monkeypatch.setenv(
            "WHATSAPP_SCRAPE_CHANNELS",
            f"{CHANNEL_A},{CHANNEL_B}",
        )
        from app.core.config import get_settings

        get_settings.cache_clear()

        mock_classify.return_value = WhatsappJobClassification.model_validate(
            CLASSIFIED_JOB
        )
        mock_embed.return_value = [0.1] * 768
        mock_resolve.return_value = ["skill-py"]
        mock_enrich.side_effect = ValueError("skip enrich in test")

        from app.api.v1.jobs import _fingerprint, _strip_html

        desc = _strip_html(CLASSIFIED_JOB["description"])
        fp = _fingerprint(
            CLASSIFIED_JOB["title"],
            CLASSIFIED_JOB["company"],
            desc,
        )

        fake_supabase.set_table(
            "job_fingerprints",
            FakeSupabaseQuery(data=[{"fingerprint": fp, "job_id": "existing-job"}]),
        )
        fake_supabase.set_table("jobs", FakeSupabaseQuery(data=[]))

        resp = client.post(
            "/api/v1/whatsapp/scraper-webhook",
            headers=_headers(),
            json=_payload(
                body=JOB_TEXT,
                msg_id="wa-other-channel-99",
                channel=CHANNEL_B,
            ),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("ingest_result") == "duplicate" or body.get("status") == "duplicate"

    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    @patch("app.api.v1.jobs.resolve_skill_ids", new_callable=AsyncMock)
    @patch(
        "app.services.whatsapp_classifier._client",
    )
    def test_classifier_cache_hit_on_repost(
        self, mock_client_fn, mock_resolve, mock_embed, client, fake_supabase
    ):
        mock_embed.return_value = [0.1] * 768
        mock_resolve.return_value = ["skill-py"]

        body_hash = hashlib.sha256(JOB_TEXT.encode()).hexdigest()
        cache_key = f"wa_classify_text:google/gemini-2.0-flash-001:{body_hash}"

        fake_supabase.set_table(
            "ai_cache",
            FakeSupabaseQuery(
                data=[
                    {
                        "cache_key": cache_key,
                        "result": CLASSIFIED_JOB,
                        "expires_at": "2099-01-01T00:00:00+00:00",
                    }
                ]
            ),
        )
        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "jobs", FakeSupabaseQuery(data=[{"id": "job-cache-1"}])
        )

        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client

        resp = client.post(
            "/api/v1/whatsapp/scraper-webhook",
            headers=_headers(),
            json=_payload(body=JOB_TEXT, msg_id="wa-cache-1"),
        )
        assert resp.status_code == 200
        mock_client.chat.completions.create.assert_not_called()

    @patch("app.api.v1.whatsapp_scraper_webhook._download_waha_media", new_callable=AsyncMock)
    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    @patch("app.api.v1.jobs.resolve_skill_ids", new_callable=AsyncMock)
    @patch(
        "app.api.v1.whatsapp_scraper_webhook.classify_whatsapp_image",
        new_callable=AsyncMock,
    )
    def test_whatsapp_image_ocr_then_classify_then_ingest(
        self, mock_vision, mock_resolve, mock_embed, mock_download, client, fake_supabase
    ):
        from app.services.whatsapp_classifier import WhatsappJobClassification

        ocr = "VACANCY: Accountant at ZANACO Lusaka. Apply careers@zanaco.co.zm"
        payload = dict(CLASSIFIED_JOB)
        payload["title"] = "Accountant"
        payload["ocr_text"] = ocr
        mock_vision.return_value = WhatsappJobClassification.model_validate(payload)
        mock_download.return_value = (b"\xff\xd8\xff", "image/jpeg")
        mock_embed.return_value = [0.1] * 768
        mock_resolve.return_value = ["skill-acc"]

        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        inserted: list[dict] = []

        class _JobsInsert(FakeSupabaseQuery):
            def insert(self, data):
                if isinstance(data, dict):
                    row = dict(data)
                    row["id"] = "job-img-1"
                    inserted.append(row)
                    self._data = [row]
                return self

        fake_supabase.set_table("jobs", _JobsInsert())

        resp = client.post(
            "/api/v1/whatsapp/scraper-webhook",
            headers=_headers(),
            json=_payload(
                body="",
                msg_id="wa-img-1",
                has_media=True,
                media={
                    "url": "http://waha:3000/api/files/wa-img-1.jpg",
                    "mimetype": "image/jpeg",
                },
            ),
        )
        assert resp.status_code == 200
        assert resp.json()["ingest_result"] == "ingested"
        assert inserted
        assert inserted[0].get("ocr_source_text") == ocr


class TestWave25IngestSkills:
    @patch("app.api.v1.jobs.generate_embedding", new_callable=AsyncMock)
    @patch("app.api.v1.jobs.resolve_skill_ids", new_callable=AsyncMock)
    def test_resolve_skill_ids_used_by_ingest_path(
        self, mock_resolve, mock_embed, client, fake_supabase
    ):
        mock_embed.return_value = [0.1] * 768
        mock_resolve.return_value = ["skill-uuid-1", "skill-uuid-2"]

        fake_supabase.set_table("job_fingerprints", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "jobs", FakeSupabaseQuery(data=[{"id": "job-ingest-skills"}])
        )

        job = {
            "title": "Software Engineer at Tech Co Ltd",
            "company": "Tech Co Ltd",
            "location": "Lusaka",
            "description": (
                "Hiring Software Engineer in Lusaka. Python and Django required. "
                "Apply jobs@techco.zm for details and requirements."
            ),
            "skills_required": ["python", "django"],
            "apply_email": "jobs@techco.zm",
            "source": "scraper",
            "source_url": "https://example.com/jobs/1",
        }

        resp = client.post(
            "/api/v1/jobs/ingest",
            json={"api_key": "test-ingest-key", "jobs": [job]},
        )
        assert resp.status_code == 200
        assert resp.json()["ingested"] == 1
        mock_resolve.assert_called()
        assert mock_resolve.call_args.kwargs.get("source") == "job_ingest"


def test_no_link_job_skills_symbol_in_backend():
    """Wave 2.5 removed _link_job_skills; ensure it does not reappear in app code."""
    from pathlib import Path

    backend_app = Path(__file__).resolve().parents[1] / "app"
    hits = [
        str(py.relative_to(backend_app))
        for py in backend_app.rglob("*.py")
        if "_link_job_skills" in py.read_text(encoding="utf-8")
    ]
    assert not hits, f"_link_job_skills found in: {hits}"
