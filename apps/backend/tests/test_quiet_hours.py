"""Quiet-hours window checks."""
from datetime import datetime, time, timezone

from app.services.quiet_hours import is_in_quiet_hours, user_in_quiet_hours


def test_overnight_quiet_hours_active_late_evening():
    now = datetime(2026, 5, 22, 21, 0, tzinfo=timezone.utc)
    assert is_in_quiet_hours(
        now,
        quiet_start=time(20, 0),
        quiet_end=time(7, 0),
        tz_name="Africa/Lusaka",
    )


def test_overnight_quiet_hours_inactive_midday():
    now = datetime(2026, 5, 22, 10, 0, tzinfo=timezone.utc)
    assert not is_in_quiet_hours(
        now,
        quiet_start=time(20, 0),
        quiet_end=time(7, 0),
        tz_name="Africa/Lusaka",
    )


def test_user_row_parses_time_strings():
    now = datetime(2026, 5, 22, 21, 0, tzinfo=timezone.utc)
    user = {
        "quiet_hours_start": "20:00:00",
        "quiet_hours_end": "07:00:00",
        "display_timezone": "Africa/Lusaka",
    }
    assert user_in_quiet_hours(user, now)
