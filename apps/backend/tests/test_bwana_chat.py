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
from tests.conftest import FakeSupabaseQuery


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
    q = FakeSupabaseQuery(data=[])
    fake_supabase.set_table("ai_cache", q)
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
        response, source = await process_bwana_message(
            user_id="test-user-id",
            message="I want to speak to a human",
            session_id="sess-1",
            supabase=fake_supabase,
        )
    assert source == "escalated"
    assert "Kaluba" in response
    mock_wa.assert_awaited_once()


@pytest.mark.asyncio
async def test_bwana_falls_back_to_llm_on_unknown(fake_supabase, bwana_cache_table):
    question = "Should I list employment dates as month-year or year-only?"
    with patch(
        "app.services.bwana_chat._call_openrouter_llm",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = "Use month-year for recent roles; year-only if 10+ years ago."
        response, source = await process_bwana_message(
            user_id="test-user-id",
            message=question,
            session_id="sess-2",
            supabase=fake_supabase,
        )
    assert source == "llm"
    assert "month-year" in response
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
    assert resp.json()["source"] == "escalated"
    mock_wa.assert_awaited()


@pytest.mark.asyncio
async def test_handle_bwana_persists_after_llm(fake_supabase, bwana_cache_table):
    with patch(
        "app.services.bwana_chat._call_openrouter_llm",
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
