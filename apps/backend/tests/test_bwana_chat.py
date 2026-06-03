"""Bwana chat — FAQ, escalation, LLM fallback, ai_cache history."""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.bwana_chat import (
    append_and_persist_history,
    handle_bwana_chat,
    load_conversation_history,
    process_bwana_message,
    session_cache_key,
)
from app.services.bwana_faq import is_escalation_request, match_faq
from app.services.bwana_config import build_bwana_system_prompt, clear_bwana_config_cache
from app.schemas.bwana_config import BwanaConfig
from tests.conftest import FakeSupabaseQuery

BWANA_CONFIG_ROW = {
    "id": 1,
    "chatbot_display_name": "Bwana",
    "operator_display_name": "ZedApply Support",
    "support_email": "support@zedapply.com",
    "support_phone": "+260971234567",
    "escalation_whatsapp_phone": "+260971234567",
    "escalation_sla_hours": 24,
    "human_escalation_reply_template": (
        "I've flagged this for {operator}. Email {email} or call {phone} within {sla}h."
    ),
    "unsatisfied_reply_template": (
        "Sorry — {operator} will follow up at {email} within {sla}h."
    ),
    "contact_admin_reply_template": "Contact {operator}: {email} or {phone}.",
    "public_knowledge_extra": "",
    "faq_intents_json": [],
    "enable_email_escalation": False,
    "enable_user_escalation_ack": True,
    "user_escalation_ack_template": (
        "Thanks — reference {ticket_id}. {operator} will email you at {email} within {sla}h."
    ),
}


def _seed_user(fake_supabase):
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "test-user-id",
                    "phone": "+260971234567",
                    "role": "user",
                }
            ]
        ),
    )


@pytest.fixture
def bwana_cache_table(fake_supabase):
    clear_bwana_config_cache()
    q = FakeSupabaseQuery(data=[])
    fake_supabase.set_table("ai_cache", q)
    fake_supabase.set_table(
        "bwana_platform_config",
        FakeSupabaseQuery(data=[BWANA_CONFIG_ROW.copy()]),
    )
    fake_supabase.set_table("bwana_escalation_log", FakeSupabaseQuery(data=[]))
    fake_supabase.set_table("bwana_event_log", FakeSupabaseQuery(data=[]))
    fake_supabase.set_table("tier_config", FakeSupabaseQuery(data=[]))
    return q


def test_bwana_faq_matches_pricing_question():
    match = match_faq("what's the price?")
    assert match is not None
    assert match.intent_id == "pricing"
    assert "Free" in match.response
    assert "Starter" in match.response
    assert "K125" in match.response
    assert "Professional" in match.response
    assert "Super Standard" in match.response


def test_bwana_escalates_on_support_keyword():
    assert is_escalation_request("I want to speak to a human")
    assert is_escalation_request("talk to human please")
    assert is_escalation_request("customer support")


@pytest.mark.asyncio
async def test_bwana_escalates_via_pipeline(fake_supabase, bwana_cache_table):
    with patch(
        "app.services.bwana_chat.send_whatsapp_message",
        new_callable=AsyncMock,
    ) as mock_wa:
        mock_wa.return_value = {"sent": True}
        turn = await process_bwana_message(
            user_id="test-user-id",
            message="I want to speak to a human",
            session_id="sess-1",
            supabase=fake_supabase,
        )
    assert turn.source == "escalated"
    assert turn.escalation_ticket_id
    assert turn.escalation_ticket_id.startswith("ZD-")
    assert "support@zedapply.com" in turn.response
    mock_wa.assert_awaited_once()


@pytest.mark.asyncio
async def test_contact_admin_returns_email_without_waha(
    fake_supabase, bwana_cache_table
):
    with patch(
        "app.services.bwana_chat.send_whatsapp_message",
        new_callable=AsyncMock,
    ) as mock_wa:
        turn = await process_bwana_message(
            user_id="test-user-id",
            message="What's your support email?",
            session_id="sess-contact",
            supabase=fake_supabase,
        )
    assert turn.source == "faq"
    assert turn.intent_id == "contact_admin"
    assert "support@zedapply.com" in turn.response
    mock_wa.assert_not_awaited()


@pytest.mark.asyncio
async def test_user_escalation_ack_email_sent(fake_supabase, bwana_cache_table):
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "test-user-id",
                    "email": "user@example.com",
                }
            ]
        ),
    )
    with patch(
        "app.services.bwana_chat.send_whatsapp_message",
        new_callable=AsyncMock,
    ) as mock_wa:
        mock_wa.return_value = {"sent": True}
        with patch(
            "app.services.bwana_chat._send",
            return_value=True,
        ) as mock_send:
            turn = await process_bwana_message(
                user_id="test-user-id",
                message="I want to speak to a human",
                session_id="sess-user-email",
                supabase=fake_supabase,
            )
    assert turn.source == "escalated"
    user_calls = [
        c
        for c in mock_send.call_args_list
        if c.args and c.args[0] == "user@example.com"
    ]
    assert user_calls
    logs = fake_supabase._tables["bwana_escalation_log"]._data
    assert "user_email" in logs[0].get("channels", [])


@pytest.mark.asyncio
async def test_unsatisfied_triggers_escalation_log(
    fake_supabase, bwana_cache_table
):
    with patch(
        "app.services.bwana_chat.send_whatsapp_message",
        new_callable=AsyncMock,
    ) as mock_wa:
        mock_wa.return_value = {"sent": True}
        turn = await process_bwana_message(
            user_id="test-user-id",
            message="I'm not satisfied with this",
            session_id="sess-unsat",
            supabase=fake_supabase,
        )
    assert turn.source == "escalated"
    assert turn.escalation_ticket_id
    assert "Sorry" in turn.response or "support@zedapply.com" in turn.response
    mock_wa.assert_awaited_once()
    logs = fake_supabase._tables["bwana_escalation_log"]._data
    assert logs
    assert logs[0].get("reason") == "unsatisfied"
    assert logs[0].get("ticket_id") == turn.escalation_ticket_id


@pytest.mark.asyncio
async def test_system_prompt_says_chatbot_not_llm(fake_supabase, bwana_cache_table):
    cfg = BwanaConfig.model_validate(BWANA_CONFIG_ROW)
    prompt = await build_bwana_system_prompt(cfg, fake_supabase)
    lower = prompt.lower()
    assert "chatbot" in lower
    assert "never say you are an llm" in lower


@pytest.mark.asyncio
async def test_bwana_falls_back_to_llm_on_unknown(fake_supabase, bwana_cache_table):
    question = "Should I list employment dates as month-year or year-only?"
    with patch(
        "app.services.bwana_chat._call_llm",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = "Use month-year for recent roles; year-only if 10+ years ago."
        turn = await process_bwana_message(
            user_id="test-user-id",
            message=question,
            session_id="sess-2",
            supabase=fake_supabase,
        )
    assert turn.source == "llm"
    assert "month-year" in turn.response
    mock_llm.assert_awaited_once()


def test_bwana_persists_history_in_ai_cache(fake_supabase, bwana_cache_table):
    append_and_persist_history(
        fake_supabase,
        user_id="test-user-id",
        session_id="sess-3",
        user_message="hello",
        assistant_message="Hi there",
        source="faq",
    )
    key = session_cache_key("test-user-id", "sess-3")
    rows = fake_supabase._tables["ai_cache"]._data
    assert rows
    assert rows[0]["cache_key"] == key
    assert rows[0]["cache_type"] == "bwana_chat"
    msgs = rows[0]["result"]["messages"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["source"] == "faq"

    history = load_conversation_history(fake_supabase, "test-user-id", "sess-3")
    assert len(history) == 2


@pytest.mark.asyncio
async def test_bwana_chat_endpoint_faq(client, auth_headers, fake_supabase, bwana_cache_table):
    _seed_user(fake_supabase)
    resp = client.post(
        "/api/v1/bwana/chat",
        headers=auth_headers,
        json={"message": "what's the price", "session_id": "web-sess"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "faq"
    assert "K125" in body["response"]
    assert body["session_id"] == "web-sess"
    assert body["took_ms"] >= 0


@pytest.mark.asyncio
async def test_bwana_chat_endpoint_escalated(client, auth_headers, fake_supabase, bwana_cache_table):
    _seed_user(fake_supabase)
    with patch(
        "app.services.bwana_chat.send_whatsapp_message",
        new_callable=AsyncMock,
    ) as mock_wa:
        mock_wa.return_value = {}
        resp = client.post(
            "/api/v1/bwana/chat",
            headers=auth_headers,
            json={"message": "I want to speak to a human"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "escalated"
    assert body.get("escalation_ticket_id", "").startswith("ZD-")
    mock_wa.assert_awaited()


@pytest.mark.asyncio
async def test_handle_bwana_persists_after_llm(fake_supabase, bwana_cache_table):
    with patch(
        "app.services.bwana_chat._call_llm",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = "Prefer month-year on CV dates."
        await handle_bwana_chat(
            user_id="u1",
            message="CV date format?",
            session_id="s-persist",
            supabase=fake_supabase,
        )
    history = load_conversation_history(fake_supabase, "u1", "s-persist")
    assert len(history) == 2
    assert history[-1]["role"] == "assistant"
