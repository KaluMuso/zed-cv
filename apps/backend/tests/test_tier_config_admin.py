"""Admin tier_config and public /tiers catalog."""
from tests.conftest import FakeSupabaseQuery


def _superadmin_users():
    return FakeSupabaseQuery(
        data=[{"id": "admin-user-id", "phone": "+260971111111", "role": "superadmin"}]
    )


def _tier_config_rows():
    return [
        {
            "tier": "free",
            "display_name": "Free",
            "price_ngwee": 0,
            "matches_limit": 10,
            "sort_order": 0,
            "updated_at": None,
        },
        {
            "tier": "starter",
            "display_name": "Starter",
            "price_ngwee": 12500,
            "matches_limit": 50,
            "sort_order": 1,
            "updated_at": None,
        },
        {
            "tier": "professional",
            "display_name": "Professional",
            "price_ngwee": 25000,
            "matches_limit": 125,
            "sort_order": 2,
            "updated_at": None,
        },
        {
            "tier": "super_standard",
            "display_name": "Super Standard",
            "price_ngwee": 50000,
            "matches_limit": 99999,
            "sort_order": 3,
            "updated_at": None,
        },
    ]


class _TierConfigQuery(FakeSupabaseQuery):
    def __init__(self, data=None):
        initial = data or _tier_config_rows()
        super().__init__(data=initial)
        self.upserted: list[dict] = []
        self._by_tier = {row["tier"]: dict(row) for row in initial}

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def upsert(self, data, **kwargs):
        if isinstance(data, dict):
            self.upserted.append(data)
            self._by_tier[data["tier"]] = dict(data)
            self._data = list(self._by_tier.values())
        return self


class TestPublicTiers:
    def test_list_tiers_no_auth(self, client, fake_supabase):
        fake_supabase.set_table("tier_config", _TierConfigQuery())
        resp = client.get("/api/v1/tiers")
        assert resp.status_code == 200
        tiers = {t["tier"]: t for t in resp.json()["tiers"]}
        assert tiers["starter"]["price_ngwee"] == 12500
        assert tiers["starter"]["matches_limit"] == 50


class TestAdminTierConfig:
    def test_get_requires_superadmin(self, client, auth_headers, fake_supabase):
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(data=[{"id": "test-user-id", "role": "user"}]),
        )
        resp = client.get("/api/v1/admin/tier-config", headers=auth_headers)
        assert resp.status_code == 403

    def test_get_superadmin(self, client, admin_headers, fake_supabase):
        fake_supabase.set_table("users", _superadmin_users())
        fake_supabase.set_table("tier_config", _TierConfigQuery())
        resp = client.get("/api/v1/admin/tier-config", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()["tiers"]) == 4

    def test_update_starter_price(self, client, admin_headers, fake_supabase):
        from app.services import tier_config as tier_config_svc

        tier_config_svc.clear_tier_config_cache()
        fake_supabase.set_table("users", _superadmin_users())
        spy = _TierConfigQuery()
        fake_supabase.set_table("tier_config", spy)

        payload = {
            "tiers": [
                {
                    "tier": "free",
                    "display_name": "Free",
                    "price_ngwee": 0,
                    "matches_limit": 10,
                },
                {
                    "tier": "starter",
                    "display_name": "Starter",
                    "price_ngwee": 13000,
                    "matches_limit": 55,
                },
                {
                    "tier": "professional",
                    "display_name": "Professional",
                    "price_ngwee": 25000,
                    "matches_limit": 125,
                },
                {
                    "tier": "super_standard",
                    "display_name": "Super Standard",
                    "price_ngwee": 50000,
                    "matches_limit": 99999,
                },
            ]
        }
        resp = client.put(
            "/api/v1/admin/tier-config",
            headers=admin_headers,
            json=payload,
        )
        assert resp.status_code == 200
        starter = next(t for t in resp.json()["tiers"] if t["tier"] == "starter")
        assert starter["price_ngwee"] == 13000
        assert starter["matches_limit"] == 55
        assert any(
            u.get("tier") == "starter" and u.get("price_ngwee") == 13000
            for u in spy.upserted
        )


class TestAdminTiersRoutes:
    def test_list_requires_auth(self, client, fake_supabase):
        fake_supabase.set_table("tier_config", _TierConfigQuery())
        resp = client.get("/api/v1/admin/tiers")
        assert resp.status_code == 401

    def test_list_with_admin_api_key(self, client, fake_supabase):
        fake_supabase.set_table("tier_config", _TierConfigQuery())
        resp = client.get(
            "/api/v1/admin/tiers",
            headers={"X-INGEST-API-KEY": "test-ingest-key"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["tiers"]) == 4

    def test_patch_starter_with_superadmin(self, client, admin_headers, fake_supabase):
        from app.services import tier_config as tier_config_svc

        tier_config_svc.clear_tier_config_cache()
        fake_supabase.set_table("users", _superadmin_users())
        spy = _TierConfigQuery()
        fake_supabase.set_table("tier_config", spy)

        resp = client.patch(
            "/api/v1/admin/tiers/starter",
            headers=admin_headers,
            json={"price_ngwee": 14000, "matches_limit": 60},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["tier"] == "starter"
        assert body["price_ngwee"] == 14000
        assert body["matches_limit"] == 60
        assert any(
            u.get("tier") == "starter" and u.get("price_ngwee") == 14000
            for u in spy.upserted
        )

    def test_patch_free_price_must_be_zero(self, client, admin_headers, fake_supabase):
        fake_supabase.set_table("users", _superadmin_users())
        fake_supabase.set_table("tier_config", _TierConfigQuery())
        resp = client.patch(
            "/api/v1/admin/tiers/free",
            headers=admin_headers,
            json={"price_ngwee": 100, "matches_limit": 10},
        )
        assert resp.status_code == 422

    def test_patch_unknown_tier(self, client, admin_headers, fake_supabase):
        fake_supabase.set_table("users", _superadmin_users())
        fake_supabase.set_table("tier_config", _TierConfigQuery())
        resp = client.patch(
            "/api/v1/admin/tiers/enterprise",
            headers=admin_headers,
            json={"price_ngwee": 10000, "matches_limit": 50},
        )
        assert resp.status_code == 404
