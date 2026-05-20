"""WAHA webhook for WhatsApp channel job scraping (Track 4c)."""
from __future__ import annotations

import hmac
import logging
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.core.deps import get_supabase
from app.services.whatsapp_classifier import (
    classify_whatsapp_image,
    classify_whatsapp_text,
)
from app.services.whatsapp_ingest import ingest_whatsapp_classification
from app.services.whatsapp_scraper import (
    channel_matches_config,
    parse_scrape_channels,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Scraper"])


def _verify_webhook_token(request: Request) -> None:
    settings = get_settings()
    secret = settings.whatsapp_scraper_webhook_token
    if not secret:
        logger.warning(
            "WhatsApp scraper webhook: WHATSAPP_SCRAPER_WEBHOOK_TOKEN unset — "
            "accepting unauthenticated traffic (dev only)"
        )
        return
    provided = request.headers.get("x-webhook-token", "")
    if not hmac.compare_digest(provided, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook token")


def _resolve_chat_id(payload: dict) -> str:
    return (
        payload.get("from")
        or payload.get("chatId")
        or payload.get("to")
        or ""
    ).strip()


def _message_id(payload: dict) -> str:
    return str(payload.get("id") or payload.get("messageId") or "").strip()


async def _download_waha_media(media: dict, settings) -> tuple[bytes, str]:
    """Fetch image bytes from WAHA media.url."""
    url = media.get("url") or ""
    if not url:
        raise ValueError("missing media url")
    mime = media.get("mimetype") or "image/jpeg"
    headers = {"X-Api-Key": settings.waha_api_key}
    parsed = urlparse(url)
    if parsed.hostname in ("localhost", "127.0.0.1", "waha"):
        base = settings.waha_api_url.rstrip("/")
        path = parsed.path or url
        if parsed.query:
            path = f"{path}?{parsed.query}"
        fetch_url = f"{base}{path}"
    else:
        fetch_url = url
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(fetch_url, headers=headers)
        resp.raise_for_status()
        return resp.content, mime


@router.post("/scraper-webhook")
async def whatsapp_scraper_webhook(
    request: Request,
    supabase=Depends(get_supabase),
):
    """Receive WAHA message events from configured scrape channels."""
    _verify_webhook_token(request)
    settings = get_settings()
    channels = parse_scrape_channels(settings.whatsapp_scrape_channels)
    if not channels:
        return {"status": "ignored", "reason": "no_channels_configured"}

    body = await request.json()
    if body.get("event") not in ("message", "message.any"):
        return {"status": "ignored", "reason": "not_message_event"}

    payload = body.get("payload") or {}
    if payload.get("fromMe"):
        return {"status": "ignored", "reason": "from_me"}

    chat_id = _resolve_chat_id(payload)
    if not channel_matches_config(chat_id, channels):
        return {"status": "ignored", "reason": "not_scrape_channel"}

    msg_id = _message_id(payload)
    if not msg_id:
        return {"status": "ignored", "reason": "missing_message_id"}

    has_media = bool(payload.get("hasMedia"))
    media = payload.get("media") or {}
    body_text = (payload.get("body") or "").strip()

    try:
        if has_media and media.get("url"):
            mime = str(media.get("mimetype") or "")
            if not mime.startswith("image/"):
                return {"status": "ignored", "reason": "unsupported_media"}
            image_bytes, mime_type = await _download_waha_media(media, settings)
            extracted = await classify_whatsapp_image(
                image_bytes,
                mime_type=mime_type,
                caption=body_text,
                supabase=supabase,
            )
            ocr_text = extracted.ocr_text
        elif body_text:
            extracted = await classify_whatsapp_text(body_text, supabase=supabase)
            ocr_text = None
        else:
            return {"status": "ignored", "reason": "empty_message"}
    except ValueError as exc:
        logger.error("WhatsApp scraper classify infra error: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)[:200]) from exc

    return await ingest_whatsapp_classification(
        supabase,
        extracted,
        channel_id=chat_id,
        message_id=msg_id,
        message_body=body_text,
        ocr_source_text=ocr_text,
    )
