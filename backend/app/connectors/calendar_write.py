"""Demo calendar adapter. Never writes to a real calendar."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ids import new_id
from app.domain.models import CalendarEvent
from app.services import clock
from app.settings import get_settings


class CalendarWriteError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class DemoCalendarAdapter:
    """In-database demo calendar with ICS export."""

    async def list_events(self, session: AsyncSession, user_id: str) -> list[CalendarEvent]:
        result = await session.execute(
            select(CalendarEvent).where(
                CalendarEvent.user_id == user_id, CalendarEvent.rolled_back.is_(False)
            )
        )
        return list(result.scalars().all())

    async def apply_blocks(
        self,
        session: AsyncSession,
        user_id: str,
        blocks: list[dict[str, str]],
        approval_id: str,
        idempotency_key: str,
    ) -> list[CalendarEvent]:
        if get_settings().simulate_calendar_write_failure:
            raise CalendarWriteError("calendar_write_failed", "Demo calendar write failed.")
        existing = await session.execute(
            select(CalendarEvent).where(CalendarEvent.approval_id == approval_id)
        )
        already = list(existing.scalars().all())
        if already:
            return already
        created: list[CalendarEvent] = []
        for block in blocks:
            uid = f"{idempotency_key}-{block['id']}@termpilot.demo"
            found = await session.execute(select(CalendarEvent).where(CalendarEvent.uid == uid))
            if found.scalar_one_or_none() is not None:
                continue
            event = CalendarEvent(
                id=new_id("cal"),
                user_id=user_id,
                uid=uid,
                title=block["title"],
                start_at=datetime.fromisoformat(block["start_at"]),
                end_at=datetime.fromisoformat(block["end_at"]),
                kind=block.get("kind", "study"),
                source="termpilot",
                written_by_termpilot=True,
                approval_id=approval_id,
                rolled_back=False,
                created_at=clock.now(),
            )
            session.add(event)
            created.append(event)
        return created

    async def rollback(self, session: AsyncSession, approval_id: str) -> int:
        result = await session.execute(
            select(CalendarEvent).where(CalendarEvent.approval_id == approval_id)
        )
        events = list(result.scalars().all())
        for event in events:
            event.rolled_back = True
        return len(events)
