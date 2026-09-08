"""Common connector protocol and health helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from app.domain.enums import HealthState, PermissionState, SourceType
from app.domain.schemas import ConnectorHealth, SourceObservationIn
from app.services import clock


@runtime_checkable
class SourceConnector(Protocol):
    source_type: SourceType
    label: str

    async def health_check(self) -> ConnectorHealth: ...

    async def fetch_observations(
        self, user_id: str, since: datetime | None = None
    ) -> list[SourceObservationIn]: ...


def stale(last_success: datetime | None, stale_after_minutes: int = 180) -> bool:
    if last_success is None:
        return True
    age = clock.now() - last_success
    return age.total_seconds() > stale_after_minutes * 60


def healthy(
    source_type: SourceType,
    label: str,
    last_success: datetime | None,
    permission: PermissionState = PermissionState.GRANTED,
) -> ConnectorHealth:
    return ConnectorHealth(
        source_type=source_type,
        label=label,
        health=HealthState.HEALTHY,
        permission_state=permission,
        last_success_at=last_success,
        stale=stale(last_success),
    )


def unavailable(
    source_type: SourceType,
    label: str,
    error_code: str,
    error_message: str,
    last_success: datetime | None = None,
    degraded_mode: str | None = "using_last_snapshot",
) -> ConnectorHealth:
    return ConnectorHealth(
        source_type=source_type,
        label=label,
        health=HealthState.UNAVAILABLE if last_success is None else HealthState.DEGRADED,
        permission_state=PermissionState.GRANTED,
        last_success_at=last_success,
        stale=True,
        error_code=error_code,
        error_message=error_message,
        degraded_mode=degraded_mode,
    )
