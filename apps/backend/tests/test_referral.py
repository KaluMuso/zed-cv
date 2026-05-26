"""Referral code resolution and signup attribution."""
from unittest.mock import MagicMock

import pytest

from app.services.referral import (
    attach_referral_on_signup,
    generate_referral_code,
    resolve_referrer_user_id,
)


class TableQuery:
    def __init__(self, tables: dict):
        self._tables = tables
        self._table = ""
        self._filters: list[tuple[str, str, object]] = []
        self._insert_payload = None
        self._update_payload = None

    def table(self, name: str):
        self._table = name
        self._filters = []
        self._insert_payload = None
        self._update_payload = None
        return self

    def select(self, *a, **kw):
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def limit(self, n):
        return self

    def insert(self, data):
        self._insert_payload = data
        if self._table == "referral_events":
            self._tables.setdefault("referral_events", []).append(data)
        return self

    def update(self, data):
        self._update_payload = data
        return self

    def execute(self):
        result = MagicMock()
        rows = self._tables.get(self._table, [])
        filtered = rows
        for op, col, val in self._filters:
            if op == "eq":
                filtered = [r for r in filtered if r.get(col) == val]
        if self._insert_payload and self._table == "users":
            row = dict(self._insert_payload)
            row.setdefault("id", "new-user")
            self._tables.setdefault("users", []).append(row)
        result.data = filtered[:1] if filtered else []
        result.count = len([r for r in rows if all(
            r.get(c) == v for _, c, v in self._filters if _ == "eq"
        )]) if self._table == "users" and any(f[1] == "referred_by_user_id" for f in self._filters) else None
        return result


REFERRER_ID = "a1111111-1111-4111-8111-111111111111"


@pytest.fixture
def supabase_tables():
    return {
        "users": [
            {
                "id": REFERRER_ID,
                "referral_code": "AB12CD34",
                "phone": "+260971111111",
            },
        ],
        "referral_events": [],
    }


def test_resolve_referrer_by_code(supabase_tables):
    sb = TableQuery(supabase_tables)
    assert resolve_referrer_user_id("ab12cd34", sb) == REFERRER_ID


def test_resolve_referrer_by_user_id(supabase_tables):
    sb = TableQuery(supabase_tables)
    assert resolve_referrer_user_id(REFERRER_ID, sb) == REFERRER_ID


def test_resolve_unknown_ref_returns_none(supabase_tables):
    sb = TableQuery(supabase_tables)
    assert resolve_referrer_user_id("ZZZZZZZZ", sb) is None


def test_generate_referral_code_unique(supabase_tables):
    sb = TableQuery(supabase_tables)
    code = generate_referral_code(sb)
    assert len(code) == 8
    assert code.isalnum()


def test_attach_referral_on_signup(supabase_tables):
    sb = TableQuery(supabase_tables)
    new_id = "b2222222-2222-4222-8222-222222222222"
    supabase_tables["users"].append({"id": new_id, "referral_code": "NEWUSER1"})
    referrer = attach_referral_on_signup(new_id, "AB12CD34", sb)
    assert referrer == REFERRER_ID
    assert len(supabase_tables["referral_events"]) == 1
    assert supabase_tables["referral_events"][0]["referrer_user_id"] == REFERRER_ID


def test_attach_self_referral_ignored(supabase_tables):
    sb = TableQuery(supabase_tables)
    assert attach_referral_on_signup(REFERRER_ID, REFERRER_ID, sb) is None
    assert len(supabase_tables["referral_events"]) == 0
