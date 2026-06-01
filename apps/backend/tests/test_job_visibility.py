"""Unit tests for job feed visibility (migration 095)."""
from datetime import date, timedelta

from app.services.job_visibility import (
    compute_visibility_status,
    include_in_default_feed,
    visibility_from_row,
)


class TestComputeVisibilityStatus:
    def test_open_active_no_deadline(self):
        assert compute_visibility_status(is_active=True, closing_date=None) == "open"

    def test_open_future_deadline(self):
        future = date.today() + timedelta(days=7)
        assert compute_visibility_status(is_active=True, closing_date=future) == "open"

    def test_recently_closed_within_grace(self):
        yesterday = date.today() - timedelta(days=1)
        assert (
            compute_visibility_status(is_active=False, closing_date=yesterday)
            == "recently_closed"
        )

    def test_archived_after_grace(self):
        old = date.today() - timedelta(days=10)
        assert compute_visibility_status(is_active=True, closing_date=old) == "archived"


class TestIncludeInDefaultFeed:
    def test_archived_hidden_by_default(self):
        row = {"is_active": True, "closing_date": (date.today() - timedelta(days=10)).isoformat()}
        assert include_in_default_feed(row, include_archived=False) is False

    def test_recently_closed_visible_by_default(self):
        row = {"is_active": False, "closing_date": (date.today() - timedelta(days=1)).isoformat()}
        assert include_in_default_feed(row, include_archived=False) is True

    def test_archived_visible_when_flag(self):
        row = {"visibility_status": "archived"}
        assert include_in_default_feed(row, include_archived=True) is True

    def test_visibility_from_view_column(self):
        row = {"visibility_status": "open", "closing_date": None}
        assert visibility_from_row(row) == "open"
