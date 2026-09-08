from __future__ import annotations

from datetime import datetime

from app.services.clock import ensure_tz, now
from app.services.extraction import parse_explicit_datetime


def test_frozen_clock() -> None:
    value = now()
    assert value.year == 2026
    assert value.month == 9
    assert value.day == 5


def test_naive_datetime_gets_timezone() -> None:
    naive = datetime(2026, 9, 18, 16, 0, 0)
    aware = ensure_tz(naive)
    assert aware.tzinfo is not None


def test_parse_human_date() -> None:
    parsed = parse_explicit_datetime("18 September 2026 at 16:00")
    assert parsed is not None
    assert parsed.day == 18
