"""Synthetic LMS fixture connector."""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from app.connectors.base import SourceConnector, healthy, unavailable
from app.domain.enums import SourceAuthority, SourceType
from app.domain.schemas import ConnectorHealth, SourceObservationIn
from app.services import clock
from app.settings import get_settings


class LmsConnector:
    source_type = SourceType.LMS
    label = "Northbridge LMS (synthetic)"

    def __init__(self, fixtures: Path | None = None, outage: bool | None = None) -> None:
        settings = get_settings()
        self._root = fixtures or settings.fixtures_root / "lms"
        self._outage = settings.simulate_lms_outage if outage is None else outage
        self._last_success: datetime | None = None
        self._snapshot: list[SourceObservationIn] | None = None

    def set_outage(self, outage: bool) -> None:
        self._outage = outage

    async def health_check(self) -> ConnectorHealth:
        if self._outage:
            return unavailable(
                self.source_type,
                self.label,
                error_code="lms_unavailable",
                error_message="LMS unreachable. Using last snapshot if present.",
                last_success=self._last_success,
            )
        return healthy(self.source_type, self.label, self._last_success or clock.now())

    async def fetch_observations(
        self, user_id: str, since: datetime | None = None
    ) -> list[SourceObservationIn]:
        del user_id
        if self._outage:
            return list(self._snapshot or [])
        path = self._root / "modules.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        observed = datetime.fromisoformat(payload["observed_at"])
        if since is not None and observed <= since:
            return list(self._snapshot or [])
        html = (self._root / "course_page.html").read_text(encoding="utf-8")
        digest = sha256((path.read_text(encoding="utf-8") + html).encode()).hexdigest()
        observation = SourceObservationIn(
            source_type=SourceType.LMS,
            source_reference=payload["source_reference"],
            source_authority=SourceAuthority.PRIMARY,
            observed_at=observed,
            excerpt="CSC0000 and ENG0001 assignment list from synthetic LMS.",
            payload={"modules": payload["modules"], "html": html[:2000]},
            content_digest=digest,
        )
        self._last_success = clock.now()
        self._snapshot = [observation]
        return [observation]


def lms_connector() -> SourceConnector:
    return LmsConnector()
