"""Tests for POST/GET /users/me/consent (consent_log audit trail)."""
from datetime import datetime, timedelta, timezone
import os
from unittest.mock import MagicMock

import pytest
from jose import jwt


@pytest.fixture
def consent_log_table(fake_supabase):
    """Track consent_log inserts in the fake Supabase client."""
    fake_supabase._consent_rows = []

    def table(name):
        if name != "consent_log":
            return fake_supabase._orig_table(name)

        mock = MagicMock()

        def insert(data):
            row = dict(data)
            row.setdefault("id", f"consent-{len(fake_supabase._consent_rows)}")
            fake_supabase._consent_rows.append(row)
            result = MagicMock()
            result.data = [row]
            return result

        def select(*_a, **_kw):
            q = MagicMock()

            def eq(col, val):
                if col == "user_id":
                    q._user_id = val
                return q

            def order(*_a, **_kw):
                return q

            def execute():
                rows = [
                    r
                    for r in fake_supabase._consent_rows
                    if r.get("user_id") == getattr(q, "_user_id", None)
                ]
                result = MagicMock()
                result.data = sorted(
                    rows,
                    key=lambda r: r.get("granted_at") or "",
                    reverse=True,
                )
                return result

            q.eq = eq
            q.order = order
            q.execute = execute
            return q

        mock.insert = insert
        mock.select = select
        return mock

    if not hasattr(fake_supabase, "_orig_table"):
        fake_supabase._orig_table = fake_supabase.table
    fake_supabase.table = table
    return fake_supabase


def _headers_for_user(user_id: str) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": user_id,
            "phone": "+260971234567",
            "exp": now + timedelta(hours=24),
            "iat": now,
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_record_consent_inserts_with_user_id(client, fake_supabase, consent_log_table):
    user_id = "user-consent-001"
    headers = _headers_for_user(user_id)

    resp = client.post(
        "/api/v1/users/me/consent",
        headers=headers,
        json={"consent_type": "marketing_whatsapp", "granted": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["consent"]["consent_type"] == "marketing_whatsapp"
    assert body["consent"]["granted"] is False

    assert len(fake_supabase._consent_rows) == 1
    row = fake_supabase._consent_rows[0]
    assert row["user_id"] == user_id
    assert row["consent_type"] == "marketing_whatsapp"
    assert row["granted"] is False


def test_get_consent_status_returns_latest(client, fake_supabase, consent_log_table):
    user_id = "user-consent-002"
    headers = _headers_for_user(user_id)

    client.post(
        "/api/v1/users/me/consent",
        headers=headers,
        json={"consent_type": "marketing_whatsapp", "granted": True},
    )
    client.post(
        "/api/v1/users/me/consent",
        headers=headers,
        json={"consent_type": "marketing_whatsapp", "granted": False},
    )

    resp = client.get("/api/v1/users/me/consent", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["consents"]["marketing_whatsapp"] is False
    assert "marketing_whatsapp" in data["last_updated"]
