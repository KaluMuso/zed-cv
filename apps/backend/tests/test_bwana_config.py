"""Bwana platform config — templates and validation."""
import pytest

from app.schemas.bwana_config import BwanaConfig, BwanaConfigPatch
from app.services.bwana_config import get_bwana_config, render_template
from tests.conftest import FakeSupabaseQuery

DEFAULT_ROW = {
    "id": 1,
    "chatbot_display_name": "Bwana",
    "operator_display_name": "ZedApply Support",
    "support_email": "support@zedapply.com",
    "support_phone": "+260971234567",
    "escalation_whatsapp_phone": "+260971234567",
    "escalation_sla_hours": 24,
    "human_escalation_reply_template": "Human: {email} {phone} {sla} {operator} {chatbot_name}",
    "unsatisfied_reply_template": "Sorry: {email}",
    "contact_admin_reply_template": "Contact {operator} at {email}",
    "user_escalation_ack_template": (
        "Thanks — reference {ticket_id}. {operator} will email you at {email} within {sla}h."
    ),
    "public_knowledge_extra": "",
    "enable_email_escalation": True,
    "enable_user_escalation_ack": True,
}


@pytest.fixture
def bwana_tables(fake_supabase):
    fake_supabase.set_table(
        "bwana_platform_config", FakeSupabaseQuery(data=[DEFAULT_ROW.copy()])
    )
    fake_supabase.set_table("bwana_escalation_log", FakeSupabaseQuery(data=[]))
    return fake_supabase


def test_render_template_substitutes_placeholders():
    cfg = BwanaConfig.model_validate(DEFAULT_ROW)
    out = render_template(
        "Email {email}, phone {phone}, SLA {sla}h, {operator}, {chatbot_name}",
        cfg,
    )
    assert "support@zedapply.com" in out
    assert "+260971234567" in out
    assert "24" in out
    assert "ZedApply Support" in out
    assert "Bwana" in out


def test_bwana_config_patch_validates_phone():
    with pytest.raises(ValueError, match="Zambian"):
        BwanaConfigPatch(support_phone="not-a-phone")


def test_get_bwana_config_from_table(bwana_tables):
    cfg = get_bwana_config(bwana_tables, force=True)
    assert cfg.support_email == "support@zedapply.com"
