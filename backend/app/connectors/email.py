"""Selected / forwarded email fixture connector."""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from app.connectors.base import healthy, unavailable
from app.domain.enums import PermissionState, SourceAuthority, SourceType
from app.domain.schemas import ConnectorHealth, SourceObservationIn
from app.policies.injection import find_injection_sentences
from app.services import clock
from app.settings import get_settings


class EmailConnector:
    source_type = SourceType.EMAIL
    label = "Forwarded student mail (synthetic)"

    def __init__(self, fixtures: Path | None = None, permission_revoked: bool = False) -> None:
        self._root = fixtures or get_settings().fixtures_root / "email"
        self._permission_revoked = permission_revoked
        self._last_success: datetime | None = None

    def revoke(self) -> None:
        self._permission_revoked = True

    async def health_check(self) -> ConnectorHealth:
        if self._permission_revoked:
            return unavailable(
                self.source_type,
                self.label,
                error_code="email_permission_revoked",
                error_message="Mailbox consent revoked. No new mail is read.",
                last_success=self._last_success,
                degraded_mode="read_stopped",
            )
        health = healthy(self.source_type, self.label, self._last_success or clock.now())
        health.permission_state = PermissionState.GRANTED
        return health

    async def fetch_observations(
        self, user_id: str, since: datetime | None = None
    ) -> list[SourceObservationIn]:
        del user_id
        if self._permission_revoked:
            return []
        items: list[SourceObservationIn] = []
        for path in sorted(self._root.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            observed = datetime.fromisoformat(payload["observed_at"])
            if since is not None and observed <= since:
                continue
            body = payload.get("body", "")
            injection = find_injection_sentences(body)
            excerpt = f"{payload.get('subject', '')} — {body[:180]}"
            digest = sha256(path.read_bytes()).hexdigest()
            items.append(
                SourceObservationIn(
                    source_type=SourceType.EMAIL,
                    source_reference=payload["source_reference"],
                    source_authority=SourceAuthority.SECONDARY,
                    observed_at=observed,
                    excerpt=excerpt,
                    payload={
                        "from": payload.get("from"),
                        "subject": payload.get("subject"),
                        "body": body,
                    },
                    content_digest=digest,
                    injection_flagged=bool(injection),
                )
            )
        self._last_success = clock.now()
        return items
