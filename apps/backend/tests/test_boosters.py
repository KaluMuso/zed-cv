import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import FakeSupabaseQuery

class _InsertSpyQuery(FakeSupabaseQuery):
    def __init__(self, data=None):
        super().__init__(data=data)
        self.inserted = []
        self.updated = []

    def insert(self, data):
        row = dict(data) if isinstance(data, dict) else data
        if "id" not in row:
            row["id"] = "test-id"
        self.inserted.append(row)
        self._data = [row]
        return self

    def update(self, data):
        self.updated.append(data)
        return self

@pytest.mark.asyncio
async def test_booster_purchase_creates_pending_entitlement(client, auth_headers, fake_supabase):
    fake_supabase.set_table("booster_skus", FakeSupabaseQuery(data=[{"sku": "test_sku", "price_ngwee": 5000}]))
    
    payments_spy = _InsertSpyQuery()
    fake_supabase.set_table("payments", payments_spy)
    
    entitlements_spy = _InsertSpyQuery()
    fake_supabase.set_table("user_entitlements", entitlements_spy)

    res = client.post("/api/v1/boosters/purchase", json={"sku": "test_sku", "phone": "0971234567"}, headers=auth_headers)
    assert res.status_code == 200
    
    assert len(payments_spy.inserted) == 1
    assert payments_spy.inserted[0]["status"] == "pending"
    assert payments_spy.inserted[0]["webhook_data"] == {"intended_sku": "test_sku"}
    
    assert len(entitlements_spy.inserted) == 1
    assert entitlements_spy.inserted[0]["status"] == "pending"
    assert entitlements_spy.inserted[0]["booster_sku"] == "test_sku"

@pytest.mark.asyncio
async def test_booster_webhook_activates_entitlement_to_paid(client, fake_supabase):
    fake_supabase.set_table("payments", FakeSupabaseQuery(data=[{
        "id": "pay-123", 
        "status": "pending", 
        "user_id": "test-user-id",
        "provider_ref": "test-ref",
        "amount": 5000,
        "webhook_data": {"intended_sku": "test_sku"}
    }]))
    
    entitlements_spy = _InsertSpyQuery(data=[{
        "id": "ent-123", "payment_id": "pay-123", "status": "pending"
    }])
    fake_supabase.set_table("user_entitlements", entitlements_spy)

    with patch("app.core.config.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.lenco_verify_signatures = False
        mock_get_settings.return_value = mock_settings
        res = client.post(
            "/api/v1/webhooks/lenco", 
            json={
                "event": "collection.successful",
                "data": {
                    "reference": "test-ref",
                    "amount": 50.00,
                    "status": "successful"
                }
            },
            headers={"x-lenco-signature": "dummy"}
        )
        assert res.status_code == 200

    assert len(entitlements_spy.updated) > 0
    assert any(u.get("status") == "paid" for u in entitlements_spy.updated)

@pytest.mark.asyncio
async def test_booster_consume_updates_status_to_consumed(client, auth_headers, fake_supabase):
    entitlements_spy = _InsertSpyQuery(data=[{
        "id": "ent-123", "user_id": "test-user-id", "status": "paid"
    }])
    fake_supabase.set_table("user_entitlements", entitlements_spy)
    
    res = client.post("/api/v1/boosters/ent-123/consume", json={"job_id": "job-123"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["message"] == "Booster consumed successfully"
    assert len(entitlements_spy.updated) > 0
    assert entitlements_spy.updated[0]["status"] == "consumed"
    assert "consumed_at" in entitlements_spy.updated[0]

@pytest.mark.asyncio
async def test_booster_consume_rejects_pending_or_consumed_entitlements(client, auth_headers, fake_supabase):
    fake_supabase.set_table("user_entitlements", FakeSupabaseQuery(data=[]))
    res = client.post("/api/v1/boosters/ent-123/consume", json={"job_id": "job-123"}, headers=auth_headers)
    assert res.status_code == 400
    assert "Booster not found or already consumed/pending" in res.json()["detail"]

@pytest.mark.asyncio
async def test_booster_purchase_requires_valid_sku(client, auth_headers, fake_supabase):
    fake_supabase.set_table("booster_skus", FakeSupabaseQuery(data=[]))
    res = client.post("/api/v1/boosters/purchase", json={"sku": "invalid_sku", "phone": "0971234567"}, headers=auth_headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "SKU not found"
