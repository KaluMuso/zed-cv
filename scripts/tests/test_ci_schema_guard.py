"""Schema-guard unit tests.

Covers:
- column drift on .select() is detected
- column drift on .insert() is detected
- missing-table drift is detected
- dynamic table names are not failures (logged as dynamic)
- dynamic insert payloads are not failures (logged as dynamic)
- allow-list suppresses a specific (table, column) pair
- migrations-derived schema reads CREATE TABLE and chained ADD COLUMN
- nested PostgREST embeds in select() don't trip the column splitter
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ci_schema_guard import (
    _is_allowlisted,
    _parse_create_table_body,
    _split_select_columns,
    check,
    extract_refs,
    load_schema_from_migrations,
)


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


# ── Helpers ──


def test_split_select_columns_strips_embeds_and_wildcards():
    cols = _split_select_columns("id, name, related:other(id, label), *, foo(bar)")
    assert cols == ["id", "name"]


def test_split_select_columns_strips_casts_and_aliases():
    cols = _split_select_columns("id, name::text, summary:body")
    assert cols == ["id", "name", "body"]


def test_parse_create_table_body_skips_constraints_and_comments():
    body = """
        id uuid PRIMARY KEY,
        -- a leading comment
        user_id uuid NOT NULL,
        -- another
        amount integer DEFAULT 0,
        PRIMARY KEY (id, user_id),
        CONSTRAINT name_uniq UNIQUE (user_id)
    """
    assert _parse_create_table_body(body) == ["id", "user_id", "amount"]


# ── End-to-end via tempdir ──


SCHEMA = {
    "cvs": {"id", "user_id", "raw_text", "parsed_data"},
    "users": {"id", "phone", "full_name"},
}


def test_clean_code_against_schema(tmp_path):
    _write(
        tmp_path,
        "ok.py",
        """
        def f(supabase):
            supabase.table("cvs").select("id, user_id").execute()
            supabase.table("users").update({"full_name": "x"}).eq("id", 1).execute()
        """,
    )
    drifts, dynamics = check(tmp_path, SCHEMA, {})
    assert drifts == []
    assert dynamics == []


def test_select_drift_detected(tmp_path):
    _write(
        tmp_path,
        "bad.py",
        """
        def f(supabase):
            supabase.table("cvs").select("id, nonexistent_col").execute()
        """,
    )
    drifts, _ = check(tmp_path, SCHEMA, {})
    assert len(drifts) == 1
    d = drifts[0]
    assert (d.table, d.column, d.method, d.reason) == (
        "cvs",
        "nonexistent_col",
        "select",
        "column_missing",
    )


def test_insert_drift_detected(tmp_path):
    _write(
        tmp_path,
        "bad.py",
        """
        def f(supabase):
            supabase.table("cvs").insert({"id": 1, "not_a_column": 2}).execute()
        """,
    )
    drifts, _ = check(tmp_path, SCHEMA, {})
    assert [d.column for d in drifts] == ["not_a_column"]
    assert drifts[0].reason == "column_missing"


def test_missing_table_detected(tmp_path):
    _write(
        tmp_path,
        "bad.py",
        """
        def f(supabase):
            supabase.table("ghost_table").select("id").execute()
        """,
    )
    drifts, _ = check(tmp_path, SCHEMA, {})
    assert [d.reason for d in drifts] == ["table_missing"]


def test_dynamic_table_name_is_warn_only(tmp_path):
    _write(
        tmp_path,
        "dyn.py",
        """
        def f(supabase, table_name):
            supabase.table(table_name).select("id").execute()
        """,
    )
    drifts, dynamics = check(tmp_path, SCHEMA, {})
    assert drifts == []
    assert len(dynamics) == 1
    assert "variable" in dynamics[0].reason


def test_dynamic_insert_payload_is_warn_only(tmp_path):
    _write(
        tmp_path,
        "dyn.py",
        """
        def f(supabase, payload):
            supabase.table("cvs").insert(payload).execute()
        """,
    )
    drifts, dynamics = check(tmp_path, SCHEMA, {})
    assert drifts == []
    assert len(dynamics) == 1
    assert "dict literal" in dynamics[0].reason


def test_chained_call_with_eq_and_execute(tmp_path):
    # Mimics the real backend pattern: .select(...).eq(...).limit(1).execute()
    _write(
        tmp_path,
        "chain.py",
        """
        def f(supabase):
            (
                supabase.table("cvs")
                .select("id, raw_text")
                .eq("user_id", "x")
                .limit(1)
                .execute()
            )
        """,
    )
    drifts, dynamics = check(tmp_path, SCHEMA, {})
    assert drifts == []
    assert dynamics == []


def test_allowlist_suppresses_specific_drift(tmp_path):
    _write(
        tmp_path,
        "bad.py",
        """
        def f(supabase):
            supabase.table("cvs").select("id, legacy_col").execute()
        """,
    )
    allowlist = {
        "ignore": [{"table": "cvs", "column": "legacy_col", "reason": "test"}]
    }
    drifts, _ = check(tmp_path, SCHEMA, allowlist)
    assert drifts == []


def test_generated_files_are_skipped(tmp_path):
    _write(
        tmp_path,
        "gen.py",
        """
        # @generated by codegen; DO NOT EDIT
        def f(supabase):
            supabase.table("cvs").select("nonexistent_col").execute()
        """,
    )
    drifts, _ = check(tmp_path, SCHEMA, {})
    assert drifts == []


# ── Migrations-derived schema ──


def test_load_schema_from_migrations_handles_create_and_alter(tmp_path):
    mig = tmp_path / "migrations"
    mig.mkdir()
    _write(
        mig,
        "001_init.sql",
        """
        CREATE TABLE IF NOT EXISTS users (
            id uuid PRIMARY KEY,
            -- leading comment
            phone varchar(15) NOT NULL,
            full_name varchar(255)
        );

        CREATE TABLE jobs (
            id uuid PRIMARY KEY,
            title text NOT NULL
        );
        """,
    )
    _write(
        mig,
        "002_richer_jobs.sql",
        """
        ALTER TABLE public.jobs
            ADD COLUMN IF NOT EXISTS employment_type text,
            ADD COLUMN IF NOT EXISTS work_arrangement text,
            ADD COLUMN IF NOT EXISTS hybrid_days_per_week integer;
        """,
    )
    schema = load_schema_from_migrations(mig)
    assert schema["users"] == {"id", "phone", "full_name"}
    assert schema["jobs"] == {
        "id",
        "title",
        "employment_type",
        "work_arrangement",
        "hybrid_days_per_week",
    }


def test_is_allowlisted_requires_all_declared_fields_to_match():
    from ci_schema_guard import CodeRef

    ref = CodeRef(
        table="cvs", column="x", file="a.py", line=10, method="select"
    )
    assert _is_allowlisted(ref, {"ignore": [{"table": "cvs", "column": "x"}]})
    # Wrong file: filter doesn't match
    assert not _is_allowlisted(
        ref, {"ignore": [{"table": "cvs", "column": "x", "file": "other.py"}]}
    )
