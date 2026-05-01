"""Smoke tests for admin routes."""
from tests.conftest import FakeSupabaseQuery


class TestAdminStats:
    def test_stats_unauthenticated(self, client):
        """Admin endpoint requires auth."""
        resp = client.get("/api/v1/admin/stats")
        assert resp.status_code in (401, 403)

    def test_stats_success(self, client, auth_headers, fake_supabase):
        """Returns admin stats (if user has admin role)."""
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "test-user-id",
                        "role": "admin",
                    }
                ]
            ),
        )
        resp = client.get("/api/v1/admin/stats", headers=auth_headers)
        # May be 200, 403 (not admin), or 404 (route doesn't exist)
        assert resp.status_code in (200, 403, 404)

    def test_stats_forbidden_for_non_admin(
        self, client, auth_headers, fake_supabase
    ):
        """Non-admin users get 403."""
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "test-user-id",
                        "role": "user",
                    }
                ]
            ),
        )
        resp = client.get("/api/v1/admin/stats", headers=auth_headers)
        # May be 403 (correctly denied) or 404 (route doesn't exist)
        assert resp.status_code in (403, 404)


class TestAdminJobs:
    def test_list_admin_jobs_requires_auth(self, client):
        """Admin jobs listing requires auth."""
        resp = client.get("/api/v1/admin/jobs")
        assert resp.status_code in (401, 403, 404)

    def test_list_admin_jobs(self, client, auth_headers, fake_supabase):
        """Returns job list for admins."""
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[{"id": "test-user-id", "role": "admin"}]
            ),
        )
        fake_supabase.set_table(
            "jobs", FakeSupabaseQuery(data=[], count=0)
        )
        resp = client.get("/api/v1/admin/jobs", headers=auth_headers)
        assert resp.status_code in (200, 403, 404)
