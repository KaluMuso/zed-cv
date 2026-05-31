"""Tests for Lenco widget reference parsing and payment lookup."""
from __future__ import annotations

import uuid

from tests.conftest import FakeSupabaseQuery
from app.services.lenco_payment_ref import (
    find_lenco_payment_row,
    is_uuid_string,
    parse_consumer_widget_reference,
)


def test_is_uuid_string_accepts_valid_uuid():
    u = str(uuid.uuid4())
    assert is_uuid_string(u) is True


def test_is_uuid_string_rejects_widget_reference():
    u = str(uuid.uuid4())
    ref = f"zedapply-{u}-1717000000000"
    assert is_uuid_string(ref) is False


def test_parse_consumer_widget_reference():
    u = str(uuid.uuid4())
    ref = f"zedapply-{u}-1717000000000"
    parsed = parse_consumer_widget_reference(ref)
    assert parsed == (u, 1717000000000)


def test_parse_consumer_widget_reference_rejects_employer():
    u = str(uuid.uuid4())
    ref = f"zedapply-emp-{u}-1717000000000"
    assert parse_consumer_widget_reference(ref) is None


def test_parse_consumer_widget_reference_rejects_malformed_uuid_segment():
    ref = "zedapply-not-a-uuid-1717000000000"
    assert parse_consumer_widget_reference(ref) is None


def test_is_uuid_string_rejects_widget_reference_even_with_valid_uuid_inside():
    u = str(uuid.uuid4())
    ref = f"zedapply-{u}-1717000000000"
    assert is_uuid_string(ref) is False


def test_find_lenco_payment_row_does_not_use_widget_ref_as_payment_id(fake_supabase):
    """Regression: widget refs must not hit payments.id (Postgres uuid cast error)."""
    user_id = str(uuid.uuid4())
    company_ref = f"zedapply-{user_id}-1717000000000"
    fake_supabase.set_table("payments", FakeSupabaseQuery(data=[]))

    row = find_lenco_payment_row(
        fake_supabase,
        company_ref=company_ref,
        lenco_ref=None,
    )
    assert row is None


def test_find_lenco_payment_row_matches_by_provider_ref(fake_supabase):
    user_id = str(uuid.uuid4())
    company_ref = f"zedapply-{user_id}-1717000000000"
    fake_supabase.set_table(
        "payments",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "pay-by-ref",
                    "user_id": user_id,
                    "provider_ref": company_ref,
                    "subscriptions": {"id": "sub-1"},
                }
            ]
        ),
    )
    row = find_lenco_payment_row(
        fake_supabase,
        company_ref=company_ref,
        lenco_ref=None,
    )
    assert row is not None
    assert row["id"] == "pay-by-ref"


def test_find_lenco_payment_row_legacy_payment_uuid(fake_supabase):
    payment_id = str(uuid.uuid4())
    fake_supabase.set_table(
        "payments",
        FakeSupabaseQuery(
            data=[
                {
                    "id": payment_id,
                    "user_id": "user-legacy",
                    "provider_ref": "dpo-token",
                    "subscriptions": {},
                }
            ]
        ),
    )
    row = find_lenco_payment_row(
        fake_supabase,
        company_ref=payment_id,
        lenco_ref=None,
    )
    assert row is not None
    assert row["id"] == payment_id
