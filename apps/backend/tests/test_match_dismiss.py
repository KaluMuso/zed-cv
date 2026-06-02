"""POST /matches/{match_id}/dismiss — soft-hide from user feed."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

MATCH_ID = "00000000-0000-4000-8000-000000000099"
MISSING_ID = "00000000-0000-4000-8000-000000000098"


class _Chain:
    def __init__(self, execute_result):
        self._execute_result = execute_result

    def select(self, *_, **__):
        return self

    def eq(self, *_, **__):
        return self

    def limit(self, *_, **__):
        return self

    def update(self, *_, **__):
        return self

    def execute(self):
        return self._execute_result


def test_dismiss_match_sets_status(client, auth_headers):
    from app.core.deps import get_supabase
    from main import app

    table = MagicMock()
    table.select.return_value = _Chain(
        SimpleNamespace(data=[{"id": MATCH_ID, "status": "new"}])
    )
    table.update.return_value = _Chain(
        SimpleNamespace(data=[{"id": MATCH_ID, "status": "dismissed"}])
    )
    supabase = MagicMock()
    supabase.table.return_value = table

    app.dependency_overrides[get_supabase] = lambda: supabase
    try:
        res = client.post(
            f"/api/v1/matches/{MATCH_ID}/dismiss",
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_supabase, None)

    assert res.status_code == 200
    body = res.json()
    assert body["match_id"] == MATCH_ID
    assert body["status"] == "dismissed"
    table.update.assert_called_once()
    update_payload = table.update.call_args[0][0]
    assert update_payload["status"] == "dismissed"
    assert "dismissed_at" in update_payload


def test_dismiss_match_not_found(client, auth_headers):
    from app.core.deps import get_supabase
    from main import app

    table = MagicMock()
    table.select.return_value = _Chain(SimpleNamespace(data=[]))
    supabase = MagicMock()
    supabase.table.return_value = table

    app.dependency_overrides[get_supabase] = lambda: supabase
    try:
        res = client.post(
            f"/api/v1/matches/{MISSING_ID}/dismiss",
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_supabase, None)

    assert res.status_code == 404
