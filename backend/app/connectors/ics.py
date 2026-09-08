"""ICS calendar connector (read-only)."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar

from app.connectors.base import healthy
from app.domain.enums import SourceAuthority, SourceType
from app.domain.schemas import ConnectorHealth, SourceObservationIn
from app.services import clock
from app.settings import get_settings


def _as_aware(value: datetime, fallback: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=fallback)
    return value


class IcsConnector:
    source_type = SourceType.CALENDAR
    label = "Student ICS calendar (synthetic)"

    def __init__(self, path: Path | None = None) -> None:
        settings = get_settings()
        self._path = path or settings.fixtures_root / "calendar" / "student.ics"
        self._last_success: datetime | None = None
        self._tz = settings.tz

    async def health_check(self) -> ConnectorHealth:
        return healthy(self.source_type, self.label, self._last_success or clock.now())

    async def fetch_observations(
        self, user_id: str, since: datetime | None = None
    ) -> list[SourceObservationIn]:
        del user_id, since
        raw = self._path.read_bytes()
        calendar = Calendar.from_ical(raw)
        events: list[dict[str, str]] = []
        for component in calendar.walk("VEVENT"):
            start = _as_aware(component.decoded("DTSTART"), self._tz)
            end = _as_aware(component.decoded("DTEND"), self._tz)
            events.append(
                {
                    "uid": str(component.get("UID")),
                    "title": str(component.get("SUMMARY")),
                    "start_at": start.isoformat(),
                    "end_at": end.isoformat(),
                    "location": str(component.get("LOCATION", "")),
                }
            )
        digest = sha256(raw).hexdigest()
        observation = SourceObservationIn(
            source_type=SourceType.CALENDAR,
            source_reference="fixtures/calendar/student.ics",
            source_authority=SourceAuthority.PRIMARY,
            observed_at=clock.now(),
            excerpt=f"{len(events)} fixed calendar events.",
            payload={"events": events},
            content_digest=digest,
        )
        self._last_success = clock.now()
        return [observation]
