"""Tests for match-scoped cover letter versioning endpoints."""
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import FakeSupabaseQuery


class _VersionsTable(FakeSupabaseQuery):
    """Accumulates inserted cover letter rows for version listing tests."""

    _counter = 0

    def __init__(self, data=None, count=None):
        super().__init__(data, count)
        self._limit_n: int | None = None
        self._order_desc = False
        self._return_last_insert = False

    def select(self, *args, **kwargs):
        self._limit_n = None
        self._order_desc = False
        self._return_last_insert = False
        return self

    def insert(self, data):
        self._limit_n = None
        self._order_desc = False
        self._return_last_insert = True
        row = dict(data) if isinstance(data, dict) else data
        if isinstance(row, dict):
            _VersionsTable._counter += 1
            row.setdefault("id", f"ver-{_VersionsTable._counter}")
            row.setdefault("created_at", "2026-05-27T14:00:00+00:00")
            if isinstance(self._data, list):
                self._data.append(row)
            else:
                self._data = [row]
        return self

    def order(self, *args, **kwargs):
        self._order_desc = bool(kwargs.get("desc"))
        return self

    def limit(self, n):
        self._limit_n = n
        return self

    def execute(self):
        if self._return_last_insert and self._data:
            rows = [self._data[-1]]
            self._return_last_insert = False
        else:
            rows = list(self._data or [])
            if self._order_desc:
                rows.sort(key=lambda r: int(r.get("version_number") or 0), reverse=True)
            if self._limit_n is not None:
                rows = rows[: self._limit_n]
        result = MagicMock()
        result.data = rows
        result.count = len(rows)
        return result


class _SingleQuery(FakeSupabaseQuery):
    def single(self):
        self._single = True
        return self

    def execute(self):
        result = MagicMock()
        if getattr(self, "_single", False) and self._data:
            result.data = (
                self._data[0] if isinstance(self._data, list) else self._data
            )
        else:
            result.data = self._data
        result.count = getattr(self, "_count", None)
        return result


def _seed_user(fake_supabase, tier="professional"):
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "test-user-id",
                    "phone": "+260971234567",
                    "role": "user",
                    "subscription_tier": tier,
                    "matches_viewed_this_month": 0,
                    "billing_cycle_reset": "2099-01-01",
                }
            ]
        ),
    )


def _seed_match(fake_supabase):
    fake_supabase.set_table(
        "matches",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "match-1",
                    "user_id": "test-user-id",
                    "job_id": "job-1",
                }
            ]
        ),
    )


class TestMatchCoverLetterVersions:
    def test_free_tier_blocked(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase, tier="free")
        _seed_match(fake_supabase)

        resp = client.get(
            "/api/v1/matches/match-1/cover-letter/versions",
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_list_versions_empty(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase, tier="professional")
        _seed_match(fake_supabase)
        fake_supabase.set_table("cover_letter_versions", FakeSupabaseQuery(data=[]))

        resp = client.get(
            "/api/v1/matches/match-1/cover-letter/versions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["versions"] == []
        assert body["latest"] is None

    def test_save_and_list_versions(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase, tier="professional")
        _seed_match(fake_supabase)

        _VersionsTable._counter = 0
        fake_supabase.set_table("cover_letter_versions", _VersionsTable(data=[]))

        save_resp = client.post(
            "/api/v1/matches/match-1/cover-letter/save",
            headers=auth_headers,
            json={
                "content_md": "Dear Hiring Manager,\n\nFirst draft.",
                "source": "ai",
            },
        )
        assert save_resp.status_code == 200
        v1 = save_resp.json()
        assert v1["version_number"] == 1
        assert v1["generated_by"] == "ai"

        edit_resp = client.post(
            "/api/v1/matches/match-1/cover-letter/save",
            headers=auth_headers,
            json={
                "content_md": "Dear Hiring Manager,\n\nEdited paragraph.",
                "parent_version_id": v1["id"],
                "source": "user_edit",
            },
        )
        assert edit_resp.status_code == 200
        v2 = edit_resp.json()
        assert v2["version_number"] == 2

        list_resp = client.get(
            "/api/v1/matches/match-1/cover-letter/versions",
            headers=auth_headers,
        )
        assert list_resp.status_code == 200
        listed = list_resp.json()
        assert len(listed["versions"]) == 2
        by_num = {v["version_number"]: v for v in listed["versions"]}
        assert "First draft" in by_num[1]["content_md"]
        assert "Edited paragraph" in by_num[2]["content_md"]
        assert listed["latest"]["version_number"] == 2

    @patch(
        "app.api.v1.match_cover_letter.generate_tailored_cover_letter",
        new_callable=AsyncMock,
    )
    def test_generate_creates_ai_version(
        self, mock_generate, client, auth_headers, fake_supabase
    ):
        _seed_user(fake_supabase, tier="professional")
        _seed_match(fake_supabase)
        fake_supabase.set_table(
            "cvs",
            FakeSupabaseQuery(data=[{"raw_text": "Accountant with SAP."}]),
        )
        fake_supabase.set_table(
            "jobs",
            FakeSupabaseQuery(
                data=[
                    {
                        "title": "Finance Lead",
                        "company": "Zed Bank",
                        "description": "SAP required.",
                    }
                ]
            ),
        )
        _VersionsTable._counter = 0
        fake_supabase.set_table("cover_letter_versions", _VersionsTable(data=[]))
        mock_generate.return_value = {
            "content": "Dear Hiring Manager,\n\nAI letter body.",
            "word_count": 12,
        }

        resp = client.post(
            "/api/v1/matches/match-1/cover-letter/generate",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "AI letter body" in body["content"]
        assert body["version_number"] == 1
