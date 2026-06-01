"""Migration 091 — cv_generations RLS scoped to auth.uid() (not USING true)."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

MIGRATION_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "infra"
    / "supabase"
    / "migrations"
    / "091_cv_generations_rls_scope.sql"
)


def _sql() -> str:
    return MIGRATION_PATH.read_text()


def _normalize_sql_fragment(text: str) -> str:
    return "".join(text.lower().split())


def _policy_blocks(sql: str) -> list[str]:
    pattern = re.compile(
        r"CREATE POLICY (\w+) ON public\.cv_generations\s*(.*?);",
        re.DOTALL | re.IGNORECASE,
    )
    return [body.strip() for _name, body in pattern.findall(sql)]


def _row_visible_to_auth_user(row_user_id: uuid.UUID | None, auth_uid: uuid.UUID) -> bool:
    return row_user_id is not None and row_user_id == auth_uid


@pytest.fixture
def two_users() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


def test_migration_091_exists():
    assert MIGRATION_PATH.exists(), f"Migration 091 missing at {MIGRATION_PATH}"


def test_migration_091_drops_permissive_cv_gen_all():
    sql = _sql()
    assert "DROP POLICY IF EXISTS cv_gen_all ON public.cv_generations" in sql


def test_migration_091_drops_legacy_cv_generations_self():
    sql = _sql()
    assert "DROP POLICY IF EXISTS cv_generations_self ON public.cv_generations" in sql


def test_migration_091_select_policy_scoped_to_auth_uid():
    sql = _sql()
    blocks = _policy_blocks(sql)
    select_blocks = [b for b in blocks if "FOR SELECT" in b.upper()]
    assert select_blocks, "cv_generations must have a SELECT policy"
    combined = " ".join(select_blocks)
    assert "to authenticated" in combined.lower()
    assert "user_id=auth.uid()" in _normalize_sql_fragment(combined)
    assert "using(true)" not in _normalize_sql_fragment(combined)


def test_migration_091_insert_deny_for_authenticated():
    sql = _sql()
    blocks = _policy_blocks(sql)
    insert_blocks = [b for b in blocks if "FOR INSERT" in b.upper()]
    assert insert_blocks, "cv_generations must deny authenticated INSERT"
    combined = " ".join(insert_blocks)
    assert "to authenticated" in combined.lower()
    assert "withcheck(false)" in _normalize_sql_fragment(combined)


def test_migration_091_no_for_all_policy():
    for body in _policy_blocks(_sql()):
        assert "FOR ALL" not in body.upper()


def test_cross_user_isolation_user_a_cannot_read_user_b_cv_generation(
    two_users: tuple[uuid.UUID, uuid.UUID],
):
    user_a, user_b = two_users
    assert not _row_visible_to_auth_user(user_b, user_a)


def test_cross_user_isolation_user_reads_own_cv_generation(
    two_users: tuple[uuid.UUID, uuid.UUID],
):
    user_a, _user_b = two_users
    assert _row_visible_to_auth_user(user_a, user_a)
