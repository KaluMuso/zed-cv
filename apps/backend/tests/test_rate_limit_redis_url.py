"""REDIS_URL normalization when operators paste Upstash CLI snippets."""
from app.core.rate_limit import normalize_redis_url


def test_normalize_extracts_rediss_url_from_cli_snippet():
    raw = (
        "redis-cli --tls -u "
        "redis://default:secret@wanted-lamb-70574.upstash.io:6379"
    )
    assert (
        normalize_redis_url(raw)
        == "redis://default:secret@wanted-lamb-70574.upstash.io:6379"
    )


def test_normalize_passes_through_clean_url():
    url = "rediss://default:token@host.upstash.io:6379"
    assert normalize_redis_url(url) == url


def test_normalize_empty():
    assert normalize_redis_url("") == ""
    assert normalize_redis_url("   ") == ""
