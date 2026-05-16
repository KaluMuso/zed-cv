#!/usr/bin/env python3
"""CI guard: every TypeScript interface used as an `apiFetch<...>` response
type in `apps/frontend/src/lib/api.ts` must match a schema in
`docs/openapi.yaml` — every TS field must exist on the OpenAPI schema.

Catches PR #24-style drift, where the frontend declared
`skills_extracted: string[]` but the backend / OpenAPI emit
`parsed_skills: string[]` — the upload toast then read an undefined key
and showed "0 skills extracted" even when 12 came back from the parser.

The guard is intentionally one-way:
   OpenAPI has fields TS doesn't  -> OK (frontend may ignore extras)
   TS has fields OpenAPI doesn't  -> DRIFT (frontend is reading
                                            fields the API doesn't send)

Mapping TS interface -> OpenAPI schema (heuristics, in order):
  1. `// @openapi SchemaName` comment immediately above the interface
  2. Exact name match
  3. Suffix swap (Result/Response, Detail, List)
  4. Fallback: unmapped TS interfaces are logged warn-only

Allow-list:  scripts/ci_openapi_ts_guard_allowlist.yml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API_TS = REPO_ROOT / "apps" / "frontend" / "src" / "lib" / "api.ts"
DEFAULT_OPENAPI = REPO_ROOT / "docs" / "openapi.yaml"
DEFAULT_ALLOWLIST = REPO_ROOT / "scripts" / "ci_openapi_ts_guard_allowlist.yml"

# ── OpenAPI loading ──


def _resolve_refs(spec: dict, node: object, seen: tuple[str, ...] = ()) -> object:
    """Recursively resolve $ref pointers within the same document. We
    intentionally don't pull `jsonref` in — the resolution we need is
    just '#/components/schemas/Name' and we want to control cycles."""
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            if ref in seen:
                return {}
            target = spec
            for part in ref[2:].split("/"):
                if not isinstance(target, dict):
                    return {}
                target = target.get(part, {})
            return _resolve_refs(spec, target, seen + (ref,))
        return {k: _resolve_refs(spec, v, seen) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_refs(spec, item, seen) for item in node]
    return node


def _schema_fields(schema: object) -> set[str] | None:
    """Pull top-level property names out of a (resolved) OpenAPI schema.

    For composed schemas (oneOf/anyOf/allOf), we union the properties
    across branches. If we can't see any properties on any branch,
    return None — the caller treats that as "skip, can't compare".
    """
    if not isinstance(schema, dict):
        return None
    out: set[str] = set()
    props = schema.get("properties")
    if isinstance(props, dict):
        out.update(props.keys())
    for key in ("oneOf", "anyOf", "allOf"):
        branches = schema.get(key)
        if isinstance(branches, list):
            for b in branches:
                f = _schema_fields(b)
                if f:
                    out.update(f)
    return out or None


def load_openapi(path: Path) -> dict[str, set[str]]:
    if yaml is None:
        raise SystemExit(
            "pyyaml not installed; run `pip install pyyaml` "
            "(see .github/workflows/schema_guard.yml)."
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    schemas = (raw.get("components") or {}).get("schemas") or {}
    out: dict[str, set[str]] = {}
    for name, schema in schemas.items():
        resolved = _resolve_refs(raw, schema)
        fields = _schema_fields(resolved)
        if fields is None:
            continue
        out[name] = fields
    return out


# ── TS parsing ──


_INTERFACE_RE = re.compile(
    r"(?P<lead>(?:^[ \t]*//[^\n]*\n)*)"
    r"^[ \t]*export\s+interface\s+(?P<name>\w+)"
    r"(?:\s+extends\s+(?P<extends>[^{]+?))?\s*\{",
    re.MULTILINE,
)
_OPENAPI_ANNOTATION_RE = re.compile(r"@openapi\s+(\w+)")


def _find_matching_brace(src: str, open_idx: int) -> int:
    """Return the index of the `}` matching the `{` at `open_idx`.

    Tracks string, template-literal, and comment context. Template
    `${...}` interpolations are skipped wholesale as part of the string
    (we don't recurse into the embedded expression — `}` inside an
    interpolation correctly pairs with the `${` rather than the outer
    `{`).
    """
    depth = 0
    i = open_idx
    n = len(src)
    in_single = in_double = in_back = in_block_comment = in_line_comment = False
    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
        elif in_line_comment:
            if ch == "\n":
                in_line_comment = False
        elif in_single:
            if ch == "\\":
                i += 2
                continue
            if ch == "'":
                in_single = False
        elif in_double:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_double = False
        elif in_back:
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                in_back = False
            elif ch == "$" and nxt == "{":
                # Skip the entire `${...}` interpolation. The matching `}`
                # belongs to the template, not the enclosing block, so we
                # consume it here without touching `depth`.
                j = i + 2
                sub = 1
                while j < n and sub > 0:
                    c2 = src[j]
                    if c2 == "\\":
                        j += 2
                        continue
                    if c2 == "{":
                        sub += 1
                    elif c2 == "}":
                        sub -= 1
                    j += 1
                i = j
                continue
        else:
            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if ch == "'":
                in_single = True
            elif ch == '"':
                in_double = True
            elif ch == "`":
                in_back = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    raise ValueError("Unbalanced braces parsing TS interface body")


def _parse_interface_fields(body: str) -> list[str]:
    """Top-level field names of an interface body, respecting nesting."""
    fields: list[str] = []
    i = 0
    n = len(body)
    depth = 0
    while i < n:
        ch = body[i]
        nxt = body[i + 1] if i + 1 < n else ""
        # Skip comments
        if depth == 0 and ch == "/" and nxt == "/":
            end = body.find("\n", i)
            i = n if end == -1 else end + 1
            continue
        if depth == 0 and ch == "/" and nxt == "*":
            end = body.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        # Skip strings
        if depth == 0 and ch in ("'", '"', "`"):
            quote = ch
            j = i + 1
            while j < n:
                if body[j] == "\\":
                    j += 2
                    continue
                if body[j] == quote:
                    break
                j += 1
            i = j + 1
            continue
        if depth == 0 and ch not in " \t\n\r;,":
            # Try to match an identifier followed by `?:` or `:`. Anything
            # else (a `[` for index signature, a `readonly` modifier, etc.)
            # we'll either handle or skip safely below.
            m = re.match(r"(?:readonly\s+)?(\w+)\s*\??\s*:", body[i:])
            if m:
                fields.append(m.group(1))
                # Jump past the colon, then continue scanning the value.
                i += m.end()
                continue
            # Index signature `[k: string]:` — skip
            if ch == "[":
                close = body.find("]", i)
                if close != -1:
                    i = close + 1
                    continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return fields


@dataclass
class TSInterface:
    name: str
    file: str
    line: int
    fields: list[str]
    openapi_hint: str | None = None  # explicit `// @openapi Name`


def parse_interfaces(src: str, *, file_path: str) -> list[TSInterface]:
    out: list[TSInterface] = []
    for m in _INTERFACE_RE.finditer(src):
        name = m.group("name")
        lead = m.group("lead") or ""
        hint_match = _OPENAPI_ANNOTATION_RE.search(lead)
        hint = hint_match.group(1) if hint_match else None
        open_brace = m.end() - 1
        try:
            close_brace = _find_matching_brace(src, open_brace)
        except ValueError:
            continue
        body = src[open_brace + 1 : close_brace]
        fields = _parse_interface_fields(body)
        line = src.count("\n", 0, m.start()) + 1
        out.append(
            TSInterface(
                name=name,
                file=file_path,
                line=line,
                fields=fields,
                openapi_hint=hint,
            )
        )
    return out


# ── apiFetch usage detection ──

_API_FETCH_RE = re.compile(
    r"apiFetch\s*<\s*(\w+)\s*>\s*\(\s*[`'\"]?([^`'\")]+)?",
    re.DOTALL,
)


def find_response_types(src: str) -> set[str]:
    """Names of TS types used as the generic type argument of `apiFetch<...>`."""
    names: set[str] = set()
    for m in _API_FETCH_RE.finditer(src):
        names.add(m.group(1))
    return names


# ── Matching TS -> OpenAPI ──


def _candidate_schema_names(ts_name: str) -> list[str]:
    """Heuristic list of OpenAPI schema names to try, in priority order."""
    cands = [ts_name]
    # Result/Response swap (CVUploadResult -> CVUploadResponse)
    if ts_name.endswith("Result"):
        cands.append(ts_name[: -len("Result")] + "Response")
    if ts_name.endswith("Response"):
        cands.append(ts_name[: -len("Response")] + "Result")
    # *List <-> *List (already exact)
    # *Detail <-> *Detail (already exact)
    # *ListResponse -> *List
    if ts_name.endswith("ListResponse"):
        cands.append(ts_name[: -len("Response")])
    # *Row -> *Row (exact)
    return cands


@dataclass
class Drift:
    ts_interface: str
    ts_field: str
    file: str
    line: int
    matched_schema: str

    def to_dict(self) -> dict:
        return {
            "ts_interface": self.ts_interface,
            "ts_field": self.ts_field,
            "matched_schema": self.matched_schema,
            "file": self.file,
            "line": self.line,
        }


@dataclass
class Unmapped:
    ts_interface: str
    file: str
    line: int

    def to_dict(self) -> dict:
        return {"ts_interface": self.ts_interface, "file": self.file, "line": self.line}


# ── Allow-list ──


def _load_allowlist(path: Path) -> dict:
    if not path.exists():
        return {}
    if yaml is None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _is_allowlisted(drift: Drift, allowlist: dict) -> bool:
    """Allow-list shape:
        ignore:
          - interface: CVUploadResult
            field: queued
            reason: 202 branch; OpenAPI 200 schema doesn't include it
    """
    for entry in allowlist.get("ignore") or []:
        if not isinstance(entry, dict):
            continue
        iface = entry.get("interface")
        field_ = entry.get("field")
        if iface is not None and iface != drift.ts_interface:
            continue
        if field_ is not None and field_ != drift.ts_field:
            continue
        return True
    return False


def _unmapped_allowlisted(name: str, allowlist: dict) -> bool:
    for entry in allowlist.get("unmapped_ok") or []:
        if entry == name or (isinstance(entry, dict) and entry.get("interface") == name):
            return True
    return False


# ── Check ──


def check(
    api_ts_path: Path,
    openapi_path: Path,
    allowlist: dict,
) -> tuple[list[Drift], list[Unmapped]]:
    src = api_ts_path.read_text(encoding="utf-8")
    rel = (
        api_ts_path.relative_to(REPO_ROOT).as_posix()
        if api_ts_path.is_absolute() and _is_inside(api_ts_path, REPO_ROOT)
        else api_ts_path.as_posix()
    )
    interfaces = {ti.name: ti for ti in parse_interfaces(src, file_path=rel)}
    response_types = find_response_types(src)
    schemas = load_openapi(openapi_path)

    drifts: list[Drift] = []
    unmapped: list[Unmapped] = []

    for name in sorted(response_types):
        ti = interfaces.get(name)
        if ti is None:
            # apiFetch<X> with no exported interface — likely a primitive
            # or an inline shape. Skip silently.
            continue

        matched_schema: str | None = None
        hints = [ti.openapi_hint] if ti.openapi_hint else []
        for candidate in hints + _candidate_schema_names(name):
            if candidate and candidate in schemas:
                matched_schema = candidate
                break

        if matched_schema is None:
            if not _unmapped_allowlisted(name, allowlist):
                unmapped.append(Unmapped(ts_interface=name, file=ti.file, line=ti.line))
            continue

        api_fields = schemas[matched_schema]
        for ts_field in ti.fields:
            if ts_field in api_fields:
                continue
            d = Drift(
                ts_interface=name,
                ts_field=ts_field,
                file=ti.file,
                line=ti.line,
                matched_schema=matched_schema,
            )
            if _is_allowlisted(d, allowlist):
                continue
            drifts.append(d)
    return drifts, unmapped


def _is_inside(p: Path, root: Path) -> bool:
    try:
        p.relative_to(root)
        return True
    except ValueError:
        return False


def _human_report(drifts: list[Drift], unmapped: list[Unmapped]) -> str:
    if not drifts and not unmapped:
        return "openapi-ts-guard: OK"
    lines: list[str] = []
    if drifts:
        lines.append(f"openapi-ts-guard: {len(drifts)} drift(s) detected")
        for d in drifts:
            lines.append(
                f"  {d.file}:{d.line}  interface {d.ts_interface} "
                f"-> schema {d.matched_schema} is missing field {d.ts_field!r}"
            )
    if unmapped:
        if drifts:
            lines.append("")
        lines.append(f"openapi-ts-guard: {len(unmapped)} unmapped interface(s) (warn-only)")
        for u in unmapped:
            lines.append(f"  {u.file}:{u.line}  {u.ts_interface}")
        lines.append(
            "  (To silence: add `// @openapi SchemaName` above the interface, "
            "or list under `unmapped_ok` in the allow-list.)"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-ts", default=str(DEFAULT_API_TS))
    parser.add_argument("--openapi", default=str(DEFAULT_OPENAPI))
    parser.add_argument("--allowlist", default=str(DEFAULT_ALLOWLIST))
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--fail-on-unmapped",
        action="store_true",
        help="Fail if any apiFetch<Name> type has no OpenAPI counterpart.",
    )
    args = parser.parse_args(argv)

    allowlist = _load_allowlist(Path(args.allowlist))
    drifts, unmapped = check(
        Path(args.api_ts), Path(args.openapi), allowlist
    )

    hard_fail = bool(drifts) or (args.fail_on_unmapped and bool(unmapped))

    if args.json:
        json.dump(
            {
                "ok": not hard_fail,
                "drifts": [d.to_dict() for d in drifts],
                "unmapped": [u.to_dict() for u in unmapped],
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        print(_human_report(drifts, unmapped))

    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
