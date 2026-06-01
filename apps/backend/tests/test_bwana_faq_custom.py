"""Custom admin FAQ intents for Bwana."""
from app.schemas.bwana_config import FaqIntentItem
from app.services.bwana_faq import match_faq
from app.services.bwana_faq_custom import match_custom_faq, parse_faq_intents_json


def test_parse_faq_intents_json_valid():
    raw = [
        {
            "intent_id": "office_hours",
            "enabled": True,
            "triggers": ["office hours", "open saturday"],
            "response": "We reply within 24h on business days.",
        }
    ]
    items = parse_faq_intents_json(raw)
    assert len(items) == 1
    assert items[0].intent_id == "office_hours"


def test_custom_faq_after_builtin_miss():
    msg = "do you have a physical office in kitwe"
    builtin = match_faq(msg)
    assert builtin is None
    custom = match_custom_faq(
        msg,
        [
            FaqIntentItem(
                intent_id="office_hours",
                enabled=True,
                triggers=["physical office in kitwe"],
                response="Email us at support.",
            )
        ],
    )
    assert custom is not None
    assert custom.intent_id == "office_hours"
