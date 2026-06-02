"""Embedding generation — Gemini direct or OpenRouter (same gemini-embedding-001).

Default path: Google `embedContent` API. Set ``EMBEDDING_VIA_OPENROUTER=true``
(or rely on auto-fallback when direct Gemini returns 403) to route through
OpenRouter while keeping model + 768-dim Matryoshka output unchanged.
"""
from __future__ import annotations

import hashlib
import logging

import httpx

from app.core.config import get_settings
from app.lib.retry import LLMCircuitOpenError, async_call_with_llm_retry, circuit_is_open
from app.services.llm import (
    FEATURE_MATCHING,
    LlmLogContext,
    merge_llm_context,
    record_gemini_embedding,
    record_openrouter_embedding,
)

logger = logging.getLogger(__name__)

GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"


def _openrouter_embed_model(model: str) -> str:
    if model.startswith("google/"):
        return model
    return f"google/{model}"


def _gemini_access_denied(status: int, body: str) -> bool:
    if status not in (401, 403):
        return False
    lower = body.lower()
    return (
        "denied access" in lower
        or "permission_denied" in lower
        or "invalid or missing" in lower
        or "unregistered callers" in lower
        or status == 401
    )


async def _embed_via_gemini(
    text: str,
    *,
    log_context: LlmLogContext | None,
    supabase,
) -> list[float]:
    settings = get_settings()
    url = GEMINI_EMBED_URL.format(model=settings.embedding_model)
    payload = {
        "model": f"models/{settings.embedding_model}",
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": settings.embedding_dimensions,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await async_call_with_llm_retry(
                lambda: client.post(
                    url,
                    params={"key": settings.gemini_api_key},
                    json=payload,
                ),
                log_prefix="gemini_embed",
            )
        except LLMCircuitOpenError:
            raise ValueError(
                "Embedding service is temporarily unavailable. Please try again shortly."
            ) from None

        if _gemini_access_denied(response.status_code, response.text):
            raise _GeminiEmbedAccessDenied(response.status_code, response.text[:200])

        if response.status_code == 429:
            logger.warning("Gemini rate limit hit during embedding generation")
            raise ValueError(
                "Embedding service is temporarily busy. Please try again in a moment."
            )

        if response.status_code >= 500:
            raise httpx.HTTPStatusError(
                "Gemini server error",
                request=response.request,
                response=response,
            )
        if response.status_code != 200:
            logger.error(
                "Gemini API error %s: %s",
                response.status_code,
                response.text[:200],
            )
            raise ValueError("Embedding service is temporarily unavailable.")

        data = response.json()
        usage = data.get("usageMetadata") or {}
        prompt_tokens = int(usage.get("promptTokenCount") or 0)
        if prompt_tokens <= 0:
            prompt_tokens = max(1, len(text) // 4)
        ctx = log_context or merge_llm_context(feature=FEATURE_MATCHING)
        record_gemini_embedding(
            model=settings.embedding_model,
            prompt_tokens=prompt_tokens,
            context=ctx,
            supabase=supabase,
        )
        values = data.get("embedding", {}).get("values")
        if not isinstance(values, list):
            raise ValueError("Embedding service returned an unexpected response.")
        return _ensure_embedding_dim(values, expected=settings.embedding_dimensions)


async def _embed_via_openrouter(
    text: str,
    *,
    log_context: LlmLogContext | None,
    supabase,
) -> list[float]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("Embedding service is not configured. Please contact support.")

    model = _openrouter_embed_model(settings.embedding_model)
    url = f"{settings.openrouter_base_url.rstrip('/')}/embeddings"
    payload = {
        "model": model,
        "input": text,
        "dimensions": settings.embedding_dimensions,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await async_call_with_llm_retry(
                lambda: client.post(url, headers=headers, json=payload),
                log_prefix="openrouter_embed",
            )
        except LLMCircuitOpenError:
            raise ValueError(
                "Embedding service is temporarily unavailable. Please try again shortly."
            ) from None

        if response.status_code in (401, 403):
            logger.error("OpenRouter embedding auth failed: %s", response.text[:200])
            raise ValueError("Embedding service is not configured. Please contact support.")
        if response.status_code == 429:
            raise ValueError(
                "Embedding service is temporarily busy. Please try again in a moment."
            )
        if response.status_code != 200:
            logger.error(
                "OpenRouter embed error %s: %s",
                response.status_code,
                response.text[:200],
            )
            raise ValueError("Embedding service is temporarily unavailable.")

        data = response.json()
        rows = data.get("data") or []
        if not rows or not isinstance(rows[0].get("embedding"), list):
            raise ValueError("Embedding service returned an unexpected response.")

        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("total_tokens") or 0)
        if prompt_tokens <= 0:
            prompt_tokens = max(1, len(text) // 4)
        cost_usd = usage.get("cost")
        ctx = log_context or merge_llm_context(feature=FEATURE_MATCHING)
        record_openrouter_embedding(
            model=model,
            prompt_tokens=prompt_tokens,
            cost_usd=float(cost_usd) if cost_usd is not None else None,
            context=ctx,
            supabase=supabase,
        )
        return _ensure_embedding_dim(
            rows[0]["embedding"], expected=settings.embedding_dimensions
        )


class _GeminiEmbedAccessDenied(Exception):
    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail
        super().__init__(detail)


def _ensure_embedding_dim(values: list, *, expected: int) -> list[float]:
    if len(values) != expected:
        raise ValueError(
            f"Embedding dimension mismatch: got {len(values)}, expected {expected}"
        )
    return values


async def generate_embedding(
    text: str,
    *,
    log_context: LlmLogContext | None = None,
    supabase=None,
) -> list[float]:
    """Return a ``settings.embedding_dimensions``-length embedding vector."""
    if circuit_is_open():
        raise ValueError(
            "Embedding service is temporarily unavailable. Please try again shortly."
        )

    settings = get_settings()
    truncated = text[:32000]

    if settings.embedding_via_openrouter:
        return await _embed_via_openrouter(
            truncated, log_context=log_context, supabase=supabase
        )

    try:
        return await _embed_via_gemini(
            truncated, log_context=log_context, supabase=supabase
        )
    except _GeminiEmbedAccessDenied as exc:
        if settings.openrouter_api_key:
            logger.warning(
                "Direct Gemini embed denied (HTTP %s); falling back to OpenRouter",
                exc.status,
            )
            return await _embed_via_openrouter(
                truncated, log_context=log_context, supabase=supabase
            )
        raise ValueError(
            "Embedding service is not configured. Please contact support."
        ) from exc
    except httpx.TimeoutException:
        logger.error("Gemini embedding request timed out")
        raise ValueError("Embedding service timed out. Please try again.")
    except httpx.HTTPError as exc:
        logger.error("HTTP error during Gemini embedding: %s", exc)
        raise ValueError("Embedding service is temporarily unavailable.")


def compute_cache_key(text: str, prefix: str = "emb") -> str:
    """SHA256 hash for ai_cache deduplication."""
    return hashlib.sha256(f"{prefix}:{text}".encode()).hexdigest()
