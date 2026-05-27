"""Pin the tier gate on POST /matches/{match_id}/tailor-cv."""
from datetime import date, timedelta

import pytest


def _make_user_row(
    user_id: str = "test-user-id",
    role: str = "user",
    tier: str = "free",
) -> dict:
    reset = (date.today() + timedelta(days=28)).isoformat()
    return {
        "id": user_id,
        "phone": "+260971234567",
        "role": role,
        "subscription_tier": tier,
        "matches_viewed_this_month": 0,
        "billing_cycle_reset": reset,
    }


def _make_sub_row(tier: str) -> dict:
    return {"user_id": "test-user-id", "tier": tier, "status": "active"}


class _FakeQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *_, **__):
        return self

    def eq(self, *_, **__):
        return self

    def limit(self, *_, **__):
        return self

    def execute(self):
        from types import SimpleNamespace
        return SimpleNamespace(data=self._data)


class _FakeSupabase:
    def __init__(self, user_role: str = "user", tier: str | None = None):
        canonical = tier or "free"
        self._user = _make_user_row(role=user_role, tier=canonical)
        self._sub = _make_sub_row(canonical) if tier else None

    def table(self, name: str):
        if name == "users":
            return _FakeQuery([self._user])
        if name == "subscriptions":
            return _FakeQuery([self._sub] if self._sub else [])
        return _FakeQuery([])


@pytest.mark.parametrize("tier", ["free", "starter"])
def test_below_professional_tier_is_rejected(client, auth_headers, tier):
    from app.core.deps import get_supabase
    from main import app

    app.dependency_overrides[get_supabase] = lambda: _FakeSupabase(tier=tier)
    try:
        resp = client.post(
            "/api/v1/matches/00000000-0000-4000-8000-000000000001/tailor-cv",
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_supabase, None)

    assert resp.status_code == 403
    assert "professional" in resp.json().get("detail", "").lower()


def test_professional_tier_passes_gate(client, auth_headers):
    from app.core.deps import get_supabase
    from main import app

    app.dependency_overrides[get_supabase] = lambda: _FakeSupabase(tier="professional")
    try:
        resp = client.post(
            "/api/v1/matches/00000000-0000-4000-8000-000000000001/tailor-cv",
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_supabase, None)

    assert resp.status_code != 403 or "professional" not in resp.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_generated_match_tailored_cv_rejects_short_content():
    from app.services.cv_generator import GeneratedMatchTailoredCV
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GeneratedMatchTailoredCV(content="too short", word_count=2)
