"""Admin-configurable FAQ intents (JSON on bwana_platform_config)."""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.schemas.bwana_config import FaqIntentItem
from app.services.bwana_faq import FaqMatch

logger = logging.getLogger(__name__)

_MAX_INTENTS = 50


def parse_faq_intents_json(raw: Any) -> list[FaqIntentItem]:
    """Validate admin FAQ JSON; return empty list on invalid stored data."""
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("bwana faq_intents_json is not valid JSON")
            return []
    if not isinstance(raw, list):
        return []
    items: list[FaqIntentItem] = []
    for entry in raw[:_MAX_INTENTS]:
        if not isinstance(entry, dict):
            continue
        try:
            item = FaqIntentItem.model_validate(entry)
            triggers = _normalize_triggers(item.triggers)
            if not triggers:
                continue
            items.append(
                FaqIntentItem(
                    intent_id=item.intent_id,
                    enabled=item.enabled,
                    triggers=triggers,
                    response=item.response.strip(),
                )
            )
        except ValidationError as exc:
            logger.warning("skip invalid faq intent: %s", exc)
    return items


def _normalize_triggers(triggers: list[str]) -> list[str]:
    out: list[str] = []
    for t in triggers:
        norm = t.strip().lower()
        if norm and norm not in out:
            out.append(norm)
    return out


def faq_intents_for_db(intents: list[FaqIntentItem]) -> list[dict[str, Any]]:
    return [i.model_dump() for i in intents]


def match_custom_faq(message: str, intents: list[FaqIntentItem]) -> FaqMatch | None:
    """Match admin FAQ intents after built-in intents miss."""
    norm = message.strip().lower()
    if not norm:
        return None
    for item in intents:
        if not item.enabled:
            continue
        if any(trigger in norm for trigger in item.triggers):
            return FaqMatch(item.intent_id, item.response)
    return None
