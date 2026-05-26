"""Referral code resolution, signup attribution, and CV qualify rewards."""
from unittest.mock import MagicMock

import pytest

from app.services.referral import (
    REFERRAL_QUALIFY_BONUS_MATCHES,
    attach_referral_on_signup,
    count_referral_qualified,
    generate_referral_code,
    qualify_referral_on_cv_upload,
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

    def in_(self, col, vals):
        self._filters.append(("in", col, vals))
        return self

    def limit(self, n):
        return self

    def insert(self, data):
        self._insert_payload = data
        return self

    def update(self, data):
        self._update_payload = data
        return self

    def _apply_filters(self, rows: list) -> list:
        filtered = rows
        for op, col, val in self._filters:
            if op == "eq":
                filtered = [r for r in filtered if r.get(col) == val]
            elif op == "in":
                filtered = [r for r in filtered if r.get(col) in val]
        return filtered

    def execute(self):
        result = MagicMock()
        rows = self._tables.get(self._table, [])
        filtered = self._apply_filters(rows)

        if self._update_payload:
            for row in filtered:
                row.update(self._update_payload)

        if self._insert_payload:
            row = dict(self._insert_payload)
            if self._table == "referral_events":
                row.setdefault("id", f"evt-{len(rows) + 1}")
            elif self._table == "users":
                row.setdefault("id", "new-user")
            self._tables.setdefault(self._table, []).append(row)
            filtered = [row]

        result.data = filtered[:1] if self._update_payload is None else filtered[:1]
        if not result.data and filtered:
            result.data = filtered[:1]
        count_filters = [
            f for f in self._filters
            if f[0] in ("eq", "in")
        ]
        if count_filters and self._table in ("users", "referral_events"):
            counted = rows
            for op, col, val in count_filters:
                if op == "eq":
                    counted = [r for r in counted if r.get(col) == val]
                elif op == "in":
                    counted = [r for r in counted if r.get(col) in val]
            result.count = len(counted)
        else:
            result.count = None
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


REFERRED_ID = "c3333333-3333-4333-8333-333333333333"
EVENT_ID = "e4444444-4444-4444-8444-444444444444"


@pytest.fixture
def qualify_tables(supabase_tables):
    supabase_tables["referral_events"] = [
        {
            "id": EVENT_ID,
            "referrer_user_id": REFERRER_ID,
            "referred_user_id": REFERRED_ID,
            "status": "signed_up",
        },
    ]
    supabase_tables["subscriptions"] = [
        {
            "id": "sub-1",
            "user_id": REFERRER_ID,
            "matches_limit": 10,
            "matches_used": 2,
        },
    ]
    return supabase_tables


def test_qualify_referral_on_cv_upload_grants_bonus(qualify_tables):
    sb = TableQuery(qualify_tables)
    assert qualify_referral_on_cv_upload(REFERRED_ID, sb) is True
    event = qualify_tables["referral_events"][0]
    assert event["status"] == "rewarded"
    assert event.get("qualified_at")
    assert event.get("rewarded_at")
    sub = qualify_tables["subscriptions"][0]
    assert sub["matches_limit"] == 10 + REFERRAL_QUALIFY_BONUS_MATCHES


def test_qualify_referral_no_event_returns_false(supabase_tables):
    sb = TableQuery(supabase_tables)
    assert qualify_referral_on_cv_upload(REFERRED_ID, sb) is False


def test_qualify_referral_already_rewarded_skipped(qualify_tables):
    qualify_tables["referral_events"][0]["status"] = "rewarded"
    sb = TableQuery(qualify_tables)
    assert qualify_referral_on_cv_upload(REFERRED_ID, sb) is False


def test_count_referral_qualified(qualify_tables):
    qualify_tables["referral_events"][0]["status"] = "rewarded"
    sb = TableQuery(qualify_tables)
    assert count_referral_qualified(REFERRER_ID, sb) == 1
