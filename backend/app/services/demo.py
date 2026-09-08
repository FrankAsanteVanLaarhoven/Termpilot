"""Demo seed and reset. Synthetic data only."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.ics import IcsConnector
from app.domain.enums import ConsentPurpose, SourceType
from app.domain.ids import new_id
from app.domain.models import (
    CalendarEvent,
    ConsentGrant,
    SourceConnection,
    StudentPreference,
    UserProfile,
)
from app.services import clock
from app.services.identity import (
    DEMO_EMAIL,
    connection_id_for,
    display_name_from_email,
    is_demo_email,
)
from app.settings import get_settings
from app.storage.database import drop_db, init_db, reset_engine

DEMO_USER_NAME = "Demo student"
DEMO_USERNAME = "FAVL"
PUBLIC_GOAL = (
    "TermPilot, reconcile my academic and recruiting commitments for the next 14 days. "
    "Show conflicts, build a realistic plan around my 20-hour weekly limit, "
    "and ask before changing my calendar."
)


async def reset_demo(session: AsyncSession | None = None) -> dict[str, Any]:
    del session
    await reset_engine()
    await drop_db()
    await init_db()
    from app.storage.database import get_session_factory

    factory = get_session_factory()
    async with factory() as seeded:
        result = await seed_user(seeded)
        await seeded.commit()
        return result


async def seed_user(
    session: AsyncSession,
    user_id: str | None = None,
    display_name: str | None = None,
    email: str | None = None,
    password: str | None = None,
    email_verified: bool | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    now = clock.now()
    uid = user_id or settings.demo_user_id
    existing = await session.get(UserProfile, uid)
    if existing is not None:
        return {"user_id": existing.id, "display_name": existing.display_name, "created": False}
    name = display_name or (DEMO_USER_NAME if uid == settings.demo_user_id else None)
    if name is None and email:
        name = display_name_from_email(email)
    from app.services.auth import DEMO_PASSWORD, hash_password

    secret = password or (DEMO_PASSWORD if uid == settings.demo_user_id else None)
    verified = email_verified
    if verified is None:
        verified = is_demo_email(email or "") or uid == settings.demo_user_id or settings.env != "production"
    user = UserProfile(
        id=uid,
        display_name=name or DEMO_USER_NAME,
        email=email
        if email and not is_demo_email(email)
        else (email or DEMO_EMAIL),
        password_hash=hash_password(secret) if secret else None,
        email_verified_at=now if verified else None,
        timezone=settings.timezone,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    purposes = [
        (ConsentPurpose.SOURCE_READ, SourceType.LMS.value, "Read synthetic LMS assignments"),
        (ConsentPurpose.SOURCE_READ, SourceType.EMAIL.value, "Read selected forwarded mail"),
        (ConsentPurpose.SOURCE_READ, SourceType.CALENDAR.value, "Read demo ICS calendar"),
        (ConsentPurpose.SOURCE_READ, SourceType.UPLOAD.value, "Read uploaded notes"),
        (
            ConsentPurpose.CALENDAR_WRITE,
            None,
            "Write study blocks to the demo calendar after approval",
        ),
        (ConsentPurpose.MONITORING, None, "Recheck authorised sources on a schedule"),
        (ConsentPurpose.EVALUATION, None, "Record optional evaluation metrics"),
    ]
    for purpose, source, note in purposes:
        session.add(
            ConsentGrant(
                id=new_id("cns"),
                user_id=uid,
                purpose=purpose.value,
                source_type=source,
                granted=True,
                granted_at=now,
                expires_at=now + timedelta(days=30),
                scope_note=note,
            )
        )
    session.add(
        StudentPreference(
            id=new_id("prf"),
            user_id=uid,
            weekly_study_limit_hours=settings.weekly_study_limit_hours,
            max_study_block_minutes=settings.max_study_block_minutes,
            break_minutes=settings.break_minutes,
            sleep_start="23:00",
            sleep_end="07:00",
            preferred_windows_json=[
                {"days": "weekdays", "start": "09:00", "end": "12:00"},
                {"days": "weekdays", "start": "19:00", "end": "22:00"},
            ],
            commute_minutes=30,
            historical_estimate_factor=1.0,
            monitoring_enabled=True,
            updated_at=now,
        )
    )
    connections = [
        ("src_lms", SourceType.LMS, "Northbridge LMS (synthetic)"),
        ("src_email", SourceType.EMAIL, "University email"),
        ("src_cal", SourceType.CALENDAR, "Student ICS calendar (synthetic)"),
        ("src_upload", SourceType.UPLOAD, "Local uploads"),
    ]
    for cid, stype, label in connections:
        session.add(
            SourceConnection(
                id=connection_id_for(uid, cid),
                user_id=uid,
                source_type=stype.value,
                label=label,
                health="healthy",
                permission_state="granted",
                last_success_at=now,
                stale_after_minutes=180,
                created_at=now,
            )
        )
    from app.services.workspace import seed_optional_connectors

    await seed_optional_connectors(session, uid)
    from app.services.mailbox import seed_mailbox

    await seed_mailbox(session, uid)
    ics = IcsConnector()
    observations = await ics.fetch_observations(uid)
    for obs in observations:
        for event in obs.payload.get("events", []):
            session.add(
                CalendarEvent(
                    id=new_id("cal"),
                    user_id=uid,
                    uid=str(event["uid"]),
                    title=str(event["title"]),
                    start_at=datetime.fromisoformat(event["start_at"]),
                    end_at=datetime.fromisoformat(event["end_at"]),
                    kind=_event_kind(str(event["title"])),
                    source="ics",
                    written_by_termpilot=False,
                    created_at=now,
                )
            )
    await session.flush()
    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "email": user.email,
        "created": True,
        "connections": [c[0] for c in connections],
        "fixed_events": len(observations[0].payload.get("events", [])) if observations else 0,
    }


def _event_kind(title: str) -> str:
    lowered = title.lower()
    if "work" in lowered:
        return "work"
    if "society" in lowered:
        return "society"
    return "fixed"


async def prepare_student_workspace(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Connect demo adapters and reconcile once so LinkedIn testers see a live tower."""
    from app.domain.models import Obligation
    from app.services.pipeline import reconcile
    from app.services.workspace import connect_all

    linked = await connect_all(session, user_id, None)
    await session.flush()
    count = int(
        (
            await session.execute(
                select(func.count()).select_from(Obligation).where(Obligation.user_id == user_id)
            )
        ).scalar_one()
    )
    reconciled = False
    if count == 0:
        await reconcile(session, user_id, PUBLIC_GOAL, False)
        await session.flush()
        count = int(
            (
                await session.execute(
                    select(func.count()).select_from(Obligation).where(Obligation.user_id == user_id)
                )
            ).scalar_one()
        )
        reconciled = True
    return {
        "connected": int(linked.get("count") or 0),
        "reconciled": reconciled,
        "obligations": count,
        "public_demo": True,
    }


async def get_user(session: AsyncSession, user_id: str | None = None) -> UserProfile:
    settings = get_settings()
    uid = user_id or settings.demo_user_id
    result = await session.execute(select(UserProfile).where(UserProfile.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise LookupError("demo_user_missing")
    return user
