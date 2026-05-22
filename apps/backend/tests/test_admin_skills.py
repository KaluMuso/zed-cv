"""Tests for admin skill dictionary and ingest canonicalization."""
from __future__ import annotations

import copy
import os
import sys
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-service-key")
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-key")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("INGEST_API_KEY", "test-ingest-key")

_BACKEND_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import pytest
from fastapi.testclient import TestClient
from jose import jwt


def _admin_token() -> str:
    return jwt.encode(
        {"sub": "admin-user-id"},
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )


class _Result:
    def __init__(self, data: list | None = None, count: int | None = None):
        self.data = list(data or [])
        self.count = count


class _Query:
    def __init__(self, parent: "SkillsFakeSupabase", table: str):
        self._parent = parent
        self._table = table
        self._op = "select"
        self._payload: Any = None
        self._filters: dict[str, Any] = {}
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None

    def select(self, *a, **kw):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def eq(self, col: str, val: Any):
        self._filters[col] = val
        return self

    @property
    def not_(self):
        return self

    def is_(self, col: str, val: Any):
        if str(val).lower() == "null":
            self._filters[col + "__is_null"] = True
        else:
            self._filters[col] = val
        return self

    def order(self, col: str, desc: bool = False):
        self._order = (col, desc)
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def execute(self):
        return self._parent._run(self)


class SkillsFakeSupabase:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {
            "users": [
                {
                    "id": "admin-user-id",
                    "phone": "+260971234567",
                    "role": "admin",
                }
            ],
            "canonical_skills": [],
            "raw_skill_mappings": [],
            "jobs": [],
            "job_fingerprints": [],
            "job_skills": [],
            "skills": [],
        }

    def table(self, name: str):
        return _Query(self, name)

    def rpc(self, *a, **kw):
        return _Query(self, "__rpc__")

    def _match(self, row: dict, filters: dict[str, Any]) -> bool:
        for key, val in filters.items():
            if key.endswith("__is_null"):
                col = key[: -len("__is_null")]
                if row.get(col) is not None:
                    return False
            elif row.get(key) != val:
                return False
        return True

    def _run(self, q: _Query) -> _Result:
        rows = self.tables.setdefault(q._table, [])
        if q._op == "insert":
            payload = copy.deepcopy(q._payload)
            if isinstance(payload, dict):
                if "id" not in payload:
                    payload["id"] = str(uuid4())
                if q._table == "canonical_skills" and "created_at" not in payload:
                    payload["created_at"] = datetime.now(timezone.utc).isoformat()
                rows.append(payload)
                return _Result([payload])
            out = []
            for item in payload:
                row = copy.deepcopy(item)
                if "id" not in row:
                    row["id"] = str(uuid4())
                rows.append(row)
                out.append(row)
            return _Result(out)

        if q._op == "update":
            updated = []
            for row in rows:
                if self._match(row, q._filters):
                    row.update(q._payload)
                    updated.append(copy.deepcopy(row))
            return _Result(updated)

        matched = [r for r in rows if self._match(r, q._filters)]
        if q._order:
            col, desc = q._order
            matched.sort(key=lambda r: r.get(col, 0), reverse=desc)
        if q._limit is not None:
            matched = matched[: q._limit]
        return _Result(matched)


@pytest.fixture
def skills_fake():
    return SkillsFakeSupabase()


@pytest.fixture
def client(skills_fake):
    from main import app
    from app.core import deps

    app.dependency_overrides[deps.get_supabase] = lambda: skills_fake
    with TestClient(app, headers={"Host": "api.zedapply.com"}) as c:
        yield c
    app.dependency_overrides.clear()


class TestSkillsDictionaryService:
    def test_record_inserts_pending_raw(self, skills_fake):
        from app.services import skills_dictionary

        out = skills_dictionary.record_raw_skills(skills_fake, ["  MS Excel  "])
        assert out == ["MS Excel"]
        assert len(skills_fake.tables["raw_skill_mappings"]) == 1
        assert skills_fake.tables["raw_skill_mappings"][0]["raw_name"] == "ms excel"
        assert skills_fake.tables["raw_skill_mappings"][0].get("canonical_id") is None
        assert skills_fake.tables["raw_skill_mappings"][0]["occurrences"] == 1

    def test_record_increments_occurrences(self, skills_fake):
        from app.services import skills_dictionary

        skills_fake.tables["raw_skill_mappings"].append(
            {
                "id": "raw-1",
                "raw_name": "ts",
                "canonical_id": None,
                "occurrences": 3,
            }
        )
        out = skills_dictionary.record_raw_skills(skills_fake, ["ts"])
        assert out == ["ts"]
        assert skills_fake.tables["raw_skill_mappings"][0]["occurrences"] == 4

    def test_record_replaces_when_canonical_set(self, skills_fake):
        from app.services import skills_dictionary

        skills_fake.tables["canonical_skills"].append(
            {"id": "canon-1", "name": "TypeScript", "created_at": "2026-01-01T00:00:00Z"}
        )
        skills_fake.tables["raw_skill_mappings"].append(
            {
                "id": "raw-1",
                "raw_name": "ts",
                "canonical_id": "canon-1",
                "occurrences": 10,
            }
        )
        out = skills_dictionary.record_raw_skills(skills_fake, ["ts"])
        assert out == ["TypeScript"]


class TestAdminSkillsRoutes:
    def test_pending_requires_admin(self, client):
        r = client.get("/api/v1/admin/skills/pending")
        assert r.status_code in (401, 403)

    def test_pending_lists_unmapped_sorted(self, client, skills_fake):
        uid_a, uid_b, uid_c, uid_x = (str(uuid4()) for _ in range(4))
        skills_fake.tables["raw_skill_mappings"] = [
            {"id": uid_a, "raw_name": "excel", "canonical_id": None, "occurrences": 2},
            {"id": uid_b, "raw_name": "word", "canonical_id": None, "occurrences": 9},
            {
                "id": uid_c,
                "raw_name": "mapped",
                "canonical_id": uid_x,
                "occurrences": 100,
            },
        ]
        r = client.get(
            "/api/v1/admin/skills/pending",
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert r.status_code == 200
        names = [p["raw_name"] for p in r.json()["pending"]]
        assert names == ["word", "excel"]

    def test_merge_creates_canonical_and_links(self, client, skills_fake):
        raw_id = str(uuid4())
        skills_fake.tables["raw_skill_mappings"] = [
            {"id": raw_id, "raw_name": "ms word", "canonical_id": None, "occurrences": 5},
        ]
        r = client.post(
            "/api/v1/admin/skills/merge",
            headers={"Authorization": f"Bearer {_admin_token()}"},
            json={
                "raw_skill_id": raw_id,
                "canonical_skill_name": "Microsoft Office",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["canonical_skill"]["name"] == "Microsoft Office"
        assert body["mapping"]["canonical_id"] == body["canonical_skill"]["id"]
        assert skills_fake.tables["raw_skill_mappings"][0]["canonical_id"] is not None

    def test_merge_404_unknown_raw(self, client):
        r = client.post(
            "/api/v1/admin/skills/merge",
            headers={"Authorization": f"Bearer {_admin_token()}"},
            json={
                "raw_skill_id": str(uuid4()),
                "canonical_skill_name": "Microsoft Excel",
            },
        )
        assert r.status_code == 404

    def test_non_admin_forbidden(self, client, skills_fake):
        skills_fake.tables["users"] = [
            {"id": "user-1", "phone": "+260971111111", "role": "user"}
        ]
        token = jwt.encode(
            {"sub": "user-1"},
            os.environ["JWT_SECRET"],
            algorithm="HS256",
        )
        r = client.get(
            "/api/v1/admin/skills/pending",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
