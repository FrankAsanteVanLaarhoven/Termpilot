"""Timezone-aware clock with a frozen demo override."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.settings import get_settings


def tz() -> ZoneInfo:
    return get_settings().tz


def now() -> datetime:
    settings = get_settings()
    if settings.frozen_now is not None:
        value = settings.frozen_now
        if value.tzinfo is None:
            return value.replace(tzinfo=tz())
        return value.astimezone(tz())
    return datetime.now(tz())


def horizon_end(start: datetime | None = None) -> datetime:
    start = start or now()
    days = get_settings().plan_horizon_days
    return (start + timedelta(days=days)).replace(hour=23, minute=59, second=59, microsecond=0)


def ensure_tz(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=tz())
    return value.astimezone(tz())
