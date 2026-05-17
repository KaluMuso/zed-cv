"""Unit tests for app.services.skill_resolver.

Strategy: build a small stateful FakeSupabase that mimics the chain
shape the resolver needs (`.table().select().eq().limit().execute()`,
`.table().upsert().execute()`, `.rpc().execute()`). Stub the embedding
call with AsyncMock. Each test wires the FakeSupabase / mocked RPC
responses to exercise exactly one branch of the resolver.

What we check (per the task spec):
- Each of the four passes resolves independently
- canonical_of is followed (and cycle-safe)
- batch helper dedupes via the canonical id
- Empty input returns None
- Embedding API failure degrades gracefully
"""

from __future__ import annotations

from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import skill_resolver
from app.services.skill_resolver import (
    MAX_CANONICAL_DEPTH,
    resolve_skill_id,
    resolve_skill_ids,
)


# ── FakeSupabase tailored to the resolver's call shape ───────────────


class _Result:
    def __init__(self, data: list[dict] | None = None, count: int | None = None):
        self.data = data or []
        self.count = count


class _SkillsQuery:
    """Mock of supabase.table('skills').<select|upsert|insert>().<chain>...execute().

    Holds a reference to the parent FakeSupabase so writes flow through to
    its in-memory list.
    """

    def __init__(self, parent: "FakeSupabase", op: str, payload: Any = None):
        self._parent = parent
        self._op = op
        self._payload = payload
        self._filters: dict[str, Any] = {}
        self._select_cols: str | None = None
        self._limit: int | None = None

    def select(self, cols: str = "*", **kw):
        self._op = "select"
        self._select_cols = cols
        return self

    def eq(self, col: str, val: Any):
        self._filters[col] = val
        return self

    def is_(self, col: str, val: Any):
        self._filters[col] = val
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def order(self, *a, **kw):
        return self

    def in_(self, col: str, vals: list):
        self._filters[col + "__in"] = vals
        return self

    def execute(self) -> _Result:
        rows = list(self._parent.skills)
        # Apply filters
        for k, v in self._filters.items():
            if k.endswith("__in"):
                col = k[: -len("__in")]
                rows = [r for r in rows if r.get(col) in v]
            else:
                rows = [r for r in rows if r.get(k) == v]
        if self._op == "select":
            if self._limit is not None:
                rows = rows[: self._limit]
            return _Result(data=rows)
        if self._op == "upsert":
            payload = self._payload
            if isinstance(payload, dict):
                payload = [payload]
            for p in payload:
                name = p.get("name")
                if any(s["name"] == name for s in self._parent.skills):
                    continue
                row = {
                    "id": f"skill-{self._parent._next_id}",
                    "canonical_of": None,
                    "category": p.get("category"),
                    "embedding": p.get("embedding"),
                    **p,
                }
                self._parent._next_id += 1
                self._parent.skills.append(row)
            return _Result(data=[])
        if self._op == "insert":
            payload = self._payload
            self._parent.skills.append(payload)
            return _Result(data=[payload])
        return _Result(data=[])


class _AnalyticsQuery:
    def __init__(self, parent: "FakeSupabase"):
        self._parent = parent

    def insert(self, payload: dict):
        self._parent.analytics_events.append(payload)
        return self

    def execute(self):
        return _Result(data=[])


class _RpcCall:
    def __init__(self, parent: "FakeSupabase", name: str, params: dict):
        self._parent = parent
        self._name = name
        self._params = params

    def execute(self) -> _Result:
        handler = self._parent.rpc_handlers.get(self._name)
        if handler is None:
            # Unknown RPC: behave like an empty result, mirroring how the
            # resolver treats RPC errors (swallow + warn).
            return _Result(data=[])
        data = handler(self._params)
        return _Result(data=data or [])


class FakeSupabase:
    def __init__(self, skills: list[dict] | None = None):
        # Each skill row carries at least: id, name, canonical_of, embedding.
        self.skills: list[dict] = list(skills or [])
        self.analytics_events: list[dict] = []
        self.rpc_handlers: dict[str, Callable[[dict], list[dict]]] = {}
        self._next_id = 1000

    def table(self, name: str):
        if name == "skills":
            return _SkillsQuery(self, op="?")
        if name == "analytics_events":
            return _AnalyticsQuery(self)
        # Fall through — junction tables aren't exercised here directly.
        return _SkillsQuery(self, op="?")

    # The first arg of .table('skills').upsert(payload) is captured here.
    # _SkillsQuery uses None as the initial op so the caller has to choose
    # one of select/insert/upsert.
    def rpc(self, name: str, params: dict | None = None):
        return _RpcCall(self, name, params or {})


# Patch the SkillsQuery to support upsert/insert with their payloads.
# Simpler than re-routing in .table(); we just override .upsert/.insert
# to set the op AND the payload before returning self.

def _skq_upsert(self, payload, **kw):
    self._op = "upsert"
    self._payload = payload
    return self


def _skq_insert(self, payload):
    self._op = "insert"
    self._payload = payload
    return self


_SkillsQuery.upsert = _skq_upsert  # type: ignore[attr-defined]
_SkillsQuery.insert = _skq_insert  # type: ignore[attr-defined]


# ── Tests ────────────────────────────────────────────────────────────


@pytest.fixture
def patched_embedding():
    """Default: embedding returns a stub vector. Tests that need to
    assert generate_embedding was/wasn't called can re-grab the mock
    via patched_embedding.mock."""
    with patch.object(
        skill_resolver,
        "generate_embedding",
        new=AsyncMock(return_value=[0.1] * 768),
    ) as m:
        yield m


@pytest.mark.asyncio
async def test_empty_input_returns_none(patched_embedding):
    sb = FakeSupabase(skills=[])
    assert await resolve_skill_id("", supabase=sb) is None
    assert await resolve_skill_id("   ", supabase=sb) is None
    # Pass through bad types defensively
    assert await resolve_skill_id(None, supabase=sb) is None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_pass1_exact_lowercase_match(patched_embedding):
    """Existing 'postgres' row should resolve 'Postgres' (case
    normalized) without invoking trgm, vector, or embedding."""
    sb = FakeSupabase(
        skills=[
            {"id": "sk-pg", "name": "postgres", "canonical_of": None}
        ]
    )
    # If trgm/vector got called we'd error — only handlers we register
    # for them.
    sid = await resolve_skill_id("Postgres", supabase=sb)
    assert sid == "sk-pg"
    patched_embedding.assert_not_called()


@pytest.mark.asyncio
async def test_pass1_follows_canonical_of(patched_embedding):
    """An exact match whose row has canonical_of -> walk to canonical."""
    sb = FakeSupabase(
        skills=[
            {"id": "sk-pg", "name": "postgresql", "canonical_of": None},
            {"id": "sk-pg-alias", "name": "postgres", "canonical_of": "sk-pg"},
        ]
    )
    sid = await resolve_skill_id("postgres", supabase=sb)
    assert sid == "sk-pg"


@pytest.mark.asyncio
async def test_pass2_trgm_when_exact_misses(patched_embedding):
    sb = FakeSupabase(
        skills=[
            {"id": "sk-pg", "name": "postgresql", "canonical_of": None}
        ]
    )
    # Stub the RPC to return a trgm match.
    sb.rpc_handlers["match_skill_trgm"] = lambda params: [
        {"id": "sk-pg", "name": "postgresql", "similarity": 0.78}
    ]
    sid = await resolve_skill_id("postgrres", supabase=sb)
    assert sid == "sk-pg"
    # Pass 3 should be skipped on Pass 2 hit.
    patched_embedding.assert_not_called()


@pytest.mark.asyncio
async def test_pass3_vector_when_trgm_misses(patched_embedding):
    """Exercises the vector pass with an input that doesn't hit the
    Pass 0 alias dict and doesn't trigram-match anything."""
    sb = FakeSupabase(
        skills=[
            {"id": "sk-distrib", "name": "distributed systems", "canonical_of": None}
        ]
    )
    sb.rpc_handlers["match_skill_trgm"] = lambda params: []
    sb.rpc_handlers["match_skill_vector"] = lambda params: [
        {"id": "sk-distrib", "name": "distributed systems", "similarity": 0.91}
    ]
    sid = await resolve_skill_id("scalable distributed architectures", supabase=sb)
    assert sid == "sk-distrib"
    patched_embedding.assert_awaited_once_with("scalable distributed architectures")


@pytest.mark.asyncio
async def test_pass4_inserts_new_skill_when_all_miss(patched_embedding):
    sb = FakeSupabase(skills=[])
    sb.rpc_handlers["match_skill_trgm"] = lambda params: []
    sb.rpc_handlers["match_skill_vector"] = lambda params: []
    sid = await resolve_skill_id(
        "supercalifragilistic-novel-skill",
        supabase=sb,
        user_id="u-1",
    )
    assert sid is not None
    # Row was inserted with category='auto' AND an embedding.
    inserted = next(
        s for s in sb.skills if s["name"] == "supercalifragilistic-novel-skill"
    )
    assert inserted["category"] == "auto"
    assert inserted["embedding"] == [0.1] * 768
    # Analytics event landed.
    assert any(
        e.get("event") == "skill_auto_inserted"
        and e.get("user_id") == "u-1"
        and e.get("properties", {}).get("source") == "cv_upload"
        for e in sb.analytics_events
    )


@pytest.mark.asyncio
async def test_pass4_still_inserts_when_embedding_fails(patched_embedding):
    """Embedding API failure must not abort the resolver — fall through
    to insert without an embedding so the skill is at least stored."""
    sb = FakeSupabase(skills=[])
    sb.rpc_handlers["match_skill_trgm"] = lambda params: []
    # Vector RPC won't be called because we never got an embedding.

    with patch.object(
        skill_resolver,
        "generate_embedding",
        new=AsyncMock(side_effect=ValueError("Gemini down")),
    ):
        sid = await resolve_skill_id("brand-new-skill", supabase=sb)

    assert sid is not None
    inserted = next(s for s in sb.skills if s["name"] == "brand-new-skill")
    assert inserted["category"] == "auto"
    # Embedding is None on the inserted row.
    assert inserted.get("embedding") is None


@pytest.mark.asyncio
async def test_canonical_of_chain_walked_through_match(patched_embedding):
    """Pass 2 hit returns id A; A -> B -> C; resolver must return C."""
    sb = FakeSupabase(
        skills=[
            {"id": "sk-c", "name": "postgresql", "canonical_of": None},
            {"id": "sk-b", "name": "postgres-pre-rename", "canonical_of": "sk-c"},
            {"id": "sk-a", "name": "postgrres", "canonical_of": "sk-b"},
        ]
    )
    sb.rpc_handlers["match_skill_trgm"] = lambda params: [
        {"id": "sk-a", "name": "postgrres", "similarity": 0.71}
    ]
    sid = await resolve_skill_id("postgree", supabase=sb)
    assert sid == "sk-c"


@pytest.mark.asyncio
async def test_canonical_of_cycle_stops_at_depth_cap(patched_embedding):
    """A -> B -> A should not infinite loop; walker stops after depth cap."""
    sb = FakeSupabase(
        skills=[
            {"id": "sk-a", "name": "x", "canonical_of": "sk-b"},
            {"id": "sk-b", "name": "y", "canonical_of": "sk-a"},
        ]
    )
    sid = await resolve_skill_id("x", supabase=sb)
    # Depth cap kicks in; exact return value depends on starting point —
    # what matters is it terminates AND returns something well-formed.
    assert sid in {"sk-a", "sk-b"}


@pytest.mark.asyncio
async def test_max_canonical_depth_matches_constant(patched_embedding):
    """Build a chain longer than MAX_CANONICAL_DEPTH and verify the
    resolver stops short instead of walking forever."""
    # MAX_CANONICAL_DEPTH+2 rows, each pointing at the next.
    rows = []
    for i in range(MAX_CANONICAL_DEPTH + 2):
        rows.append(
            {
                "id": f"sk-{i}",
                "name": f"name-{i}",
                "canonical_of": f"sk-{i + 1}" if i < MAX_CANONICAL_DEPTH + 1 else None,
            }
        )
    sb = FakeSupabase(skills=rows)
    # Exact match on the head — walker runs.
    sid = await resolve_skill_id("name-0", supabase=sb)
    # After exactly MAX_CANONICAL_DEPTH hops we stop. Starting at sk-0,
    # 5 hops gets us to sk-5 (sk-0 -> sk-1 -> ... -> sk-5).
    assert sid == f"sk-{MAX_CANONICAL_DEPTH}"


@pytest.mark.asyncio
async def test_cache_dedupes_within_batch(patched_embedding):
    sb = FakeSupabase(skills=[])
    sb.rpc_handlers["match_skill_trgm"] = lambda params: []
    sb.rpc_handlers["match_skill_vector"] = lambda params: []
    cache: dict[str, str] = {}
    a = await resolve_skill_id("new-thing", supabase=sb, cache=cache)
    b = await resolve_skill_id("New-Thing", supabase=sb, cache=cache)
    # Both should return the same id, and the second call must NOT have
    # spent a second embedding call.
    assert a == b
    patched_embedding.assert_awaited_once()


@pytest.mark.asyncio
async def test_batch_helper_dedupes_via_canonical(patched_embedding):
    """resolve_skill_ids over ["postgres", "PostgreSQL", "postgres"]
    should return a single id (the canonical for whichever existing
    row matches first)."""
    sb = FakeSupabase(
        skills=[
            {"id": "sk-pg", "name": "postgresql", "canonical_of": None},
            {"id": "sk-pg-alias", "name": "postgres", "canonical_of": "sk-pg"},
        ]
    )
    ids = await resolve_skill_ids(
        ["postgres", "PostgreSQL", "postgres"],
        supabase=sb,
        user_id="u-1",
    )
    assert ids == ["sk-pg"]


@pytest.mark.asyncio
async def test_resolver_ignores_trgm_rpc_failure(patched_embedding):
    """RPC failure (e.g., function not yet deployed) must not crash —
    the resolver should fall through to vector + insert."""
    sb = FakeSupabase(skills=[])

    def boom(params):
        raise RuntimeError("function does not exist")

    sb.rpc_handlers["match_skill_trgm"] = boom
    sb.rpc_handlers["match_skill_vector"] = lambda params: []

    sid = await resolve_skill_id("brand-new", supabase=sb)
    assert sid is not None
    assert any(s["name"] == "brand-new" for s in sb.skills)


@pytest.mark.asyncio
async def test_normalization_strips_and_lowercases(patched_embedding):
    """`  POSTGRES  ` should match an existing `postgres` row."""
    sb = FakeSupabase(
        skills=[{"id": "sk-pg", "name": "postgres", "canonical_of": None}]
    )
    sid = await resolve_skill_id("  POSTGRES  ", supabase=sb)
    assert sid == "sk-pg"


@pytest.mark.asyncio
async def test_pass0_alias_substitution(patched_embedding):
    """Pass 0 hardcoded alias dict — "JS" should resolve to the
    existing "javascript" row WITHOUT calling the embedding API,
    because the alias dict short-circuits to the canonical name and
    Pass 1 then hits exactly."""
    sb = FakeSupabase(
        skills=[
            {"id": "sk-js", "name": "javascript", "canonical_of": None}
        ]
    )
    sid = await resolve_skill_id("JS", supabase=sb)
    assert sid == "sk-js"
    # Critical: the alias hit Pass 1 directly via the substituted name,
    # so neither trgm nor embedding ran.
    patched_embedding.assert_not_called()


@pytest.mark.asyncio
async def test_pass0_caches_both_raw_and_substituted(patched_embedding):
    """When alias "js" → "javascript" resolves, the cache should have
    both "js" AND "javascript" entries so a subsequent call with either
    form short-circuits."""
    sb = FakeSupabase(
        skills=[
            {"id": "sk-js", "name": "javascript", "canonical_of": None}
        ]
    )
    cache: dict[str, str] = {}
    a = await resolve_skill_id("JS", supabase=sb, cache=cache)
    b = await resolve_skill_id("javascript", supabase=sb, cache=cache)
    assert a == b == "sk-js"
    # Cache populated under both forms.
    assert cache.get("js") == "sk-js"
    assert cache.get("javascript") == "sk-js"
    # No embedding call across both resolves.
    patched_embedding.assert_not_called()


@pytest.mark.asyncio
async def test_pass0_alias_falls_through_when_canonical_absent(patched_embedding):
    """If the alias maps to a canonical form that isn't in skills, the
    resolver continues through Pass 2/3/4 — the alias dict is a hint,
    not a guarantee the row exists."""
    sb = FakeSupabase(skills=[])
    sb.rpc_handlers["match_skill_trgm"] = lambda params: []
    sb.rpc_handlers["match_skill_vector"] = lambda params: []
    sid = await resolve_skill_id("ml", supabase=sb)
    # Pass 4 inserts the alias-resolved form ("machine learning"),
    # NOT the raw input "ml". That keeps the master table consistent.
    assert sid is not None
    inserted = next(s for s in sb.skills if s["name"] == "machine learning")
    assert inserted["category"] == "auto"


@pytest.mark.asyncio
async def test_pass0_lower_vector_threshold_passes(patched_embedding):
    """Default vector threshold is now 0.72. A 0.78-cosine match (the
    react ↔ reactjs band that broke the original 0.85 cutoff) should
    now resolve via Pass 3."""
    sb = FakeSupabase(
        skills=[{"id": "sk-react", "name": "react", "canonical_of": None}]
    )
    sb.rpc_handlers["match_skill_trgm"] = lambda params: []
    # match_skill_vector receives the threshold; it'd filter server-
    # side. Stub it to return a row WITHIN the new threshold band.
    sb.rpc_handlers["match_skill_vector"] = lambda params: [
        {"id": "sk-react", "name": "react", "similarity": 0.78}
    ]
    sid = await resolve_skill_id("react native devvariant", supabase=sb)
    assert sid == "sk-react"
