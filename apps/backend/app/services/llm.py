"""Central LLM usage logging — OpenRouter, Gemini embeddings, OpenAI.

Wraps chat completions and embedding calls to persist token counts and
estimated USD cost into `llm_usage_log` (migration 064).
"""
from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, replace
from typing import Any

from supabase import Client

from app.core.deps import get_supabase

logger = logging.getLogger(__name__)

# Product features surfaced on the admin cost panel (Prompt 4F).
FEATURE_MATCHING = "matching"
FEATURE_CV_PARSING = "cv_parsing"
FEATURE_BWANA = "bwana"
FEATURE_INTERVIEW_PREP = "interview_prep"
FEATURE_APTITUDE = "aptitude"
FEATURE_OTHER = "other"

DASHBOARD_FEATURES = (
    FEATURE_MATCHING,
    FEATURE_CV_PARSING,
    FEATURE_BWANA,
    FEATURE_INTERVIEW_PREP,
    FEATURE_APTITUDE,
)

# OpenRouter USD per 1M tokens (input / output). Source: openrouter.ai/models
# snapshots 2026-05; unknown models fall back to DEFAULT_OPENROUTER_PRICING.
OPENROUTER_PRICE_PER_MILLION: dict[str, tuple[float, float]] = {
    "google/gemini-2.0-flash-001": (0.10, 0.40),
    "google/gemini-2.0-flash-exp:free": (0.0, 0.0),
    "google/gemini-flash-1.5": (0.075, 0.30),
    "google/gemini-flash-1.5-8b": (0.0375, 0.15),
    "openai/gpt-4o-mini": (0.15, 0.60),
}
DEFAULT_OPENROUTER_PRICING = (0.15, 0.60)

# Direct Gemini API (embedContent) — USD per 1M input tokens.
GEMINI_EMBED_PRICE_PER_MILLION: dict[str, float] = {
    "gemini-embedding-001": 0.15,
    "text-embedding-004": 0.10,
}
DEFAULT_GEMINI_EMBED_PRICE_PER_MILLION = 0.15

# OpenAI direct (cover letters via ai_service.py).
OPENAI_PRICE_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
}
DEFAULT_OPENAI_PRICING = (0.15, 0.60)


@dataclass(frozen=True)
class LlmLogContext:
    """Metadata attached to each inference call."""

    feature: str
    route: str = "unknown"
    user_id: str | None = None
    request_id: str | None = None
    provider: str = "openrouter"


_llm_context: ContextVar[LlmLogContext | None] = ContextVar("llm_log_context", default=None)


def set_llm_context(ctx: LlmLogContext) -> Token[LlmLogContext | None]:
    return _llm_context.set(ctx)


def reset_llm_context(token: Token[LlmLogContext | None]) -> None:
    _llm_context.reset(token)


def get_llm_context() -> LlmLogContext | None:
    return _llm_context.get()


def merge_llm_context(**kwargs: object) -> LlmLogContext:
    """Return context merged with overrides; uses ambient context when set."""
    base = get_llm_context()
    if base is None:
        base = LlmLogContext(feature=FEATURE_OTHER)
    return replace(base, **kwargs)  # type: ignore[arg-type]


def estimate_openrouter_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    input_rate, output_rate = OPENROUTER_PRICE_PER_MILLION.get(
        model, DEFAULT_OPENROUTER_PRICING
    )
    return (
        (prompt_tokens / 1_000_000.0) * input_rate
        + (completion_tokens / 1_000_000.0) * output_rate
    )


def estimate_gemini_embed_cost_usd(model: str, prompt_tokens: int) -> float:
    rate = GEMINI_EMBED_PRICE_PER_MILLION.get(
        model, DEFAULT_GEMINI_EMBED_PRICE_PER_MILLION
    )
    return (prompt_tokens / 1_000_000.0) * rate


def estimate_openai_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    input_rate, output_rate = OPENAI_PRICE_PER_MILLION.get(
        model, DEFAULT_OPENAI_PRICING
    )
    return (
        (prompt_tokens / 1_000_000.0) * input_rate
        + (completion_tokens / 1_000_000.0) * output_rate
    )


def extract_usage_from_completion(response: Any) -> tuple[int, int, str | None]:
    """Return (prompt_tokens, completion_tokens, request_id)."""
    usage = getattr(response, "usage", None)
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
    completion = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
    req_id = getattr(response, "id", None)
    return prompt, completion, str(req_id) if req_id else None


def record_llm_usage(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    context: LlmLogContext,
    supabase: Client | None = None,
) -> None:
    """Fire-and-forget insert into llm_usage_log. Never raises to callers."""
    request_id = context.request_id or str(uuid.uuid4())
    row = {
        "request_id": request_id,
        "user_id": context.user_id,
        "route": context.route[:128],
        "feature": context.feature[:32],
        "provider": context.provider,
        "model": model[:80],
        "prompt_tokens": max(0, prompt_tokens),
        "completion_tokens": max(0, completion_tokens),
        "cost_usd": round(max(0.0, cost_usd), 8),
    }
    logger.info(
        "llm_usage feature=%s model=%s prompt=%s completion=%s cost_usd=%.8f route=%s",
        row["feature"],
        row["model"],
        row["prompt_tokens"],
        row["completion_tokens"],
        row["cost_usd"],
        row["route"],
    )
    client = supabase
    if client is None:
        try:
            client = get_supabase()
        except Exception:
            return
    try:
        client.table("llm_usage_log").insert(row).execute()
    except Exception as exc:  # pragma: no cover - must not break inference
        logger.debug("llm_usage_log insert failed: %s", exc)


def record_openrouter_completion(
    response: Any,
    *,
    model: str,
    context: LlmLogContext | None = None,
    supabase: Client | None = None,
) -> None:
    ctx = context or get_llm_context() or LlmLogContext(feature=FEATURE_OTHER)
    prompt, completion, req_id = extract_usage_from_completion(response)
    if req_id and not ctx.request_id:
        ctx = replace(ctx, request_id=req_id)
    cost = estimate_openrouter_cost_usd(model, prompt, completion)
    record_llm_usage(
        model=model,
        prompt_tokens=prompt,
        completion_tokens=completion,
        cost_usd=cost,
        context=replace(ctx, provider="openrouter"),
        supabase=supabase,
    )


def record_gemini_embedding(
    *,
    model: str,
    prompt_tokens: int,
    context: LlmLogContext | None = None,
    supabase: Client | None = None,
) -> None:
    ctx = context or get_llm_context() or LlmLogContext(
        feature=FEATURE_MATCHING, provider="gemini"
    )
    cost = estimate_gemini_embed_cost_usd(model, prompt_tokens)
    record_llm_usage(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=0,
        cost_usd=cost,
        context=replace(ctx, provider="gemini"),
        supabase=supabase,
    )


def record_openai_completion(
    response: Any,
    *,
    model: str,
    context: LlmLogContext | None = None,
    supabase: Client | None = None,
) -> None:
    ctx = context or get_llm_context() or LlmLogContext(feature=FEATURE_OTHER)
    prompt, completion, req_id = extract_usage_from_completion(response)
    if req_id and not ctx.request_id:
        ctx = replace(ctx, request_id=req_id)
    cost = estimate_openai_cost_usd(model, prompt, completion)
    record_llm_usage(
        model=model,
        prompt_tokens=prompt,
        completion_tokens=completion,
        cost_usd=cost,
        context=replace(ctx, provider="openai"),
        supabase=supabase,
    )
