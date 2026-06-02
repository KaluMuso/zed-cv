"""POST /admin/users/{id}/repair-delivery-quota."""
from unittest.mock import AsyncMock, patch

from tests.conftest import FakeSupabaseQuery


def _superadmin_users():
    return FakeSupabaseQuery(
        data=[{"id": "admin-user-id", "phone": "+260971111111", "role": "superadmin"}]
    )


def test_repair_delivery_quota_endpoint(client, admin_headers, fake_supabase):
    fake_supabase.set_table("users", _superadmin_users())
    with patch(
        "app.api.v1.admin.repair_user_match_delivery",
        new_callable=AsyncMock,
        return_value={
            "user_id": "target-user-id",
            "tier": "free",
            "matches_limit": 7,
            "credited_before": 51,
            "credited_after": 7,
            "credits_reset_this_month": 51,
            "newly_credited_job_ids": ["j1", "j2"],
            "welcome_bonus_updated": True,
        },
    ) as mock_repair:
        res = client.post(
            "/api/v1/admin/users/target-user-id/repair-delivery-quota",
            headers=admin_headers,
            json={"reset_month_credits": True, "apply_welcome": True},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["credited_after"] == 7
    assert body["welcome_bonus_updated"] is True
    mock_repair.assert_called_once()
