"""Integration tests for /api/v1/admin/jobs CRUD (Wave 4 PR 2).

These cover the POST/PATCH/DELETE endpoints in app/api/v1/admin.py.

Strategy: in-memory Supabase fake tuned for the jobs pipeline (jobs,
job_fingerprints, job_skills, skills, skill_aliases, analytics_events,
users). The Wave-2 skill resolver runs against the same fake — its
Pass 1 (exact name) is enough for the resolver-collapse test, so the
trgm/vector RPCs return empty and Pass 4 (auto-insert) never fires.

Embedding generation is patched in both modules that import it
(`app.api.v1.admin.generate_embedding` and
`app.services.skill_resolver.generate_embedding`). Each test that cares
about embedding behaviour declares its own AsyncMock side effect.
"""

from __future__ import annotations

import copy
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Mirror conftest's env setup so the file is importable standalone.
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


# ── In-memory Supabase fake ──────────────────────────────────────────


class _Result:
    def __init__(self, data: Any = None, count: int | None = None):
        if isinstance(data, (list, tuple)):
            self.data = list(data)
        elif data is None:
            self.data = []
        else:
            self.data = data
        self.count = count


class _Query:
    """Generic chainable query over a row-list stored on the parent fake."""

    def __init__(self, parent: "JobsFakeSupabase", table: str):
        self._parent = parent
        self._table = table
        self._op = "select"
        self._payload: Any = None
        self._filters: dict[str, Any] = {}
        self._lt: dict[str, Any] = {}
        self._gte: dict[str, Any] = {}
        self._not_null: set[str] = set()
        self._negate_is = False
        self._limit: int | None = None

    # ── operation setters ──
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

    def upsert(self, payload, **kw):
        self._op = "upsert"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    # ── filter chain ──
    def eq(self, col: str, val: Any):
        self._filters[col] = val
        return self

    def in_(self, col: str, vals: list):
        self._filters[col + "__in"] = vals
        return self

    @property
    def not_(self):
        self._negate_is = True
        return self

    def is_(self, col: str, val: Any):
        if self._negate_is and str(val).lower() == "null":
            self._not_null.add(col)
            self._negate_is = False
        elif str(val).lower() == "null":
            self._filters[col] = None
        else:
            self._filters[col] = val
        return self

    def neq(self, *a, **kw):
        return self

    def gte(self, col: str, val: Any):
        self._gte[col] = val
        return self

    def lte(self, *a, **kw):
        return self

    def lt(self, col: str, val: Any):
        self._lt[col] = val
        return self

    def ilike(self, *a, **kw):
        return self

    def like(self, *a, **kw):
        return self

    def or_(self, *a, **kw):
        return self

    def order(self, *a, **kw):
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def range(self, *a, **kw):
        return self

    def single(self):
        return self

    # ── apply ──
    def _row_matches(self, row: dict) -> bool:
        for k, v in self._filters.items():
            if k.endswith("__in"):
                col = k[: -len("__in")]
                if row.get(col) not in v:
                    return False
            elif row.get(k) != v:
                return False
        for col in self._not_null:
            if row.get(col) is None:
                return False
        for col, bound in self._lt.items():
            val = row.get(col)
            if val is None or val >= bound:
                return False
        for col, bound in self._gte.items():
            val = row.get(col)
            if val is None or val < bound:
                return False
        return True

    def _matches(self) -> list[dict]:
        rows = list(self._parent.tables.get(self._table, []))
        return [r for r in rows if self._row_matches(r)]

    def execute(self):
        if self._op == "select":
            rows = self._matches()
            if self._limit is not None:
                rows = rows[: self._limit]
            return _Result(data=copy.deepcopy(rows), count=len(rows))

        if self._op == "insert":
            payload = self._payload
            payloads = payload if isinstance(payload, list) else [payload]
            inserted = []
            for p in payloads:
                row = dict(p)
                if self._table == "jobs":
                    row.setdefault("id", f"job-{uuid4()}")
                    row.setdefault("is_active", True)
                    row.setdefault("posted_at", "2026-05-17T00:00:00+00:00")
                    row.setdefault("created_at", "2026-05-17T00:00:00+00:00")
                    row.setdefault("updated_at", "2026-05-17T00:00:00+00:00")
                self._parent.tables.setdefault(self._table, []).append(row)
                inserted.append(row)
            self._parent.writes.append(
                {"op": "insert", "table": self._table, "rows": inserted}
            )
            return _Result(data=copy.deepcopy(inserted))

        if self._op == "update":
            rows = self._matches()
            updated = []
            for r in rows:
                for actual in self._parent.tables.get(self._table, []):
                    if actual is r or actual.get("id") == r.get("id") or (
                        self._table == "job_fingerprints"
                        and actual.get("job_id") == r.get("job_id")
                    ):
                        actual.update(self._payload)
                        updated.append(actual)
                        break
            self._parent.writes.append(
                {
                    "op": "update",
                    "table": self._table,
                    "payload": dict(self._payload),
                    "filters": dict(self._filters),
                    "ids": [r.get("id") for r in updated],
                }
            )
            return _Result(data=copy.deepcopy(updated))

        if self._op == "upsert":
            payload = self._payload
            payloads = payload if isinstance(payload, list) else [payload]
            self._parent.tables.setdefault(self._table, []).extend(payloads)
            return _Result(data=copy.deepcopy(payloads))

        if self._op == "delete":
            rows = self._matches()
            remaining = [
                r for r in self._parent.tables.get(self._table, [])
                if r not in rows
            ]
            self._parent.tables[self._table] = remaining
            self._parent.writes.append(
                {"op": "delete", "table": self._table, "ids": [r.get("id") or r.get("job_id") for r in rows]}
            )
            return _Result(data=copy.deepcopy(rows))

        return _Result()


class _Rpc:
    """Fake RPC that handles known functions; falls back to returning empty."""

    def __init__(self, parent: "JobsFakeSupabase", fn_name: str):
        self._parent = parent
        self._fn_name = fn_name

    def execute(self):
        if self._fn_name == "deactivate_expired_jobs":
            from datetime import date
            today = date.today().isoformat()
            jobs = self._parent.tables.get("jobs", [])
            count = 0
            for row in jobs:
                closing = row.get("closing_date")
                if closing and closing < today and row.get("is_active") is True:
                    row["is_active"] = False
                    count += 1
            return _Result(data=count)
        return _Result(data=[])


class JobsFakeSupabase:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {
            "users": [],
            "jobs": [],
            "job_fingerprints": [],
            "job_skills": [],
            "skills": [],
            "skill_aliases": [],
            "analytics_events": [],
        }
        self.writes: list[dict] = []
        self.storage = MagicMock()
        self.storage.from_ = MagicMock(return_value=MagicMock())

    def table(self, name: str) -> _Query:
        return _Query(self, name)

    def rpc(self, fn_name: str, *a, **kw) -> _Rpc:
        return _Rpc(self, fn_name)


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def jobs_fake():
    fake = JobsFakeSupabase()
    # Admin user the JWT claims (auth_headers fixture in conftest uses
    # sub='test-user-id'; require_admin reads this row).
    fake.tables["users"].append(
        {"id": "test-user-id", "phone": "+260971234567", "role": "admin"}
    )
    # Seed skills so the Wave-2 resolver's Pass 1 (exact match) hits
    # for the resolver-collapse test. canonical_of links postgres →
    # postgresql; the resolver walks the chain and returns the
    # canonical row's id.
    fake.tables["skills"].extend(
        [
            {"id": "s-pg", "name": "postgresql", "canonical_of": None},
            {"id": "s-pg-alias", "name": "postgres", "canonical_of": "s-pg"},
            {"id": "s-node", "name": "node.js", "canonical_of": None},
            {"id": "s-py", "name": "python", "canonical_of": None},
        ]
    )
    return fake


@pytest.fixture
def regular_user_fake():
    fake = JobsFakeSupabase()
    fake.tables["users"].append(
        {"id": "test-user-id", "phone": "+260971234567", "role": "user"}
    )
    return fake


@pytest.fixture
def admin_client(jobs_fake):
    from app.core.config import get_settings
    from app.core.deps import get_supabase
    from main import app

    get_settings.cache_clear()
    app.dependency_overrides[get_supabase] = lambda: jobs_fake
    try:
        from app.core.rate_limit import limiter
        limiter.enabled = False
    except Exception:
        pass

    with TestClient(app, headers={"Host": "api.zedapply.com"}) as c:
        yield c

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def regular_client(regular_user_fake):
    from app.core.config import get_settings
    from app.core.deps import get_supabase
    from main import app

    get_settings.cache_clear()
    app.dependency_overrides[get_supabase] = lambda: regular_user_fake
    try:
        from app.core.rate_limit import limiter
        limiter.enabled = False
    except Exception:
        pass

    with TestClient(app, headers={"Host": "api.zedapply.com"}) as c:
        yield c

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def auth_headers():
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    now = datetime.now(timezone.utc)
    tok = jwt.encode(
        {
            "sub": "test-user-id",
            "phone": "+260971234567",
            "exp": now + timedelta(hours=24),
            "iat": now,
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {tok}"}


def _valid_payload(**overrides) -> dict:
    base = {
        "title": "Backend Engineer",
        "company": "Zed Tech",
        "location": "Lusaka",
        "description": "Build and ship API services with Python and PostgreSQL.",
        "employment_type": "full_time",
        "work_arrangement": "on_site",
        "requirements": ["5+ years backend experience"],
        "skills_required": ["python"],
        "apply_email": "jobs@zedtech.com",
        "source_url": "https://careers.zedtech.com/jobs/backend-engineer",
        "closing_date": "2026-12-31",
    }
    base.update(overrides)
    return base


def _patch_embedding(vector_value: list[float] | None = None):
    """Patch generate_embedding in BOTH binding sites. Returns the mock
    so tests can swap side_effect mid-test if needed."""
    mock = AsyncMock(return_value=vector_value or [0.01] * 768)
    return mock


# ── Auth gating ──────────────────────────────────────────────────────


class TestAuthGating:
    def test_create_requires_auth(self, admin_client):
        r = admin_client.post("/api/v1/admin/jobs", json=_valid_payload())
        assert r.status_code in (401, 403)

    def test_create_rejects_non_admin(self, regular_client, auth_headers):
        r = regular_client.post(
            "/api/v1/admin/jobs", json=_valid_payload(), headers=auth_headers
        )
        assert r.status_code == 403


# ── POST ─────────────────────────────────────────────────────────────


class TestCreate:
    def test_validates_payload(self, admin_client, auth_headers, jobs_fake):
        # Bad salary order
        bad = _valid_payload(salary_min=200000, salary_max=100000)
        r = admin_client.post(
            "/api/v1/admin/jobs", json=bad, headers=auth_headers
        )
        assert r.status_code == 422
        assert "salary_min" in r.text

        # Missing required field
        bad = _valid_payload()
        del bad["title"]
        r = admin_client.post(
            "/api/v1/admin/jobs", json=bad, headers=auth_headers
        )
        assert r.status_code == 422

        # Unknown field (extra='forbid')
        bad = _valid_payload(zed_unknown_field="oops")
        r = admin_client.post(
            "/api/v1/admin/jobs", json=bad, headers=auth_headers
        )
        assert r.status_code == 422

        # Neither apply_url nor apply_email (XOR violated)
        bad = _valid_payload()
        del bad["apply_email"]
        r = admin_client.post(
            "/api/v1/admin/jobs", json=bad, headers=auth_headers
        )
        assert r.status_code == 422
        # Both apply_url AND apply_email (XOR violated)
        bad = _valid_payload(apply_url="https://example.com/apply")
        r = admin_client.post(
            "/api/v1/admin/jobs", json=bad, headers=auth_headers
        )
        assert r.status_code == 422

    def test_persists_with_embedding_and_fingerprint(
        self, admin_client, auth_headers, jobs_fake
    ):
        emb = _patch_embedding([0.1] * 768)
        with patch("app.api.v1.admin.generate_embedding", emb), patch(
            "app.services.skill_resolver.generate_embedding", emb
        ):
            r = admin_client.post(
                "/api/v1/admin/jobs",
                json=_valid_payload(),
                headers=auth_headers,
            )
        assert r.status_code == 201, r.text
        body = r.json()

        # Persisted row
        rows = jobs_fake.tables["jobs"]
        assert len(rows) == 1
        job = rows[0]
        assert job["is_active"] is True
        assert job["updated_by_user_id"] == "test-user-id"
        assert isinstance(job["embedding"], list)
        assert len(job["embedding"]) == 768

        # Fingerprint row
        fps = jobs_fake.tables["job_fingerprints"]
        assert len(fps) == 1
        assert fps[0]["job_id"] == job["id"]

        # Response model fidelity
        assert body["id"] == job["id"]
        assert body["title"] == "Backend Engineer"

    def test_runs_skills_through_resolver(
        self, admin_client, auth_headers, jobs_fake
    ):
        emb = _patch_embedding([0.1] * 768)
        with patch("app.api.v1.admin.generate_embedding", emb), patch(
            "app.services.skill_resolver.generate_embedding", emb
        ):
            r = admin_client.post(
                "/api/v1/admin/jobs",
                json=_valid_payload(
                    skills_required=["postgres", "PostgreSQL", "node.js"]
                ),
                headers=auth_headers,
            )
        assert r.status_code == 201, r.text

        job_id = r.json()["id"]
        links = [
            x for x in jobs_fake.tables["job_skills"] if x["job_id"] == job_id
        ]
        skill_ids = {link["skill_id"] for link in links}
        # postgres → postgresql via canonical_of, PostgreSQL → postgresql,
        # node.js → node.js. Two distinct canonical ids.
        assert skill_ids == {"s-pg", "s-node"}, skill_ids

    def test_emits_analytics_event(self, admin_client, auth_headers, jobs_fake):
        emb = _patch_embedding([0.1] * 768)
        with patch("app.api.v1.admin.generate_embedding", emb), patch(
            "app.services.skill_resolver.generate_embedding", emb
        ):
            r = admin_client.post(
                "/api/v1/admin/jobs",
                json=_valid_payload(),
                headers=auth_headers,
            )
        assert r.status_code == 201, r.text
        events = jobs_fake.tables["analytics_events"]
        assert any(e["event"] == "admin_job_created" for e in events), events
        evt = next(e for e in events if e["event"] == "admin_job_created")
        assert evt["user_id"] == "test-user-id"
        assert evt["properties"]["admin_user_id"] == "test-user-id"
        assert evt["properties"]["source"] == "admin"
        assert evt["properties"]["skill_count"] == 1  # one python


# ── PATCH ────────────────────────────────────────────────────────────


def _seed_job(jobs_fake, **fields) -> str:
    job_id = f"job-{uuid4()}"
    row = {
        "id": job_id,
        "title": "Original Title",
        "company": "Zed Tech",
        "location": "Lusaka",
        "description": "Original description text.",
        "embedding": [0.1] * 768,
        "apply_email": "jobs@zedtech.com",
        "source": "manual",
        "is_active": True,
        "posted_at": "2026-05-17T00:00:00+00:00",
        "created_at": "2026-05-17T00:00:00+00:00",
        "updated_at": "2026-05-17T00:00:00+00:00",
    }
    row.update(fields)
    jobs_fake.tables["jobs"].append(row)
    jobs_fake.tables["job_fingerprints"].append(
        {"job_id": job_id, "fingerprint": "seed-fp"}
    )
    return job_id


class TestPatch:
    def test_partial_update_preserves_embedding(
        self, admin_client, auth_headers, jobs_fake
    ):
        job_id = _seed_job(jobs_fake)
        before = list(jobs_fake.tables["jobs"][0]["embedding"])

        # generate_embedding patched but should NOT be called for a
        # metadata-only PATCH. The mock would raise if invoked.
        emb = AsyncMock(side_effect=AssertionError("embedding regen forbidden"))
        with patch("app.api.v1.admin.generate_embedding", emb):
            r = admin_client.patch(
                f"/api/v1/admin/jobs/{job_id}",
                json={"apply_email": "new@example.com"},
                headers=auth_headers,
            )
        assert r.status_code == 200, r.text

        row = jobs_fake.tables["jobs"][0]
        assert row["apply_email"] == "new@example.com"
        assert row["embedding"] == before  # unchanged
        assert row["updated_by_user_id"] == "test-user-id"
        emb.assert_not_called()

    def test_regenerates_embedding_on_description_change(
        self, admin_client, auth_headers, jobs_fake
    ):
        job_id = _seed_job(jobs_fake)
        before = list(jobs_fake.tables["jobs"][0]["embedding"])

        emb = _patch_embedding([0.9] * 768)
        with patch("app.api.v1.admin.generate_embedding", emb):
            r = admin_client.patch(
                f"/api/v1/admin/jobs/{job_id}",
                json={"description": "A completely different description now."},
                headers=auth_headers,
            )
        assert r.status_code == 200, r.text

        row = jobs_fake.tables["jobs"][0]
        assert row["embedding"] != before
        assert row["embedding"] == [0.9] * 768
        emb.assert_awaited()

    def test_emits_analytics_event_with_changed_fields(
        self, admin_client, auth_headers, jobs_fake
    ):
        job_id = _seed_job(jobs_fake)

        emb = _patch_embedding([0.5] * 768)
        with patch("app.api.v1.admin.generate_embedding", emb):
            r = admin_client.patch(
                f"/api/v1/admin/jobs/{job_id}",
                json={"description": "Brand new description text here."},
                headers=auth_headers,
            )
        assert r.status_code == 200, r.text

        events = jobs_fake.tables["analytics_events"]
        edited = [e for e in events if e["event"] == "admin_job_edited"]
        assert len(edited) == 1
        props = edited[0]["properties"]
        assert props["job_id"] == job_id
        assert props["admin_user_id"] == "test-user-id"
        assert "description" in props["changed_fields"]
        assert props["embedding_regenerated"] is True
        assert props["skills_changed"] is False

    def test_empty_body_returns_422(
        self, admin_client, auth_headers, jobs_fake
    ):
        job_id = _seed_job(jobs_fake)
        r = admin_client.patch(
            f"/api/v1/admin/jobs/{job_id}", json={}, headers=auth_headers
        )
        assert r.status_code == 422

    def test_missing_job_returns_404(
        self, admin_client, auth_headers, jobs_fake
    ):
        r = admin_client.patch(
            "/api/v1/admin/jobs/nonexistent-id",
            json={"apply_email": "x@y.com"},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_with_empty_requirements_clears_job_skills(
        self, admin_client, auth_headers, jobs_fake
    ):
        """Owner addendum #2: explicit `requirements: []` clears job_skills
        AND regenerates embedding (requirements is in the embedding trigger
        set). 'Three skills before, zero after.'"""
        job_id = _seed_job(jobs_fake, requirements=["python", "postgres", "node.js"])
        # Seed three job_skills links manually so the test is independent
        # of POST routing semantics.
        for sid in ("s-pg", "s-py", "s-node"):
            jobs_fake.tables["job_skills"].append(
                {"job_id": job_id, "skill_id": sid}
            )
        assert len(
            [x for x in jobs_fake.tables["job_skills"] if x["job_id"] == job_id]
        ) == 3

        before_embedding = list(jobs_fake.tables["jobs"][0]["embedding"])
        emb = _patch_embedding([0.7] * 768)
        with patch("app.api.v1.admin.generate_embedding", emb), patch(
            "app.services.skill_resolver.generate_embedding", emb
        ):
            r = admin_client.patch(
                f"/api/v1/admin/jobs/{job_id}",
                json={"requirements": []},
                headers=auth_headers,
            )
        assert r.status_code == 200, r.text

        # job_skills emptied.
        remaining = [
            x for x in jobs_fake.tables["job_skills"] if x["job_id"] == job_id
        ]
        assert remaining == [], remaining
        # Embedding regenerated.
        assert jobs_fake.tables["jobs"][0]["embedding"] != before_embedding
        # Analytics event records skills_changed.
        events = jobs_fake.tables["analytics_events"]
        edited = [e for e in events if e["event"] == "admin_job_edited"]
        assert edited and edited[-1]["properties"]["skills_changed"] is True

    def test_without_requirements_preserves_skills(
        self, admin_client, auth_headers, jobs_fake
    ):
        """Owner addendum #2 inverse: omitting `requirements` from the
        PATCH body leaves job_skills untouched. 'Three before, three
        after.'"""
        job_id = _seed_job(jobs_fake)
        for sid in ("s-pg", "s-py", "s-node"):
            jobs_fake.tables["job_skills"].append(
                {"job_id": job_id, "skill_id": sid}
            )

        # Metadata-only PATCH; embedding mock raises if called.
        emb = AsyncMock(side_effect=AssertionError("embedding regen forbidden"))
        with patch("app.api.v1.admin.generate_embedding", emb):
            r = admin_client.patch(
                f"/api/v1/admin/jobs/{job_id}",
                json={"apply_email": "new@example.com"},
                headers=auth_headers,
            )
        assert r.status_code == 200, r.text

        remaining = [
            x for x in jobs_fake.tables["job_skills"] if x["job_id"] == job_id
        ]
        assert len(remaining) == 3, remaining
        events = jobs_fake.tables["analytics_events"]
        edited = [e for e in events if e["event"] == "admin_job_edited"]
        assert edited and edited[-1]["properties"]["skills_changed"] is False

    def test_fingerprint_collision_warns_and_emits_event(
        self, admin_client, auth_headers, jobs_fake
    ):
        """Owner addendum #1: a PATCH whose new fingerprint matches another
        ACTIVE job's fingerprint is allowed (not 409) but logs a warning
        and emits admin_job_fingerprint_collision."""
        # Active other job with a known fingerprint.
        other_id = _seed_job(jobs_fake, title="Other Active Job")
        jobs_fake.tables["job_fingerprints"][-1]["fingerprint"] = "collision-fp"

        # Job we're going to PATCH.
        target_id = _seed_job(jobs_fake)

        # Patch the fingerprint helper so the recomputed fp deterministically
        # collides with the other active job's fp.
        emb = _patch_embedding([0.42] * 768)
        with patch(
            "app.api.v1.jobs._fingerprint", return_value="collision-fp"
        ), patch("app.api.v1.admin.generate_embedding", emb):
            r = admin_client.patch(
                f"/api/v1/admin/jobs/{target_id}",
                json={"title": "Something That Forces Fingerprint Change"},
                headers=auth_headers,
            )

        assert r.status_code == 200, r.text  # warn-only, no 409
        events = jobs_fake.tables["analytics_events"]
        coll = [e for e in events if e["event"] == "admin_job_fingerprint_collision"]
        assert len(coll) == 1, events
        props = coll[0]["properties"]
        assert props["job_id"] == target_id
        assert props["collided_with_job_id"] == other_id
        assert props["admin_user_id"] == "test-user-id"

    def test_fingerprint_collision_with_inactive_job_does_not_warn(
        self, admin_client, auth_headers, jobs_fake
    ):
        """Inactive jobs' fingerprints don't trigger the collision event —
        admin can revive a soft-deleted listing by recreating its content."""
        inactive_id = _seed_job(jobs_fake, is_active=False)
        jobs_fake.tables["job_fingerprints"][-1]["fingerprint"] = "shared-fp"
        target_id = _seed_job(jobs_fake)

        emb = _patch_embedding([0.42] * 768)
        with patch(
            "app.api.v1.jobs._fingerprint", return_value="shared-fp"
        ), patch("app.api.v1.admin.generate_embedding", emb):
            r = admin_client.patch(
                f"/api/v1/admin/jobs/{target_id}",
                json={"title": "Same content as the inactive job"},
                headers=auth_headers,
            )
        assert r.status_code == 200, r.text
        events = jobs_fake.tables["analytics_events"]
        assert not [
            e for e in events if e["event"] == "admin_job_fingerprint_collision"
        ]


# ── DELETE ───────────────────────────────────────────────────────────


class TestDelete:
    def test_hard_deletes_row(self, admin_client, auth_headers, jobs_fake):
        job_id = _seed_job(jobs_fake)
        assert len(jobs_fake.tables["jobs"]) == 1

        r = admin_client.delete(
            f"/api/v1/admin/jobs/{job_id}", headers=auth_headers
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body == {"deleted": True, "id": job_id}

        # Row has been physically removed from the table.
        assert jobs_fake.tables["jobs"] == []

    def test_missing_job_returns_404(self, admin_client, auth_headers, jobs_fake):
        r = admin_client.delete(
            "/api/v1/admin/jobs/does-not-exist", headers=auth_headers
        )
        assert r.status_code == 404

    def test_emits_analytics_event(
        self, admin_client, auth_headers, jobs_fake
    ):
        job_id = _seed_job(jobs_fake)
        r = admin_client.delete(
            f"/api/v1/admin/jobs/{job_id}", headers=auth_headers
        )
        assert r.status_code == 200, r.text
        events = jobs_fake.tables["analytics_events"]
        deleted_events = [e for e in events if e["event"] == "admin_job_deleted"]
        assert len(deleted_events) == 1
        assert deleted_events[0]["properties"]["job_id"] == job_id
        assert deleted_events[0]["properties"]["admin_user_id"] == "test-user-id"


# ── bulk-deactivate (expired_only) ───────────────────────────────────


class TestBulkDeactivateExpired:
    def test_expired_only_deactivates_past_closing_date_active_jobs(
        self, admin_client, auth_headers, jobs_fake
    ):
        from datetime import date, timedelta

        today = date.today()
        expired_id = _seed_job(
            jobs_fake,
            title="Expired active",
            closing_date=(today - timedelta(days=1)).isoformat(),
            is_active=True,
        )
        future_id = _seed_job(
            jobs_fake,
            title="Future deadline",
            closing_date=(today + timedelta(days=7)).isoformat(),
            is_active=True,
        )
        no_deadline_id = _seed_job(
            jobs_fake,
            title="No closing date",
            closing_date=None,
            is_active=True,
        )
        already_inactive_id = _seed_job(
            jobs_fake,
            title="Already inactive expired",
            closing_date=(today - timedelta(days=3)).isoformat(),
            is_active=False,
        )

        r = admin_client.post(
            "/api/v1/admin/jobs/bulk-deactivate",
            json={"expired_only": True},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["deactivated"] == 1

        by_id = {row["id"]: row for row in jobs_fake.tables["jobs"]}
        assert by_id[expired_id]["is_active"] is False
        assert by_id[future_id]["is_active"] is True
        assert by_id[no_deadline_id]["is_active"] is True
        assert by_id[already_inactive_id]["is_active"] is False

    def test_expired_only_without_flag_requires_job_ids(
        self, admin_client, auth_headers, jobs_fake
    ):
        r = admin_client.post(
            "/api/v1/admin/jobs/bulk-deactivate",
            json={},
            headers=auth_headers,
        )
        assert r.status_code == 422
