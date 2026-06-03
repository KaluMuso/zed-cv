"""Tests for review queue auto-dismiss eligibility and admin endpoint."""
from __future__ import annotations

from datetime import date

from app.services.review_queue_cleanup import (
    AUTO_DISMISS_REVIEW_REASONS,
    JUNK_DEACTIVATION_MARKERS,
    build_hidden_inactive_dismiss_patch,
    build_review_dismiss_patch,
    matches_expired_review_dismiss,
    matches_hidden_inactive_dismiss,
    matches_junk_review_dismiss,
)


class TestMatchesHiddenInactiveDismiss:
    def test_eligible_both_inactive(self):
        assert matches_hidden_inactive_dismiss(
            {
                "is_review_required": True,
                "admin_reviewed_at": None,
                "is_active": False,
                "review_reason": "both",
            }
        )

    def test_rejects_no_deadline(self):
        assert not matches_hidden_inactive_dismiss(
            {
                "is_review_required": True,
                "admin_reviewed_at": None,
                "is_active": False,
                "review_reason": "no_deadline",
            }
        )

    def test_rejects_still_active(self):
        assert not matches_hidden_inactive_dismiss(
            {
                "is_review_required": True,
                "admin_reviewed_at": None,
                "is_active": True,
                "review_reason": "both",
            }
        )

    def test_idempotent_already_reviewed(self):
        assert not matches_hidden_inactive_dismiss(
            {
                "is_review_required": False,
                "admin_reviewed_at": "2026-01-01T00:00:00Z",
                "is_active": False,
                "review_reason": "both",
            }
        )


class TestBuildPatch:
    def test_sets_auto_dismissed_reason(self):
        patch = build_hidden_inactive_dismiss_patch()
        assert patch["review_reason"] == "auto_dismissed_hidden"
        assert patch["is_review_required"] is False
        assert patch["admin_review_reason"] is None


class TestAutoDismissReasons:
    def test_reasons_frozen(self):
        assert AUTO_DISMISS_REVIEW_REASONS == frozenset({"both", "no_apply_path"})


class TestExpiredDismiss:
    def test_eligible_past_closing(self):
        assert matches_expired_review_dismiss(
            {
                "is_review_required": True,
                "admin_reviewed_at": None,
                "closing_date": "2020-01-01",
            },
            today=date(2026, 6, 3),
        )

    def test_rejects_future_closing(self):
        assert not matches_expired_review_dismiss(
            {
                "is_review_required": True,
                "admin_reviewed_at": None,
                "closing_date": "2030-01-01",
            },
            today=date(2026, 6, 3),
        )


class TestJunkDismiss:
    def test_eligible_thin_description(self):
        assert matches_junk_review_dismiss(
            {
                "is_review_required": True,
                "admin_reviewed_at": None,
                "is_active": False,
                "deactivation_reason": "thin_description",
            }
        )

    def test_rejects_active_junk(self):
        assert not matches_junk_review_dismiss(
            {
                "is_review_required": True,
                "admin_reviewed_at": None,
                "is_active": True,
                "deactivation_reason": "thin_description",
            }
        )


class TestJunkMarkers:
    def test_markers_include_source_issues(self):
        assert "missing_source_url" in JUNK_DEACTIVATION_MARKERS


class TestReviewDismissPatch:
    def test_custom_reason(self):
        patch = build_review_dismiss_patch(review_reason="auto_dismissed_expired")
        assert patch["review_reason"] == "auto_dismissed_expired"
