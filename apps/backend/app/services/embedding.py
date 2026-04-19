"""Embedding generation service using OpenAI text-embedding-3-small."""

import hashlib
import json
from openai import OpenAI

from app.core.config import get_settings


def get_openai_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


async def generate_embedding(text: str) -> list[float]:
    """Generate a 1536-dim embedding for the given text.

    Uses OpenAI text-embedding-3-small (~$0.02 per 1M tokens).
    """
    settings = get_settings()
    client = get_openai_client()

    # Truncate to ~8000 tokens (~32000 chars) to stay within model limits
    truncated = text[:32000]

    response = client.embeddings.create(
        model=settings.embedding_model,
        input=truncated,
        dimensions=settings.embedding_dimensions,
    )

    return response.data[0].embedding


def compute_cache_key(text: str, prefix: str = "emb") -> str:
    """SHA256 hash for AI cache deduplication."""
    return hashlib.sha256(f"{prefix}:{text}".encode()).hexdigest()
