#!/usr/bin/env python3
"""CI guard: every (table, column) pair referenced by the FastAPI backend
must exist in the live Postgres schema.

Catches PR #23-style drift where backend code reads/writes a column
(cv_generations.word_count) that no migration ever added — PostgREST
returns 42703 and uvicorn's 500 strips CORS, surfacing in the browser
as a misleading "CORS error".

Static analysis: walk every .py file in apps/backend with AST. For each
call whose receiver chain bottoms out at supabase.table("X"), extract
- .select("a, b") column names
- .insert/.upsert/.update({"k": v, ...}) dict keys

Schema source (one of):
- live  : query Supabase via SUPABASE_URL + SUPABASE_SERVICE_KEY
- file  : load a pre-dumped JSON schema (used by tests)
- auto  : live if SUPABASE_URL is set, else fall back to file

Dynamic refs (table name not a string literal, insert payload is a
variable, etc.) are logged as warnings and never fail the build —
they're not static-analyzable and would produce noise.

Static names that are tripping the analyzer in ways the developer
can't or won't refactor are listed in
scripts/ci_schema_guard_allowlist.yml.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - allow running without yaml
    yaml = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
DEFAULT_ALLOWLIST = REPO_ROOT / "scripts" / "ci_schema_guard_allowlist.yml"

# `.select()` PostgREST embeds we strip before treating each item as a column.
# Examples we want to handle:
#   "id, name, related:other_table(id)"  -> id, name
#   "id, *"                              -> id (* skipped)
#   "id, related_table(*)"               -> id  (skip the embed)
#   "count"                              -> count (special, skip)
_WILDCARD_COL = "*"
_SPECIAL_NAMES = {"count"}


@dataclass
class CodeRef:
    """A statically-resolved (table, column) reference in backend code."""

    table: str
    column: str
    file: str
    line: int
    method: str  # select | insert | upsert | update


@dataclass
class DynamicRef:
    """A call where the table or the column set couldn't be resolved at
    parse time (variable arguments). Surfaced as a warning so a human
    can decide whether to refactor or to allowlist."""

    file: str
    line: int
    method: str
    reason: str


@dataclass
class Drift:
    file: str
    line: int
    method: str
    table: str
    column: str
    reason: str  # "column_missing" | "table_missing"

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "method": self.method,
            "table": self.table,
            "column": self.column,
            "reason": self.reason,
        }


# ── AST extraction ──


def _is_supabase_table_call(node: ast.AST) -> tuple[str | None, bool]:
    """If `node` is `supabase.table("X")` or `<x>.table("X")` (any receiver
    we treat as a Supabase client), return ("X", True). If the call is
    `.table(variable)` we return (None, True) to signal "dynamic".
    Otherwise (None, False) — it's not a table call.
    """
    if not isinstance(node, ast.Call):
        return None, False
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "table":
        return None, False
    if not node.args:
        return None, True
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value, True
    return None, True  # dynamic arg


def _trace_to_table(call: ast.Call) -> tuple[str | None, bool]:
    """Walk back through chained Attribute/Call nodes from `call` looking
    for the closest `.table("X")` call in the receiver chain. Returns the
    same shape as `_is_supabase_table_call`.

    Example: for `supabase.table("X").select("a").eq("k", v).execute()`,
    starting from the .execute() Call, walk: .execute -> .eq -> .select ->
    .table("X").
    """
    cur: ast.AST | None = call
    while isinstance(cur, ast.Call):
        # Check this call itself first
        name, is_table = _is_supabase_table_call(cur)
        if is_table:
            return name, True
        # Move to receiver of this call: cur.func is an Attribute, walk
        # to its .value (which might be another Call).
        if isinstance(cur.func, ast.Attribute):
            cur = cur.func.value
        else:
            return None, False
    return None, False


def _split_select_columns(arg_value: str) -> list[str]:
    """Split a PostgREST .select() string into top-level column names,
    stripping embeds and wildcards."""
    cols: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in arg_value:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            cols.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        cols.append("".join(buf).strip())

    out: list[str] = []
    for col in cols:
        if not col:
            continue
        # Drop embed bodies: `related_table(*)` -> drop entirely.
        if "(" in col:
            continue
        # Strip cast first: `col::text` -> col. Must run before the `:`
        # alias strip below, otherwise `name::text` becomes `:text`.
        if "::" in col:
            col = col.split("::", 1)[0].strip()
        # Strip alias / nested-embed prefix: `alias:column` -> column
        elif ":" in col:
            col = col.split(":", 1)[1].strip()
        if col == _WILDCARD_COL:
            continue
        if col in _SPECIAL_NAMES:
            continue
        # Drop dotted refs (`related.col`) — handled by embed branch above
        # but be defensive.
        if "." in col:
            continue
        out.append(col)
    return out


def _extract_dict_keys(node: ast.AST) -> list[str] | None:
    """If `node` is a Dict literal whose keys are all string constants,
    return the keys. Otherwise None (caller treats as dynamic)."""
    if not isinstance(node, ast.Dict):
        return None
    keys: list[str] = []
    for k in node.keys:
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            keys.append(k.value)
        else:
            return None
    return keys


@dataclass
class ExtractionResult:
    refs: list[CodeRef] = field(default_factory=list)
    dynamics: list[DynamicRef] = field(default_factory=list)


def _extract_from_call(
    call: ast.Call, file: str, result: ExtractionResult, *, generated: bool
) -> None:
    """Inspect a single Call node. If it's `.select/.insert/.upsert/.update`
    on a `supabase.table(...)` chain, record refs.
    """
    func = call.func
    if not isinstance(func, ast.Attribute):
        return
    method = func.attr
    if method not in ("select", "insert", "upsert", "update"):
        return

    # Receiver of this method is func.value — should resolve to a
    # `.table("X")` call somewhere up the chain.
    receiver = func.value
    if isinstance(receiver, ast.Call):
        table_name, found = _trace_to_table(receiver)
    else:
        table_name, found = None, False
    if not found:
        return
    if generated:
        return  # generated files: skip both refs and dynamic warnings

    line = call.lineno
    if table_name is None:
        result.dynamics.append(
            DynamicRef(
                file=file,
                line=line,
                method=method,
                reason="table name is a variable, not a string literal",
            )
        )
        return

    if method == "select":
        # First positional arg expected to be a string literal.
        if not call.args:
            # `.select()` no-args is rare; treat as wildcard.
            return
        first = call.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            for col in _split_select_columns(first.value):
                result.refs.append(
                    CodeRef(
                        table=table_name,
                        column=col,
                        file=file,
                        line=line,
                        method=method,
                    )
                )
        else:
            result.dynamics.append(
                DynamicRef(
                    file=file,
                    line=line,
                    method=method,
                    reason=f".select() arg is not a string literal on table {table_name!r}",
                )
            )
        return

    # insert / upsert / update
    if not call.args:
        return
    payload = call.args[0]
    keys = _extract_dict_keys(payload)
    if keys is None:
        result.dynamics.append(
            DynamicRef(
                file=file,
                line=line,
                method=method,
                reason=(
                    f".{method}() payload is not a dict literal on table {table_name!r}"
                ),
            )
        )
        return
    for key in keys:
        result.refs.append(
            CodeRef(
                table=table_name,
                column=key,
                file=file,
                line=line,
                method=method,
            )
        )


_GENERATED_MARKER_RE = re.compile(r"@generated|DO NOT EDIT", re.IGNORECASE)


def _file_is_generated(text: str) -> bool:
    head = text[:1024]
    return bool(_GENERATED_MARKER_RE.search(head))


def extract_refs(backend_root: Path) -> ExtractionResult:
    result = ExtractionResult()
    for path in sorted(backend_root.rglob("*.py")):
        # Skip caches and venvs
        parts = set(path.parts)
        if any(p in parts for p in ("__pycache__", ".venv", "venv", "site-packages")):
            continue
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            # Path is outside the repo (used by tests with tempfile dirs).
            rel = path.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        generated = _file_is_generated(text)
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            # Skip — caller has bigger problems than schema drift on this file.
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                _extract_from_call(node, rel, result, generated=generated)
    return result


# ── Schema source ──


def _load_schema_from_file(path: Path) -> dict[str, set[str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Schema file {path} must be {{table: [columns]}}")
    return {table: set(cols) for table, cols in raw.items()}


def _load_schema_from_supabase() -> dict[str, set[str]]:
    """Query information_schema.columns for the `public` schema."""
    try:
        from supabase import create_client  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "supabase python client not installed; run "
            "`pip install supabase` or pass --schema-file."
        ) from exc

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise SystemExit(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for live schema mode."
        )

    client = create_client(url, key)
    # information_schema is reachable through PostgREST when exposed; the
    # cleanest cross-version path is the `pg_meta` Supabase RPC, but that
    # isn't enabled by default. Use the `execute_sql`-style POST through a
    # one-shot SQL function we ship with the migrations? That'd be too much
    # infrastructure for a CI check. Instead: rely on the fact that
    # PostgREST exposes `pg_catalog` / `information_schema` views when
    # they're added to `db-schemas` — which we DON'T do by default.
    #
    # Pragmatic path: try the `pg_meta` style RPC first; if absent, fall
    # back to reading our own migration files to derive the schema. The
    # migrations are the source of truth for what should be live, so this
    # is a useful fallback for CI without DB access (PRs from forks, etc).
    try:
        rpc = client.rpc("schema_guard_columns", {}).execute()
        rows = rpc.data or []
        out: dict[str, set[str]] = {}
        for row in rows:
            table = row.get("table_name") or row.get("table")
            column = row.get("column_name") or row.get("column")
            if table and column:
                out.setdefault(table, set()).add(column)
        if out:
            return out
    except Exception:
        pass

    # Fallback: derive from migrations. This is the documented escape
    # hatch — see docs/CI_SCHEMA_GUARD.md.
    return load_schema_from_migrations(REPO_ROOT / "infra" / "supabase" / "migrations")


# ── Migrations-derived schema (fallback) ──
# We don't try to be a full SQL parser. We handle CREATE TABLE / ALTER
# TABLE ... ADD COLUMN, which covers every column the live schema has.
# DROP COLUMN is rare in this repo (drift would surface as a column
# referenced in code that no longer exists; this fallback would miss
# that — live mode is preferred and tested).

_CREATE_TABLE_RE = re.compile(
    r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
# Match the entire ALTER TABLE statement so we can find chained
# ADD COLUMN clauses (`ALTER TABLE foo ADD COLUMN a TEXT, ADD COLUMN b INT;`).
_ALTER_TABLE_RE = re.compile(
    r"alter\s+table\s+(?:only\s+)?(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s+(.*?);",
    re.IGNORECASE | re.DOTALL,
)
_ADD_COLUMN_CLAUSE_RE = re.compile(
    r"add\s+column\s+(?:if\s+not\s+exists\s+)?\"?([a-z_][a-z0-9_]*)\"?",
    re.IGNORECASE,
)
_COLUMN_LINE_RE = re.compile(r"^\s*\"?([a-z_][a-z0-9_]*)\"?\s+[A-Za-z]", re.MULTILINE)
_TABLE_CONSTRAINT_PREFIXES = (
    "primary",
    "foreign",
    "unique",
    "check",
    "constraint",
    "references",
)


_SQL_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
_SQL_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_sql_comments(sql: str) -> str:
    sql = _SQL_BLOCK_COMMENT_RE.sub(" ", sql)
    sql = _SQL_LINE_COMMENT_RE.sub("", sql)
    return sql


def _parse_create_table_body(body: str) -> list[str]:
    body = _strip_sql_comments(body)
    # Split top-level commas (depth = 0) on parens.
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))

    cols: list[str] = []
    for part in parts:
        stripped = part.strip().strip(",").strip()
        if not stripped:
            continue
        first = stripped.split()[0].lower().strip('"')
        if first in _TABLE_CONSTRAINT_PREFIXES:
            continue
        # Column line: "name TYPE ..."
        m = re.match(r'\"?([a-z_][a-z0-9_]*)\"?\s+\S', stripped, re.IGNORECASE)
        if m:
            cols.append(m.group(1).lower())
    return cols


def load_schema_from_migrations(migrations_dir: Path) -> dict[str, set[str]]:
    schema: dict[str, set[str]] = {}
    if not migrations_dir.is_dir():
        return schema
    for path in sorted(migrations_dir.glob("*.sql")):
        sql = _strip_sql_comments(path.read_text(encoding="utf-8"))
        for m in _CREATE_TABLE_RE.finditer(sql):
            table = m.group(1).lower()
            cols = _parse_create_table_body(m.group(2))
            schema.setdefault(table, set()).update(cols)
        for m in _ALTER_TABLE_RE.finditer(sql):
            table = m.group(1).lower()
            body = m.group(2)
            for c in _ADD_COLUMN_CLAUSE_RE.finditer(body):
                schema.setdefault(table, set()).add(c.group(1).lower())
    return schema


# ── Allow-list ──


def _load_allowlist(path: Path) -> dict:
    if not path.exists():
        return {}
    if yaml is None:
        # YAML not available: tolerate JSON-style minimal allow-list.
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _is_allowlisted(ref: CodeRef, allowlist: dict) -> bool:
    """Allow-list shape:
        ignore:
          - table: cvs
            column: legacy_field
            reason: kept for migration backfill
          - file: apps/backend/app/services/foo.py
            line: 42
            reason: dynamic table from config
    """
    ignore = allowlist.get("ignore") or []
    for entry in ignore:
        if not isinstance(entry, dict):
            continue
        table = entry.get("table")
        column = entry.get("column")
        file_ = entry.get("file")
        line = entry.get("line")
        method = entry.get("method")
        if table is not None and table != ref.table:
            continue
        if column is not None and column != ref.column:
            continue
        if file_ is not None and file_ != ref.file:
            continue
        if line is not None and line != ref.line:
            continue
        if method is not None and method != ref.method:
            continue
        # All declared filters matched, so this entry applies.
        return True
    return False


# ── Check ──


def check(
    backend_root: Path,
    schema: dict[str, set[str]],
    allowlist: dict,
) -> tuple[list[Drift], list[DynamicRef]]:
    extraction = extract_refs(backend_root)
    drifts: list[Drift] = []
    for ref in extraction.refs:
        if _is_allowlisted(ref, allowlist):
            continue
        if ref.table not in schema:
            drifts.append(
                Drift(
                    file=ref.file,
                    line=ref.line,
                    method=ref.method,
                    table=ref.table,
                    column=ref.column,
                    reason="table_missing",
                )
            )
            continue
        if ref.column not in schema[ref.table]:
            drifts.append(
                Drift(
                    file=ref.file,
                    line=ref.line,
                    method=ref.method,
                    table=ref.table,
                    column=ref.column,
                    reason="column_missing",
                )
            )
    return drifts, extraction.dynamics


def _human_report(
    drifts: list[Drift], dynamics: list[DynamicRef], *, show_dynamics: bool
) -> str:
    if not drifts and (not show_dynamics or not dynamics):
        return "schema-guard: OK (no static drift detected)"
    lines: list[str] = []
    if drifts:
        lines.append(f"schema-guard: {len(drifts)} drift(s) detected")
        for d in drifts:
            lines.append(
                f"  {d.file}:{d.line}  .{d.method}({d.table!r})  "
                f"-> column {d.column!r} {d.reason}"
            )
    else:
        lines.append("schema-guard: no drift")
    if show_dynamics and dynamics:
        lines.append("")
        lines.append(f"schema-guard: {len(dynamics)} dynamic call(s) (warn-only)")
        for w in dynamics:
            lines.append(f"  {w.file}:{w.line}  .{w.method}  {w.reason}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-root",
        default=str(DEFAULT_BACKEND_ROOT),
    )
    parser.add_argument(
        "--allowlist",
        default=str(DEFAULT_ALLOWLIST),
    )
    parser.add_argument(
        "--schema-source",
        choices=["auto", "live", "file", "migrations"],
        default="auto",
        help=(
            "auto: live if SUPABASE_URL is set, otherwise migrations. "
            "live: query Supabase. "
            "file: read --schema-file. "
            "migrations: derive from infra/supabase/migrations."
        ),
    )
    parser.add_argument(
        "--schema-file",
        default=None,
        help="JSON dump of {table: [columns]} — used with --schema-source=file.",
    )
    parser.add_argument(
        "--migrations-dir",
        default=str(REPO_ROOT / "infra" / "supabase" / "migrations"),
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--show-dynamics",
        action="store_true",
        help="Include dynamic (un-resolvable) calls in human output.",
    )
    args = parser.parse_args(argv)

    if args.schema_source == "file":
        if not args.schema_file:
            parser.error("--schema-file required with --schema-source=file")
        schema = _load_schema_from_file(Path(args.schema_file))
    elif args.schema_source == "live":
        schema = _load_schema_from_supabase()
    elif args.schema_source == "migrations":
        schema = load_schema_from_migrations(Path(args.migrations_dir))
    else:  # auto
        if os.environ.get("SUPABASE_URL") and (
            os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
        ):
            schema = _load_schema_from_supabase()
        else:
            schema = load_schema_from_migrations(Path(args.migrations_dir))

    allowlist = _load_allowlist(Path(args.allowlist))
    drifts, dynamics = check(Path(args.backend_root), schema, allowlist)

    if args.json:
        json.dump(
            {
                "ok": not drifts,
                "drifts": [d.to_dict() for d in drifts],
                "dynamics": [
                    {
                        "file": w.file,
                        "line": w.line,
                        "method": w.method,
                        "reason": w.reason,
                    }
                    for w in dynamics
                ],
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        print(_human_report(drifts, dynamics, show_dynamics=args.show_dynamics))

    return 1 if drifts else 0


if __name__ == "__main__":
    sys.exit(main())
