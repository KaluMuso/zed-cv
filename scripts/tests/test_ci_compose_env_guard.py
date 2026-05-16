"""Compose-env guard tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

from ci_compose_env_guard import _extract_vars, _parse_env_keys, _scan_secrets, check


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


# ── Helpers ──


def test_extract_vars_handles_brace_and_bare_forms():
    text = """
        WAHA_API_KEY=${WAHA_API_KEY}
        OPTIONAL=${MAYBE:-default}
        NESTED=${PORT?error}
        BARE=$PORT
    """
    assert _extract_vars(text) == {"WAHA_API_KEY", "MAYBE", "PORT"}


def test_parse_env_keys_ignores_comments_and_blank_lines():
    text = """
        # comment
        WAHA_API_KEY=secret-value
        export FOO=bar
        no_equals_here
    """
    assert _parse_env_keys(text) == {"WAHA_API_KEY", "FOO"}


def test_scan_secrets_flags_long_hex_and_jwt_shapes():
    # JWT header segment needs at least ~20 chars after "eyJ" for the
    # pattern to fire; that's deliberately not a hair-trigger.
    text = """
        JWT=eyJabcdefghijklmnopqrstuvwxyz0123456789ABC.eyJ0eXAiOiJKV1QifQ.signature_blob_here
        HEX=0123456789abcdef0123456789abcdef0123456789abcdef
    """
    hits = _scan_secrets(text)
    assert any("JWT" in h for h in hits)
    assert any("Long hex" in h for h in hits)


# ── End-to-end ──


def test_clean_compose_passes(tmp_path):
    infra = tmp_path / "infra"
    _write(
        infra / "waha" / "docker-compose.yml",
        """
        services:
          waha:
            environment:
              WAHA_API_KEY: ${WAHA_API_KEY}
        """,
    )
    _write(
        infra / "waha" / ".env.example",
        """
        WAHA_API_KEY=
        """,
    )
    drifts = check(infra)
    assert drifts == []


def test_missing_var_in_env_example_is_drift(tmp_path):
    infra = tmp_path / "infra"
    _write(
        infra / "waha" / "docker-compose.yml",
        """
        services:
          waha:
            environment:
              WAHA_API_KEY: ${WAHA_API_KEY}
              N8N_USER: ${N8N_USER}
        """,
    )
    _write(
        infra / "waha" / ".env.example",
        """
        WAHA_API_KEY=
        """,
    )
    drifts = check(infra)
    assert len(drifts) == 1
    assert drifts[0].missing == ["N8N_USER"]


def test_missing_env_example_entirely_is_drift(tmp_path):
    """PR #26 root cause: compose references ${X} but no .env.example
    exists next to the compose file."""
    infra = tmp_path / "infra"
    _write(
        infra / "waha" / "docker-compose.yml",
        """
        services:
          waha:
            environment:
              WAHA_API_KEY: ${WAHA_API_KEY}
        """,
    )
    drifts = check(infra)
    assert len(drifts) == 1
    assert drifts[0].env_example_missing is True
    assert drifts[0].missing == ["WAHA_API_KEY"]


def test_secret_in_env_example_is_warn_only_not_fail(tmp_path):
    """Suspicious secrets are surfaced for human review but do not
    fail the build (regex false positives are likely)."""
    infra = tmp_path / "infra"
    _write(
        infra / "waha" / "docker-compose.yml",
        """
        services:
          waha:
            environment:
              WAHA_API_KEY: ${WAHA_API_KEY}
        """,
    )
    _write(
        infra / "waha" / ".env.example",
        """
        WAHA_API_KEY=sk-real-looking-secret-that-shouldnt-be-here-abc123def456
        """,
    )
    drifts = check(infra)
    # Drift exists for the suspicious-secrets warning, but `missing`
    # is empty — so it'd be a warn, not a hard failure.
    assert len(drifts) == 1
    assert drifts[0].missing == []
    assert drifts[0].suspicious_secrets
