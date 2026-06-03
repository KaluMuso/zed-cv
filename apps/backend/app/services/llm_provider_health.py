"""In-process last-known status for LLM providers (health probe)."""
from __future__ import annotations

import threading

_lock = threading.Lock()
_status: dict[str, str] = {
    "gemini_direct": "unknown",
    "openrouter": "unknown",
}


def record_llm_provider_status(provider: str, status: str) -> None:
    """Record outcome of an LLM call (ok, error, quota_exhausted, not_configured)."""
    with _lock:
        _status[provider] = status


def get_llm_provider_status() -> dict[str, str]:
    with _lock:
        return dict(_status)


def reset_llm_provider_status_for_tests() -> None:
    with _lock:
        _status["gemini_direct"] = "unknown"
        _status["openrouter"] = "unknown"
