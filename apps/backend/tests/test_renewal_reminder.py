"""Admin cron endpoint for renewal reminders."""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

INGEST_HEADERS = {"INGEST_API_KEY": "test-ingest-key"}


def test_trigger_renewal_reminders_requires_auth(client: TestClient):
    resp = client.post("/api/v1/admin/trigger-renewal-reminders")
    assert resp.status_code == 401


def test_trigger_renewal_reminders_ok(client: TestClient):
    with patch(
        "app.api.v1.admin_ingest.run_renewal_reminder_emails",
        new_callable=AsyncMock,
        return_value={"sent": 2, "skipped": 5, "failed": 0},
    ):
        resp = client.post(
            "/api/v1/admin/trigger-renewal-reminders",
            headers=INGEST_HEADERS,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] == 2
    assert body["skipped"] == 5
