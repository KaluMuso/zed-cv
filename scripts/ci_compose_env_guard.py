#!/usr/bin/env python3
"""CI guard: every ${VAR} in infra/*/docker-compose*.yml must be declared
in the sibling .env.example.

Catches PR #26-style drift where a compose file references a variable for
substitution at `docker-compose up` time, but no operator-facing
.env.example documents it — so a fresh `cp .env.example .env` produces a
silent empty value and the service starts up with auth disabled.

Also surfaces (warn-only) suspicious-looking secrets accidentally committed
to .env.example. We don't fail on these because regexes have false
positives; we only print so a human can investigate before merge.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent

# ${VAR}, ${VAR:-default}, ${VAR-default}, ${VAR:?err}, ${VAR?err}, ${VAR:+alt}
_VAR_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(?::?[-+?][^}]*)?\}")
# Bare $VAR (no braces) — compose supports this too.
_BARE_VAR_RE = re.compile(r"(?<![\\\$])\$([A-Z_][A-Z0-9_]*)\b")

# Heuristic patterns for secrets accidentally committed to .env.example.
# All warn-only — false positives are likely, so we surface and let a
# human decide.
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("OpenAI/Anthropic-style API key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("JWT-shaped token", re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Long hex string (>=32 chars)", re.compile(r"\b[0-9a-fA-F]{32,}\b")),
]


@dataclass
class Drift:
    compose_file: str
    env_example: str | None
    missing: list[str] = field(default_factory=list)
    suspicious_secrets: list[str] = field(default_factory=list)
    env_example_missing: bool = False

    def to_dict(self) -> dict:
        return {
            "compose_file": self.compose_file,
            "env_example": self.env_example,
            "missing": sorted(set(self.missing)),
            "suspicious_secrets": self.suspicious_secrets,
            "env_example_missing": self.env_example_missing,
        }


def _extract_vars(compose_text: str) -> set[str]:
    found: set[str] = set()
    for m in _VAR_RE.finditer(compose_text):
        found.add(m.group(1))
    for m in _BARE_VAR_RE.finditer(compose_text):
        found.add(m.group(1))
    return found


def _parse_env_keys(env_text: str) -> set[str]:
    keys: set[str] = set()
    for raw in env_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        if re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
            keys.add(key)
    return keys


def _scan_secrets(env_text: str) -> list[str]:
    hits: list[str] = []
    for raw in env_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        _, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        if not value:
            continue
        for label, pat in _SECRET_PATTERNS:
            if pat.search(value):
                # Mask the value for the output so we don't echo the
                # secret if it really is one. Keep enough for a human
                # to recognise the key.
                preview = value if len(value) <= 12 else value[:6] + "…" + value[-4:]
                hits.append(f"{label}: {raw.split('=', 1)[0]}={preview}")
                break
    return hits


def _iter_compose_files(infra_root: Path) -> Iterable[Path]:
    for path in sorted(infra_root.glob("*/docker-compose*.yml")):
        # Skip overlays in subdirs we don't recognise; explicit glob keeps
        # us tied to infra/<service>/docker-compose*.yml only.
        yield path


def check(infra_root: Path | None = None) -> list[Drift]:
    infra_root = infra_root or (REPO_ROOT / "infra")
    drifts: list[Drift] = []
    for compose_path in _iter_compose_files(infra_root):
        text = compose_path.read_text(encoding="utf-8")
        referenced = _extract_vars(text)
        if not referenced:
            continue

        env_example = compose_path.parent / ".env.example"
        rel_compose = _relpath(compose_path)
        if not env_example.exists():
            drifts.append(
                Drift(
                    compose_file=rel_compose,
                    env_example=None,
                    missing=sorted(referenced),
                    env_example_missing=True,
                )
            )
            continue

        env_text = env_example.read_text(encoding="utf-8")
        declared = _parse_env_keys(env_text)
        missing = sorted(v for v in referenced if v not in declared)
        secrets = _scan_secrets(env_text)
        if missing or secrets:
            drifts.append(
                Drift(
                    compose_file=rel_compose,
                    env_example=_relpath(env_example),
                    missing=missing,
                    suspicious_secrets=secrets,
                )
            )
    return drifts


def _relpath(p: Path) -> str:
    """Path relative to REPO_ROOT when possible; absolute posix otherwise.

    Tests pass tempdir paths that aren't under REPO_ROOT — the guard
    shouldn't crash on those.
    """
    try:
        return p.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def _human_report(drifts: list[Drift]) -> str:
    if not drifts:
        return "compose-env-guard: OK (all ${VAR} references documented in .env.example)"
    lines = ["compose-env-guard: drift detected", ""]
    for d in drifts:
        lines.append(f"  {d.compose_file}")
        if d.env_example_missing:
            lines.append(
                f"    ⚠ no .env.example next to this compose file; "
                f"referenced vars: {', '.join(d.missing)}"
            )
            continue
        if d.missing:
            lines.append(f"    ⚠ missing from {d.env_example}:")
            for v in d.missing:
                lines.append(f"        - {v}")
        if d.suspicious_secrets:
            lines.append("    (warn) suspicious values in .env.example:")
            for s in d.suspicious_secrets:
                lines.append(f"        - {s}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--infra-root",
        default=str(REPO_ROOT / "infra"),
        help="Root directory containing service subdirs with docker-compose*.yml",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON drift report on stdout.",
    )
    args = parser.parse_args(argv)

    drifts = check(Path(args.infra_root))
    # Suspicious-secret hits are warn-only. Fail only on missing-var or
    # missing-env-example.
    hard_fail = any(d.missing or d.env_example_missing for d in drifts)

    if args.json:
        json.dump(
            {
                "ok": not hard_fail,
                "drifts": [d.to_dict() for d in drifts],
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        print(_human_report(drifts))

    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
