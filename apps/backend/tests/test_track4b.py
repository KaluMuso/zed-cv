"""Track 4b coverage: job eligibility, match crediting, and cron."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class MemoryQuery:
    def __init__(self, db, table: str):
        self.db = db
        self.table = table
        self.filters: list[tuple[str, str, object]] = []
        self._count = False
        self._single = False
        self._limit: int | None = None
        self._order: tuple[str, bool] | None = None
        self._negate_next = False
        self._update: dict | None = None

    def select(self, *_args, **kwargs):
        self._count = kwargs.get("count") == "exact"
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def neq(self, column, value):
        self.filters.append(("neq", column, value))
        return self

    def gte(self, column, value):
        self.filters.append(("gte", column, value))
        return self

    def in_(self, column, values):
        self.filters.append(("in", column, set(values)))
        return self

    def is_(self, column, value):
        op = "not_null" if self._negate_next else "is_null"
        self._negate_next = False
        self.filters.append((op, column, value))
        return self

    @property
    def not_(self):
        self._negate_next = True
        return self

    def single(self):
        self._single = True
        return self

    def limit(self, value):
        self._limit = value
        return self

    def order(self, column, desc=False):
        self._order = (column, desc)
        return self

    def range(self, *_args):
        return self

    def insert(self, payload):
        rows = payload if isinstance(payload, list) else [payload]
        inserted = []
        for row in rows:
            new_row = dict(row)
            new_row.setdefault("id", f"{self.table}-{len(self.db.rows(self.table)) + 1}")
            self.db.rows(self.table).append(new_row)
            inserted.append(new_row)
        return StaticQuery(inserted)

    def upsert(self, payload, **_kwargs):
        rows = payload if isinstance(payload, list) else [payload]
        out = []
        table_rows = self.db.rows(self.table)
        for row in rows:
            existing = next(
                (
                    item
                    for item in table_rows
                    if item.get("user_id") == row.get("user_id")
                    and item.get("job_id") == row.get("job_id")
                ),
                None,
            )
            if existing:
                existing.update(row)
                out.append(existing)
            else:
                new_row = dict(row)
                new_row.setdefault("id", f"{self.table}-{len(table_rows) + 1}")
                table_rows.append(new_row)
                out.append(new_row)
        return StaticQuery(out)

    def update(self, payload):
        self._update = payload
        return self

    def _matches(self, row):
        for op, column, value in self.filters:
            cell = row.get(column)
            if op == "eq" and cell != value:
                return False
            if op == "neq" and cell == value:
                return False
            if op == "in" and cell not in value:
                return False
            if op == "is_null" and cell is not None:
                return False
            if op == "not_null" and cell is None:
                return False
            if op == "gte" and (cell is None or str(cell) < str(value)):
                return False
        return True

    def execute(self):
        rows = [row for row in self.db.rows(self.table) if self._matches(row)]
        if self._update is not None:
            for row in rows:
                row.update(self._update)
        if self._order:
            column, desc = self._order
            rows = sorted(rows, key=lambda row: row.get(column) or "", reverse=desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        result = MagicMock()
        result.data = (rows[0] if self._single and rows else rows)
        result.count = len(rows) if self._count else None
        return result


class StaticQuery:
    def __init__(self, data):
        self.data = data

    def execute(self):
        result = MagicMock()
        result.data = self.data
        result.count = len(self.data) if isinstance(self.data, list) else None
        return result


class MemorySupabase:
    def __init__(self, tables=None):
        self.tables = tables or {}

    def rows(self, table):
        return self.tables.setdefault(table, [])

    def table(self, table):
        return MemoryQuery(self, table)


def _job(**overrides):
    from app.schemas.jobs import JobCreate, JobSource

    data = {
        "title": "Accounts Officer at TEVETA",
        "company": "TEVETA",
        "description": "Manage accounting records and monthly reporting for the finance team.",
        "source": JobSource.scraper,
        "source_url": "https://careers.teveta.org.zm/jobs/accounts-officer",
        "closing_date": "2026-06-30",
    }
    data.update(overrides)
    return JobCreate(**data)


@pytest.mark.parametrize(
    ("job", "active"),
    [
        (_job(apply_url="https://company.test/apply", apply_email="hr@test.com", application_instructions="Call +260971234567"), True),
        (_job(apply_url="https://company.test/apply", apply_email="hr@test.com"), True),
        (_job(application_instructions="Email careers@test.com"), False),
        (_job(closing_date=None), False),
    ],
)
def test_ingest_sets_listing_eligibility(job, active):
    from app.api.v1.jobs import _ingest_one_job
    from app.services.job_enricher import JobEnrichment

    supabase = MemorySupabase()
    with patch("app.api.v1.jobs.generate_embedding", new=AsyncMock(return_value=[0.1] * 768)), patch(
        "app.api.v1.jobs.enrich_job",
        new=AsyncMock(return_value=JobEnrichment()),
    ), patch("app.api.v1.jobs.apply_job_enrichment", new=AsyncMock()):
        status, detail = asyncio.run(_ingest_one_job(supabase, job, []))

    assert (status, detail) == ("ingested", "")
    inserted = supabase.rows("jobs")[0]
    assert inserted["is_active"] is active
    if active:
        assert inserted["admin_review_reason"] is None
        assert supabase.rows("analytics_events") == []
    elif job.closing_date is None:
        assert inserted["admin_review_reason"] == "missing_apply_link,missing_contact,missing_deadline"
        assert supabase.rows("analytics_events")[0]["event"] == "job_eligibility_flagged"
    else:
        # Instructions-only contact no longer activates public listings.
        assert inserted.get("admin_review_reason") is None
        assert supabase.rows("analytics_events") == []


def test_match_crediting_unique_pairs_and_new_only():
    from app.services.matching import credit_matches_for_cycle, store_matches

    supabase = MemorySupabase(
        {"subscriptions": [{"user_id": "u1", "tier": "starter", "status": "active"}]}
    )
    first = [{"job_id": "j1", "final_score": 88, "vector_score": 80, "skill_score": 90, "bonus_score": 5},
             {"job_id": "j2", "final_score": 82, "vector_score": 78, "skill_score": 86, "bonus_score": 4}]
    asyncio.run(store_matches("u1", "cv1", first, supabase))
    assert asyncio.run(credit_matches_for_cycle("u1", ["j1", "j2"], supabase)) == [
        "j1",
        "j2",
    ]
    assert asyncio.run(credit_matches_for_cycle("u1", ["j1", "j2"], supabase)) == []

    third = [{"job_id": "j2", "final_score": 82, "vector_score": 78, "skill_score": 86, "bonus_score": 4},
             {"job_id": "j3", "final_score": 80, "vector_score": 76, "skill_score": 84, "bonus_score": 4}]
    asyncio.run(store_matches("u1", "cv1", third, supabase))
    assert asyncio.run(credit_matches_for_cycle("u1", ["j2", "j3"], supabase)) == ["j3"]


def test_tier_quota_inserts_but_does_not_credit_after_cap():
    from app.services import tier_config as tier_config_svc
    from app.services.matching import (
        credit_matches_for_cycle,
        get_credited_match_count,
        get_user_tier_limit,
        store_matches,
    )

    tier_config_svc.clear_tier_config_cache()
    now = datetime.now(timezone.utc).replace(day=2)
    # Free tier quota is 3; rows need active status to count toward delivery usage.
    credited_rows = [
        {
            "id": f"m{i}",
            "user_id": "u1",
            "job_id": f"old-{i}",
            "credited_at": now.isoformat(),
            "status": "new",
        }
        for i in range(3)
    ]
    supabase = MemorySupabase(
        {
            "matches": list(credited_rows),
            "subscriptions": [{"user_id": "u1", "tier": "free", "status": "active"}],
            "users": [
                {
                    "id": "u1",
                    "subscription_tier": "free",
                    "welcome_match_bonus": None,
                    "welcome_match_bonus_until": None,
                }
            ],
        }
    )
    _, quota, active = asyncio.run(get_user_tier_limit("u1", supabase))
    assert active is True
    assert quota == 3
    assert asyncio.run(get_credited_match_count("u1", supabase, now=now)) == quota

    asyncio.run(
        store_matches(
            "u1",
            "cv1",
            [
                {
                    "job_id": "new",
                    "final_score": 90,
                    "vector_score": 90,
                    "skill_score": 90,
                    "bonus_score": 0,
                }
            ],
            supabase,
        )
    )
    assert any(row["job_id"] == "new" for row in supabase.rows("matches"))
    assert asyncio.run(credit_matches_for_cycle("u1", ["new"], supabase, now=now)) == []
    assert (
        next(row for row in supabase.rows("matches") if row["job_id"] == "new").get(
            "credited_at"
        )
        is None
    )


def test_cron_tick_processes_eligible_users_idempotently():
    from app.api.v1 import matches as matches_module

    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    supabase = MemorySupabase(
        {
            "users": [
                {"id": "u1", "subscription_tier": "starter", "auto_match_enabled": True, "last_auto_match_at": None},
                {"id": "u2", "subscription_tier": "free", "auto_match_enabled": True, "last_auto_match_at": None},
                {"id": "u3", "subscription_tier": "starter", "auto_match_enabled": False, "last_auto_match_at": None},
                {"id": "u4", "subscription_tier": "starter", "auto_match_enabled": True, "last_auto_match_at": recent},
            ],
            "cvs": [{"id": "cv1", "user_id": "u1", "is_primary": True}],
            "subscriptions": [{"user_id": "u1", "tier": "starter", "status": "active"}],
        }
    )
    settings = SimpleNamespace(ingest_api_key="test-ingest-key")
    with patch.object(
        matches_module,
        "run_matching_for_user",
        new=AsyncMock(return_value=[{"job_id": "j1", "final_score": 90, "vector_score": 90, "skill_score": 90, "bonus_score": 0}]),
    ), patch.object(matches_module, "_send_due_digest", new=AsyncMock(return_value=False)):
        first = asyncio.run(matches_module.cron_tick(
            limit=100,
            ingest_api_key="test-ingest-key",
            x_ingest_api_key=None,
            supabase=supabase,
            settings=settings,
        ))
        second = asyncio.run(matches_module.cron_tick(
            limit=100,
            ingest_api_key="test-ingest-key",
            x_ingest_api_key=None,
            supabase=supabase,
            settings=settings,
        ))

    assert first.users_processed == 1
    assert first.new_matches_total == 1
    assert second.users_processed == 0
    assert second.new_matches_total == 0
