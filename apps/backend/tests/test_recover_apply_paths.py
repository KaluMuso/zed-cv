"""Unit tests for recover_apply_paths backfill script."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts import recover_apply_paths


class TestLoadCandidates:
    def test_dedupes_pending_and_legacy(self):
        supabase = MagicMock()
        pending = [{"id": "a", "source_url": "https://x.com/1"}]
        legacy = [{"id": "b", "source_url": "https://x.com/2"}]

        with (
            patch.object(
                recover_apply_paths,
                "_fetch_pending_enrich",
                return_value=pending,
            ),
            patch.object(
                recover_apply_paths,
                "_fetch_legacy_active_recoverable_broad",
                return_value=legacy,
            ),
        ):
            out = recover_apply_paths.load_candidates(supabase)

        assert len(out) == 2
        assert {r["id"] for r in out} == {"a", "b"}


class TestProcessJob:
    @pytest.mark.asyncio
    async def test_apply_recovers_when_enrich_succeeds(self):
        supabase = MagicMock()
        before = {
            "id": "job-1",
            "title": "Driver",
            "source_url": "https://employer.com/post",
            "apply_url": "https://www.jobwebzambia.com/job/1",
            "apply_email": None,
            "contact_phone": None,
        }
        after = {
            **before,
            "apply_url": "https://employer.com/apply",
            "apply_email": "hr@employer.com",
        }

        with (
            patch.object(
                recover_apply_paths,
                "enrich_job_deep",
                new_callable=AsyncMock,
                return_value="enriched",
            ),
            patch.object(
                recover_apply_paths,
                "_refetch_job",
                return_value=after,
            ),
            patch.object(recover_apply_paths, "_log_outcome"),
        ):
            bucket = await recover_apply_paths.process_job(
                supabase, before, dry_run=False
            )

        assert bucket == "recovered"
        update_call = supabase.table.return_value.update.return_value.eq.return_value
        update_call.execute.assert_called()
        payload = supabase.table.return_value.update.call_args[0][0]
        assert payload["is_active"] is True
        assert payload["deactivation_reason"] is None

    @pytest.mark.asyncio
    async def test_apply_deactivates_when_still_invalid(self):
        supabase = MagicMock()
        row = {
            "id": "job-2",
            "title": "Clerk",
            "source_url": "https://employer.com/post",
            "apply_url": "https://www.jobwebzambia.com/job/2",
        }
        still_bad = dict(row)

        with (
            patch.object(
                recover_apply_paths,
                "enrich_job_deep",
                new_callable=AsyncMock,
                return_value="enriched",
            ),
            patch.object(
                recover_apply_paths,
                "_refetch_job",
                return_value=still_bad,
            ),
            patch.object(recover_apply_paths, "_log_outcome"),
        ):
            bucket = await recover_apply_paths.process_job(
                supabase, row, dry_run=False
            )

        assert bucket == "deactivated"
        payload = supabase.table.return_value.update.call_args[0][0]
        assert payload["deactivation_reason"] == "no_valid_apply_path_after_enrich"

    @pytest.mark.asyncio
    async def test_fetch_failed_on_enrich_failure(self):
        supabase = MagicMock()
        row = {"id": "job-3", "title": "T", "source_url": "https://x.com"}

        with (
            patch.object(
                recover_apply_paths,
                "enrich_job_deep",
                new_callable=AsyncMock,
                return_value="failed",
            ),
            patch.object(
                recover_apply_paths,
                "_refetch_job",
                return_value=row,
            ),
            patch.object(recover_apply_paths, "_log_outcome"),
        ):
            bucket = await recover_apply_paths.process_job(
                supabase, row, dry_run=False
            )

        assert bucket == "fetch_failed"
