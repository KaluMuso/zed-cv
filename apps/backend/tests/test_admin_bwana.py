"""Admin Bwana config API."""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.bwana_config import clear_bwana_config_cache
from tests.conftest import FakeSupabaseQuery

BWANA_ROW = {
    "id": 1,
    "chatbot_display_name": "Bwana",
    "operator_display_name": "ZedApply Support",
    "support_email": "convergeozambia@gmail.com",
    "support_phone": "+260761359005",
    "escalation_whatsapp_phone": "+260761359005",
    "escalation_sla_hours": 24,
    "human_escalation_reply_template": "Human {email}",
    "unsatisfied_reply_template": "Sorry {email}",
    "contact_admin_reply_template": "Contact {email}",
    "public_knowledge_extra": "",
    "enable_email_escalation": True,
    "enable_user_escalation_ack": True,
    "user_escalation_ack_template": "Thanks {ticket_id}",
    "faq_intents_json": [],
    "updated_at": "2026-06-01T00:00:00+00:00",
}


def _seed_admin_user(fake_supabase):
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[{"id": "test-user-id", "phone": "+260971234567", "role": "admin"}]
        ),
    )


@pytest.fixture
def bwana_admin_tables(fake_supabase):
    clear_bwana_config_cache()
    _seed_admin_user(fake_supabase)
    fake_supabase.set_table("bwana_platform_config", FakeSupabaseQuery(data=[BWANA_ROW]))
    fake_supabase.set_table("bwana_escalation_log", FakeSupabaseQuery(data=[]))
    fake_supabase.set_table(
        "bwana_event_log",
        FakeSupabaseQuery(
            data=[
                {
                    "source": "faq",
                    "intent_id": "pricing",
                    "session_id": "sess-a",
                    "created_at": "2026-06-02T12:00:00+00:00",
                },
                {
                    "source": "llm",
                    "intent_id": None,
                    "session_id": "sess-a",
                    "created_at": "2026-06-02T12:01:00+00:00",
                },
            ]
        ),
    )
    fake_supabase.set_table("llm_usage_log", FakeSupabaseQuery(data=[]))
    fake_supabase.set_table(
        "ai_cache",
        FakeSupabaseQuery(
            data=[
                {
                    "cache_key": "abc",
                    "cache_type": "bwana_chat",
                    "created_at": "2026-06-02T12:00:00+00:00",
                    "result": {
                        "user_id": "user-1",
                        "session_id": "sess-a",
                        "messages": [
                            {"role": "user", "content": "hello pricing", "ts": "t1"},
                        ],
                    },
                }
            ]
        ),
    )
    return fake_supabase


def test_get_admin_bwana_config_requires_admin(client, auth_headers, bwana_admin_tables):
    resp = client.get("/api/v1/admin/bwana/config", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["support_email"] == "convergeozambia@gmail.com"


def test_patch_admin_bwana_config(client, auth_headers, bwana_admin_tables):
    resp = client.patch(
        "/api/v1/admin/bwana/config",
        headers=auth_headers,
        json={"support_email": "ops@zedapply.com", "escalation_sla_hours": 48},
    )
    assert resp.status_code == 200
    assert resp.json()["support_email"] == "ops@zedapply.com"
    assert resp.json()["escalation_sla_hours"] == 48


def test_patch_bwana_rejects_invalid_phone(client, auth_headers, bwana_admin_tables):
    resp = client.patch(
        "/api/v1/admin/bwana/config",
        headers=auth_headers,
        json={"support_phone": "invalid"},
    )
    assert resp.status_code == 422


def test_bwana_analytics(client, auth_headers, bwana_admin_tables):
    resp = client.get("/api/v1/admin/bwana/analytics?days=7", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_messages"] == 2
    assert body["unique_sessions"] == 1
    assert body["faq_turns"] == 1
    assert body["llm_turns"] == 1
    assert body["analytics_source"] == "live"


def test_bwana_prompt_preview_includes_version(client, auth_headers, bwana_admin_tables):
    resp = client.get("/api/v1/admin/bwana/config/preview", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "system_prompt_version" in body
    assert body["system_prompt_version"].startswith("bwana-")


def test_bwana_conversations_list(client, auth_headers, bwana_admin_tables):
    resp = client.get(
        "/api/v1/admin/bwana/conversations?q=pricing",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["items"][0]["session_id"] == "sess-a"


def test_bwana_conversations_export_csv(client, auth_headers, bwana_admin_tables):
    resp = client.get(
        "/api/v1/admin/bwana/conversations/export",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "user_id,session_id" in resp.text


def test_non_admin_denied_bwana_analytics(client, auth_headers, fake_supabase):
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[{"id": "test-user-id", "phone": "+260971234567", "role": "user"}]
        ),
    )
    resp = client.get("/api/v1/admin/bwana/analytics", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_test_escalation_endpoint(client, auth_headers, bwana_admin_tables):
    with patch(
        "app.api.v1.admin_bwana.send_test_escalation_whatsapp",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.return_value = None
        resp = client.post(
            "/api/v1/admin/bwana/test-escalation",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    mock_send.assert_awaited_once()
