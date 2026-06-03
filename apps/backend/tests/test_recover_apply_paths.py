"""Unit tests for recover_apply_paths backfill script."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts import recover_apply_paths


class TestLoadCandidates:
    def test_dedupes_pending_legacy_and_after_enrich(self):
        supabase = MagicMock()
        pending = [{"id": "a", "source_url": "https://x.com/1"}]
        after_fail = [{"id": "c", "source_url": "https://x.com/3"}]
        stale = [{"id": "d", "source_url": "https://x.com/4"}]
        legacy = [{"id": "b", "source_url": "https://x.com/2"}]

        with (
            patch.object(
                recover_apply_paths,
                "_fetch_pending_enrich",
                return_value=pending,
            ),
            patch.object(
                recover_apply_paths,
                "_fetch_after_enrich_failures",
                return_value=after_fail,
            ),
            patch.object(
                recover_apply_paths,
                "_fetch_stale_inactive_with_valid_path",
                return_value=stale,
            ),
            patch.object(
                recover_apply_paths,
                "_fetch_legacy_active_recoverable_broad",
                return_value=legacy,
            ),
        ):
            out = recover_apply_paths.load_candidates(supabase)

        assert len(out) == 4
        assert {r["id"] for r in out} == {"a", "b", "c", "d"}


class TestStaleReconcile:
    @pytest.mark.asyncio
    async def test_reactivates_when_email_already_valid(self):
        supabase = MagicMock()
        row = {
            "id": "8473a9bd-57be-4cd8-90c4-d6b3db27d4cf",
            "title": "HR Officer",
            "source_url": "https://www.jobwebzambia.com/jobs/hr-officer/",
            "apply_url": "https://www.jobwebzambia.com/jobs/hr-officer/",
            "apply_email": "careers@karibaharvest.com",
            "contact_phone": None,
            "is_active": False,
            "deactivation_reason": "no_valid_apply_path_after_enrich",
        }

        with (
            patch.object(
                recover_apply_paths,
                "enrich_job_deep",
                new_callable=AsyncMock,
            ) as mock_enrich,
            patch.object(recover_apply_paths, "_log_outcome"),
        ):
            bucket = await recover_apply_paths.process_job(
                supabase, row, dry_run=False
            )

        assert bucket == "recovered"
        mock_enrich.assert_not_called()
        payload = supabase.table.return_value.update.call_args[0][0]
        assert payload["is_active"] is True
        assert payload["deactivation_reason"] is None


class TestParserRecovery:
    @pytest.mark.asyncio
    async def test_parser_recovery_skips_llm(self):
        supabase = MagicMock()
        row = {
            "id": "job-p",
            "title": "Clerk",
            "source_url": "https://www.jobwebzambia.com/jobs/clerk-1",
            "apply_url": "https://www.jobwebzambia.com/jobs/clerk-1",
        }
        recovery_patch = {
            **row,
            "apply_email": "hr@company.co.zm",
            "contact_phone": "+260971234567",
        }

        with (
            patch.object(
                recover_apply_paths,
                "_try_parser_recovery",
                new_callable=AsyncMock,
                return_value=recovery_patch,
            ),
            patch.object(
                recover_apply_paths,
                "enrich_job_deep",
                new_callable=AsyncMock,
            ) as mock_enrich,
            patch.object(
                recover_apply_paths,
                "_apply_recovery_patch",
                return_value="recovered",
            ),
        ):
            bucket = await recover_apply_paths.process_job(
                supabase, row, dry_run=False
            )

        assert bucket == "recovered"
        mock_enrich.assert_not_called()


class TestProcessJob:
    @pytest.mark.asyncio
    async def test_split_parent_not_overwritten_with_after_enrich(self):
        supabase = MagicMock()
        parent = {
            "id": "parent-1",
            "title": "Head Chef & Sous Chef",
            "source_url": "https://www.jobwebzambia.com/jobs/combo/",
            "apply_url": "https://www.jobwebzambia.com/jobs/combo/",
            "is_active": False,
            "deactivation_reason": "no_valid_apply_path_after_enrich",
        }
        after_split = {
            **parent,
            "deactivation_reason": "split_into_children",
        }

        with (
            patch.object(
                recover_apply_paths,
                "_try_parser_recovery",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                recover_apply_paths,
                "enrich_job_deep",
                new_callable=AsyncMock,
                return_value="split",
            ),
            patch.object(
                recover_apply_paths,
                "_refetch_job",
                return_value=after_split,
            ),
            patch.object(recover_apply_paths, "_log_outcome"),
        ):
            bucket = await recover_apply_paths.process_job(
                supabase, parent, dry_run=False
            )

        assert bucket == "recovered"
        supabase.table.return_value.update.assert_not_called()

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
                "_try_parser_recovery",
                new_callable=AsyncMock,
                return_value=None,
            ),
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
                "_try_parser_recovery",
                new_callable=AsyncMock,
                return_value=None,
            ),
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
                "_try_parser_recovery",
                new_callable=AsyncMock,
                return_value=None,
            ),
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
