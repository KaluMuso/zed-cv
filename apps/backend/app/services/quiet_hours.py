"""User quiet-hours window checks for outbound WhatsApp notifications."""
from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "Africa/Lusaka"
DEFAULT_QUIET_START = time(20, 0)
DEFAULT_QUIET_END = time(7, 0)


def _parse_time_value(raw: Any, fallback: time) -> time:
    if raw is None:
        return fallback
    text = str(raw).strip()
    if not text:
        return fallback
    if len(text) >= 5 and text[2] == ":":
        try:
            hour, minute = int(text[0:2]), int(text[3:5])
            return time(hour, minute)
        except ValueError:
            return fallback
    return fallback


def _resolve_zone(tz_name: str | None) -> ZoneInfo:
    name = (tz_name or "").strip() or DEFAULT_TIMEZONE
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)


def is_in_quiet_hours(
    now: datetime,
    *,
    quiet_start: time,
    quiet_end: time,
    tz_name: str | None = None,
) -> bool:
    """
    Return True when local time falls inside the quiet window.

    Supports overnight windows (e.g. 20:00–07:00) when start > end.
    """
    local = now.astimezone(_resolve_zone(tz_name))
    current = local.time().replace(second=0, microsecond=0)
    if quiet_start == quiet_end:
        return False
    if quiet_start < quiet_end:
        return quiet_start <= current < quiet_end
    return current >= quiet_start or current < quiet_end


def user_in_quiet_hours(user: dict[str, Any], now: datetime) -> bool:
    """Read quiet-hours fields from a users row."""
    start = _parse_time_value(user.get("quiet_hours_start"), DEFAULT_QUIET_START)
    end = _parse_time_value(user.get("quiet_hours_end"), DEFAULT_QUIET_END)
    return is_in_quiet_hours(
        now,
        quiet_start=start,
        quiet_end=end,
        tz_name=user.get("display_timezone"),
    )
