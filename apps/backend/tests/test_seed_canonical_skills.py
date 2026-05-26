"""Tests for canonical_skills seeding from job/user skill frequency."""
from __future__ import annotations

from collections import Counter
from unittest.mock import MagicMock

import pytest

from app.services.canonical_skills_curated_list import CURATED_ZAMBIA_SKILLS_RAW
from app.services.canonical_skills_seed import (
    CanonicalSeedRow,
    build_seed_row_from_raw,
    collect_raw_skill_counts,
    curated_seed_rows,
    raw_to_canonical_display,
    rows_from_top_raw,
    seed_canonical_skills,
)


class TestCanonicalDisplay:
    def test_excel_alias_and_parent(self):
        row = build_seed_row_from_raw("ms excel")
        assert row is not None
        assert row.name == "Microsoft Excel"
        assert row.parent_skill == "Microsoft Office"
        assert row.notes is None

    def test_ifrs_acronym_and_notes(self):
        row = build_seed_row_from_raw("ifrs")
        assert row is not None
        assert row.name == "IFRS"
        assert row.notes == "Financial reporting standards"

    def test_python_standalone(self):
        assert raw_to_canonical_display("Python") == "Python"


class TestHarvest:
    def test_collect_from_jobs_and_user_skills(self):
        supabase = MagicMock()
        jobs_data = [
            {"requirements": ["ms excel", "IFRS"]},
            {"requirements": ["excel", "communication"]},
        ]
        user_skills_data = [
            {"skills": {"name": "python"}},
            {"skills": {"name": "excel"}},
        ]
        call_idx = {"n": 0}

        def table(name: str):
            q = MagicMock()

            def range_(start: int, end: int):
                q._range = (start, end)
                return q

            def select(*_a, **_kw):
                return q

            def execute():
                if name == "jobs":
                    if call_idx["n"] == 0:
                        call_idx["n"] += 1
                        return MagicMock(data=jobs_data)
                    return MagicMock(data=[])
                if name == "user_skills":
                    return MagicMock(data=user_skills_data if q._range[0] == 0 else [])
                return MagicMock(data=[])

            q.select = select
            q.range = range_
            q.execute = execute
            return q

        supabase.table = table
        counts = collect_raw_skill_counts(supabase)
        assert counts["microsoft excel"] >= 2 or counts["excel"] >= 2
        assert counts["ifrs"] == 1
        assert counts["python"] == 1


class TestSeedRows:
    def test_top_raw_dedupes_canonical_names(self):
        counts = Counter(
            {
                "excel": 10,
                "ms excel": 8,
                "ifrs": 5,
                "python": 3,
            }
        )
        rows = rows_from_top_raw(counts, limit=10)
        names = [r.name for r in rows]
        assert "Microsoft Excel" in names
        assert names.count("Microsoft Excel") == 1

    def test_curated_seed_has_full_list(self):
        rows = curated_seed_rows()
        assert len(rows) >= 190
        assert len(rows) <= len(CURATED_ZAMBIA_SKILLS_RAW)
        assert all(isinstance(r, CanonicalSeedRow) for r in rows)


class TestSeedInsert:
    def test_table_non_empty_after_seeding(self):
        """Regression: seed path must populate canonical_skills when empty."""
        store: list[dict] = []
        supabase = MagicMock()

        def table(name: str):
            q = MagicMock()
            if name in ("jobs", "user_skills"):
                q.select.return_value = q
                q.range.return_value = q
                q.execute.return_value = MagicMock(data=[])
            elif name == "canonical_skills":
                q._mode = "select"

                def insert(payload):
                    q._mode = "insert"
                    q._payload = payload
                    return q

                def execute():
                    if q._mode == "insert" and hasattr(q, "_payload"):
                        row = dict(q._payload)
                        row["id"] = "new-id"
                        store.append(row)
                        q._mode = "select"
                        return MagicMock(data=[row])
                    return MagicMock(data=[])

                q.select.return_value = q
                q.eq.return_value = q
                q.limit.return_value = q
                q.insert = insert
                q.execute = execute
            return q

        supabase.table = table
        inserted = seed_canonical_skills(supabase, dry_run=False)
        assert len(store) >= 1
        assert len(inserted) >= 1
