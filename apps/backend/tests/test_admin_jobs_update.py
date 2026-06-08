"""Tests for PATCH /admin/jobs/{job_id} dedupe-key collision behaviour.

Regression for Sentry ZEDCV-BACKEND-1S:
  "duplicate key value violates unique constraint idx_jobs_dedupe_key_active"
  raised by PATCH /api/v1/admin/jobs/{job_id} when the DB trigger
  recomputes dedupe_key to a value already held by another active row.

The primary fix is migration 107 (trigger now INSERT-only).
The secondary fix is a 409 catch in the handler (belt-and-suspenders).

Test name required by the spec: test_patch_does_not_collide_with_existing_dedupe_key
"""
from __future__ import annotations

import copy
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Mirror conftest env so the file is importable standalone.
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


# ── In-process Supabase fake ─────────────────────────────────────────


class _Result:
    def __init__(self, data=None, count=None):
        self.data = list(data or [])
        self.count = count


class _DQ:
    """Chainable query stub backed by _DS table lists."""

    def __init__(self, parent: "_DS", table: str):
        self._p = parent
        self._t = table
        self._op = "select"
        self._pl: Any = None
        self._f: dict[str, Any] = {}
        self._lim: int | None = None

    def select(self, *a, **kw):
        self._op = "select"
        return self

    def insert(self, pl):
        self._op = "insert"
        self._pl = pl
        return self

    def update(self, pl):
        self._op = "update"
        self._pl = pl
        return self

    def upsert(self, pl, **kw):
        self._op = "upsert"
        self._pl = pl
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col, val):
        self._f[col] = val
        return self

    def in_(self, col, vals):
        self._f[col + "__in"] = vals
        return self

    def limit(self, n):
        self._lim = n
        return self

    def order(self, *a, **kw):
        return self

    def single(self):
        return self

    def or_(self, *a, **kw):
        return self

    @property
    def not_(self):
        return self

    def is_(self, *a, **kw):
        return self

    def neq(self, *a, **kw):
        return self

    def gte(self, *a, **kw):
        return self

    def lte(self, *a, **kw):
        return self

    def lt(self, *a, **kw):
        return self

    def ilike(self, *a, **kw):
        return self

    def range(self, *a, **kw):
        return self

    def _rows(self):
        rows = list(self._p.tables.get(self._t, []))
        out = []
        for r in rows:
            ok = True
            for k, v in self._f.items():
                if k.endswith("__in"):
                    if r.get(k[:-4]) not in v:
                        ok = False
                        break
                elif r.get(k) != v:
                    ok = False
                    break
            if ok:
                out.append(r)
        return out

    def execute(self):
        if self._op == "select":
            rows = self._rows()
            if self._lim is not None:
                rows = rows[: self._lim]
            return _Result(data=copy.deepcopy(rows), count=len(rows))

        if self._op == "insert":
            pls = self._pl if isinstance(self._pl, list) else [self._pl]
            ins = []
            for p in pls:
                row = dict(p)
                if self._t == "jobs":
                    row.setdefault("id", f"job-{uuid4()}")
                    row.setdefault("is_active", True)
                    row.setdefault("posted_at", "2026-05-17T00:00:00+00:00")
                    row.setdefault("created_at", "2026-05-17T00:00:00+00:00")
                    row.setdefault("updated_at", "2026-05-17T00:00:00+00:00")
                self._p.tables.setdefault(self._t, []).append(row)
                ins.append(row)
            return _Result(data=copy.deepcopy(ins))

        if self._op == "update":
            if self._t == "jobs" and self._p._raise_on_jobs_update is not None:
                raise self._p._raise_on_jobs_update
            rows = self._rows()
            upd = []
            for r in rows:
                for actual in self._p.tables.get(self._t, []):
                    if (
                        actual is r
                        or actual.get("id") == r.get("id")
                        or (
                            self._t == "job_fingerprints"
                            and actual.get("job_id") == r.get("job_id")
                        )
                    ):
                        actual.update(self._pl)
                        upd.append(actual)
                        break
            return _Result(data=copy.deepcopy(upd))

        if self._op == "upsert":
            pls = self._pl if isinstance(self._pl, list) else [self._pl]
            self._p.tables.setdefault(self._t, []).extend(pls)
            return _Result(data=copy.deepcopy(pls))

        if self._op == "delete":
            rows = self._rows()
            self._p.tables[self._t] = [
                r for r in self._p.tables.get(self._t, []) if r not in rows
            ]
            return _Result(data=copy.deepcopy(rows))

        return _Result()


class _DS:
    """Isolated Supabase fake.  Set _raise_on_jobs_update to simulate a
    DB UniqueViolation on the next jobs.update() call."""

    def __init__(self):
        self.tables: dict[str, list[dict]] = {
            "users": [
                {"id": "test-user-id", "phone": "+260971234567", "role": "admin"}
            ],
            "jobs": [],
            "job_fingerprints": [],
            "job_skills": [],
            "skills": [{"id": "s-py", "name": "python", "canonical_of": None}],
            "skill_aliases": [],
            "analytics_events": [],
        }
        self._raise_on_jobs_update: Exception | None = None
        self.storage = MagicMock()
        self.storage.from_ = MagicMock(return_value=MagicMock())

    def table(self, name: str) -> _DQ:
        return _DQ(self, name)

    def rpc(self, *a, **kw):
        class _R:
            def execute(self_):
                return _Result(data=[])
        return _R()

    def seed_job(self, **overrides) -> str:
        jid = str(uuid4())
        row = {
            "id": jid,
            "title": "Senior Engineer",
            "company": "Acme Corp",
            "location": "Lusaka",
            "description": "Build and maintain backend systems.",
            "source": "manual",
            "is_active": True,
            "is_review_required": False,
            "posted_at": "2026-05-01T00:00:00+00:00",
            "created_at": "2026-05-01T00:00:00+00:00",
            "updated_at": "2026-05-01T00:00:00+00:00",
            "apply_email": "jobs@acme.com",
            "requirements": [],
            "skills_required": [],
            "benefits": [],
            "tools_tech_stack": [],
            "scraping_sources": [],
            "visibility_status": "open",
        }
        row.update(overrides)
        self.tables["jobs"].append(row)
        self.tables["job_fingerprints"].append(
            {"fingerprint": "fp-" + jid, "job_id": jid}
        )
        return jid


# ── Module-scoped client + per-test db reset ─────────────────────────────
#
# Module scope avoids repeated TestClient startup/teardown which hangs
# on Windows asyncio (event loop not fully cleaned up between tests).
# Each test gets a fresh _DS instance injected at module level; tests
# that need to inspect or mutate state access `_DS_INSTANCE` directly.

_DS_INSTANCE: _DS | None = None


@pytest.fixture(scope="module")
def dedupe_app():
    """One TestClient for the whole module, with a swappable DB."""
    global _DS_INSTANCE
    _DS_INSTANCE = _DS()

    from app.core.config import get_settings
    from app.core.deps import get_supabase
    from main import app

    get_settings.cache_clear()

    def _get_db():
        return _DS_INSTANCE

    app.dependency_overrides[get_supabase] = _get_db
    try:
        from app.core.rate_limit import limiter
        limiter.enabled = False
    except Exception:
        pass

    with TestClient(app, headers={"Host": "api.zedapply.com"}, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_db():
    """Fresh DB state before each test (autouse so no test forgets)."""
    global _DS_INSTANCE
    if _DS_INSTANCE is not None:
        _DS_INSTANCE.tables = {
            "users": [
                {"id": "test-user-id", "phone": "+260971234567", "role": "admin"}
            ],
            "jobs": [],
            "job_fingerprints": [],
            "job_skills": [],
            "skills": [{"id": "s-py", "name": "python", "canonical_of": None}],
            "skill_aliases": [],
            "analytics_events": [],
        }
        _DS_INSTANCE._raise_on_jobs_update = None


def _jwt() -> str:
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "test-user-id",
            "phone": "+260971234567",
            "exp": now + timedelta(hours=24),
            "iat": now,
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )


_AH = {"Authorization": f"Bearer {_jwt()}"}


# ── Tests ─────────────────────────────────────────────────────────────


class TestPatchDedupeKeyCollision:
    """Primary regression: Sentry ZEDCV-BACKEND-1S.

    Belt-and-suspenders: even before migration 107 reaches prod, the
    handler must convert a UniqueViolation on idx_jobs_dedupe_key_active
    into a 409 (not a bare 500 that bypasses CORS headers).
    """

    def test_patch_does_not_collide_with_existing_dedupe_key(self, dedupe_app):
        """Core test name required by the spec.

        Simulates the DB raising a unique-constraint error on the jobs
        update.  Asserts the handler returns 409, never 500.
        """
        jid = _DS_INSTANCE.seed_job()
        _DS_INSTANCE._raise_on_jobs_update = Exception(
            "duplicate key value violates unique constraint "
            '"idx_jobs_dedupe_key_active"'
        )

        with patch(
            "app.api.v1.admin.generate_embedding",
            new=AsyncMock(return_value=[0.0] * 768),
        ):
            r = dedupe_app.patch(
                f"/api/v1/admin/jobs/{jid}",
                json={"title": "Senior Engineer", "company": "Other Corp"},
                headers=_AH,
            )

        assert r.status_code == 409, (
            f"Expected 409 for dedupe collision, got {r.status_code}: {r.text}"
        )
        detail = r.json().get("detail", "")
        assert any(
            kw in detail.lower()
            for kw in ("duplicate", "collision", "title", "company", "location")
        ), f"409 body not actionable: {detail!r}"

    def test_409_body_is_actionable(self, dedupe_app):
        """Detail must explain the collision, not a generic server error."""
        jid = _DS_INSTANCE.seed_job()
        _DS_INSTANCE._raise_on_jobs_update = Exception(
            "duplicate key value violates unique constraint idx_jobs_dedupe_key_active"
        )

        with patch(
            "app.api.v1.admin.generate_embedding",
            new=AsyncMock(return_value=[0.0] * 768),
        ):
            r = dedupe_app.patch(
                f"/api/v1/admin/jobs/{jid}",
                json={"title": "Clashing Title"},
                headers=_AH,
            )

        assert r.status_code == 409
        assert "duplicate" in r.json()["detail"].lower() or "collision" in r.json()["detail"].lower()

    def test_non_dedupe_db_error_is_not_swallowed_as_409(self, dedupe_app):
        """A non-dedupe DB error must NOT be returned as 409."""
        jid = _DS_INSTANCE.seed_job()
        _DS_INSTANCE._raise_on_jobs_update = Exception("connection timeout")

        with patch(
            "app.api.v1.admin.generate_embedding",
            new=AsyncMock(return_value=[0.0] * 768),
        ):
            r = dedupe_app.patch(
                f"/api/v1/admin/jobs/{jid}",
                json={"description": "Updated description that is long enough."},
                headers=_AH,
            )

        assert r.status_code != 409, "Non-dedupe error must not return 409"


class TestPatchNoDedupeCollisionAfterMigration107:
    """After migration 107 (trigger INSERT-only), admin edits that don't
    involve the dedupe fields must succeed normally — no exception injected."""

    def test_description_only_patch_returns_200(self, dedupe_app):
        jid = _DS_INSTANCE.seed_job()

        with patch(
            "app.api.v1.admin.generate_embedding",
            new=AsyncMock(return_value=[0.0] * 768),
        ):
            r = dedupe_app.patch(
                f"/api/v1/admin/jobs/{jid}",
                json={"description": "Updated description that is long enough to pass."},
                headers=_AH,
            )

        assert r.status_code == 200, r.text
        assert r.json()["description"] == "Updated description that is long enough to pass."

    def test_salary_patch_does_not_raise(self, dedupe_app):
        jid = _DS_INSTANCE.seed_job()

        with patch(
            "app.api.v1.admin.generate_embedding",
            new=AsyncMock(return_value=[0.0] * 768),
        ):
            r = dedupe_app.patch(
                f"/api/v1/admin/jobs/{jid}",
                json={"salary_min": 150000},
                headers=_AH,
            )

        assert r.status_code == 200, r.text
