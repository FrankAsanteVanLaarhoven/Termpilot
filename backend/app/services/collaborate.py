"""Student-to-student task invites. No cohort scoring or advisor surveillance."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ids import new_id
from app.domain.models import CollaborationInvite, Obligation, UserProfile
from app.services import clock
from app.services.audit import record_audit
from app.settings import get_settings

PEERS = [
    {
        "code": "usr_okonkwo",
        "name": "S. Okonkwo",
        "context": "CSC0000 lab partner (synthetic)",
    },
    {
        "code": "usr_chen",
        "name": "M. Chen",
        "context": "ENG0001 study group (synthetic)",
    },
]


async def me(session: AsyncSession, user_id: str) -> dict[str, Any]:
    user = await session.get(UserProfile, user_id)
    settings_demo = user_id == get_settings().demo_user_id
    return {
        "user_id": user_id,
        "display_name": user.display_name if user else "Frank Van Laarhoven",
        "username": user.id if user else user_id,
        "email": (user.email if user and user.email else "info@frankvanlaarhoven.co.uk"),
        "timezone": user.timezone if user else "Europe/London",
        "role": "student",
        "plan": "demo",
        "synthetic": True,
        "demo_identity": settings_demo,
    }


async def invite(
    session: AsyncSession,
    user_id: str,
    to_code: str,
    obligation_id: str | None,
    note: str,
) -> dict[str, Any]:
    peer = next((p for p in PEERS if p["code"] == to_code), None)
    if peer is None:
        raise LookupError("unknown_peer")
    title = ""
    if obligation_id:
        obl = await session.get(Obligation, obligation_id)
        if obl is None or obl.user_id != user_id:
            raise LookupError("obligation_not_found")
        title = obl.title
    row = CollaborationInvite(
        id=new_id("inv"),
        from_user_id=user_id,
        to_code=peer["code"],
        to_name=peer["name"],
        obligation_id=obligation_id,
        task_title=title,
        note=note[:400],
        state="pending",
        created_at=clock.now(),
    )
    session.add(row)
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=row.id,
        event_type="collaboration_invite",
        object_type="invite",
        object_id=row.id,
        summary=f"Invited {peer['name']} to collaborate on {title or 'a task'}.",
    )
    return {
        "id": row.id,
        "to_code": row.to_code,
        "to_name": row.to_name,
        "task_title": row.task_title,
        "state": row.state,
        "note": "Invite is student-controlled. No advisor scoring.",
    }


async def list_invites(session: AsyncSession, user_id: str) -> dict[str, Any]:
    rows = (
        (
            await session.execute(
                select(CollaborationInvite)
                .where(CollaborationInvite.from_user_id == user_id)
                .order_by(CollaborationInvite.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "peers": PEERS,
        "items": [
            {
                "id": r.id,
                "to_code": r.to_code,
                "to_name": r.to_name,
                "task_title": r.task_title,
                "obligation_id": r.obligation_id,
                "state": r.state,
                "note": r.note,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }
