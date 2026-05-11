"""Embedding generation using Google Gemini.

Default model: `gemini-embedding-001` (the current public Gemini embedding
model). Native output is 3072 dimensions; we use Matryoshka Representation
Learning (the `outputDimensionality` parameter) to truncate to the size of
our `vector(N)` column — 768 by default. This lets us swap models without
migrating the DB.

Note: the older `text-embedding-004` was retired from the v1beta endpoint
on 2026-05 (returns 404 for embedContent). `gemini-embedding-001` is now
the only recommended modern path; older `text-embedding-*` aliases are
gone.

Free tier limits: 1,500 requests/min, generous daily token allowance.
"""
import asyncio
import hashlib
import logging
from functools import lru_cache

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding via Gemini `embedContent`.

    Output dimensionality is taken from `settings.embedding_dimensions`
    (default 768). With `gemini-embedding-001`, this is achieved via
    Matryoshka truncation of the native 3072-dim vector. The returned
    list always has exactly `settings.embedding_dimensions` floats.

    Uses httpx async — no thread pool needed.
    """
    settings = get_settings()
    truncated = text[:32000]

    url = GEMINI_EMBED_URL.format(model=settings.embedding_model)

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                url,
                params={"key": settings.gemini_api_key},
                json={
                    "model": f"models/{settings.embedding_model}",
                    "content": {"parts": [{"text": truncated}]},
                    # Matryoshka truncation — supported by gemini-embedding-001.
                    # Older models silently 400 with this param; that's the
                    # signal that the EMBEDDING_MODEL env var needs updating.
                    "outputDimensionality": settings.embedding_dimensions,
                },
            )

            if response.status_code == 401 or response.status_code == 403:
                logger.error("Gemini API key is invalid or missing")
                raise ValueError("Embedding service is not configured. Please contact support.")

            if response.status_code == 429:
                logger.warning("Gemini rate limit hit during embedding generation")
                raise ValueError("Embedding service is temporarily busy. Please try again in a moment.")

            if response.status_code != 200:
                logger.error(f"Gemini API error {response.status_code}: {response.text[:200]}")
                raise ValueError("Embedding service is temporarily unavailable.")

            data = response.json()
            return data["embedding"]["values"]

        except httpx.TimeoutException:
            logger.error("Gemini embedding request timed out")
            raise ValueError("Embedding service timed out. Please try again.")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during Gemini embedding: {e}")
            raise ValueError("Embedding service is temporarily unavailable.")
        except KeyError:
            logger.error(f"Unexpected Gemini response format: {response.text[:200]}")
            raise ValueError("Embedding service returned an unexpected response.")


def compute_cache_key(text: str, prefix: str = "emb") -> str:
    """SHA256 hash for ai_cache deduplication."""
    return hashlib.sha256(f"{prefix}:{text}".encode()).hexdigest()
