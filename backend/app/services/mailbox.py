"""Student mailbox desk: classify, alert, draft, cleanup.

The bot may act on authorised mail only. Sends stay in the demo outbox
until Guardian + explicit on-screen approval. Cleanup archives clutter
(P2/P3) and never drops P0/P1 academic or visa mail.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AgentName
from app.domain.ids import new_id
from app.domain.models import MailItem, UserProfile
from app.policies.consent import ConsentError
from app.services import clock
from app.services.audit import record_audit
from app.services.identity import get_connection, scoped_id
from app.services.workspace import draft_email
from app.settings import get_settings

STUDENT_EMAIL = "info@frankvanlaarhoven.co.uk"

HIERARCHY: list[dict[str, str]] = [
    {
        "order": "1",
        "fn": "guardian.inspect_goal",
        "priority": "all",
        "note": "Block homework completion and impersonation before any mail action.",
    },
    {
        "order": "2",
        "fn": "consent.require_authorised_mailbox",
        "priority": "all",
        "note": "Read only mail the student has linked. No hidden monitoring.",
    },
    {
        "order": "3",
        "fn": "mailbox.classify",
        "priority": "all",
        "note": "P0 visa/deadline, P1 university/career, P2 society/news, P3 promo.",
    },
    {
        "order": "4",
        "fn": "mailbox.alert",
        "priority": "p0",
        "note": "ASAP surface. Never silent on P0.",
    },
    {
        "order": "5",
        "fn": "mailbox.draft",
        "priority": "p0-p1",
        "note": "Draft a reply or clarification. Never SMTP from this step.",
    },
    {
        "order": "6",
        "fn": "approval.require",
        "priority": "send",
        "note": "On-screen approve. Spoken yes is not enough.",
    },
    {
        "order": "7",
        "fn": "mailbox.send_demo_outbox",
        "priority": "approved",
        "note": "Copy to the demo outbox. No external send.",
    },
    {
        "order": "8",
        "fn": "mailbox.cleanup_clutter",
        "priority": "p2-p3",
        "note": "Archive newsletters and promo. Never archive P0/P1.",
    },
]


def _fixture() -> dict[str, Any]:
    path = get_settings().fixtures_root / "mailbox" / "inbox.json"
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return payload


async def _mail_authorised(session: AsyncSession, user_id: str) -> bool:
    email = await get_connection(session, user_id, "src_email")
    mailbox = await get_connection(session, user_id, "src_mailbox")
    return any(
        row is not None and row.user_id == user_id and row.permission_state == "granted"
        for row in (email, mailbox)
    )


async def _send_authorised(session: AsyncSession, user_id: str) -> bool:
    mailbox = await get_connection(session, user_id, "src_mailbox")
    return bool(mailbox and mailbox.user_id == user_id and mailbox.permission_state == "granted")


async def seed_mailbox(session: AsyncSession, user_id: str) -> int:
    existing = (
        (await session.execute(select(MailItem.id).where(MailItem.user_id == user_id)))
        .scalars()
        .all()
    )
    if existing:
        return len(existing)
    owner = await session.get(UserProfile, user_id)
    to_address = (owner.email if owner and owner.email else STUDENT_EMAIL)
    count = 0
    for raw in _fixture().get("items", []):
        observed = datetime.fromisoformat(str(raw["observed_at"]))
        session.add(
            MailItem(
                id=scoped_id(user_id, str(raw["id"])),
                user_id=user_id,
                from_address=str(raw["from"]),
                to_address=to_address,
                subject=str(raw["subject"]),
                excerpt=str(raw.get("excerpt") or ""),
                priority=str(raw.get("priority") or "p2"),
                category=str(raw.get("category") or "newsletter"),
                state="inbox",
                suggested_action=str(raw.get("suggested_action") or "keep"),
                observed_at=observed,
            )
        )
        count += 1
    return count


def _item_dict(row: MailItem) -> dict[str, Any]:
    return {
        "id": row.id,
        "from": row.from_address,
        "to": row.to_address,
        "subject": row.subject,
        "excerpt": row.excerpt,
        "priority": row.priority,
        "category": row.category,
        "state": row.state,
        "suggested_action": row.suggested_action,
        "observed_at": row.observed_at.isoformat(),
        "archived_at": row.archived_at.isoformat() if row.archived_at else None,
    }


async def mailbox_desk(session: AsyncSession, user_id: str) -> dict[str, Any]:
    if not await _mail_authorised(session, user_id):
        raise ConsentError(
            "mailbox_disconnected",
            "Connect the university mailbox or student mailbox first. TermPilot will not guess the inbox.",
        )
    await seed_mailbox(session, user_id)
    owner = await session.get(UserProfile, user_id)
    student_email = owner.email if owner and owner.email else STUDENT_EMAIL
    rows = (
        (
            await session.execute(
                select(MailItem)
                .where(MailItem.user_id == user_id)
                .order_by(MailItem.priority, MailItem.observed_at)
            )
        )
        .scalars()
        .all()
    )
    items = [_item_dict(row) for row in rows]
    inbox = [i for i in items if i["state"] == "inbox"]
    alerts = [i for i in inbox if i["priority"] == "p0"]
    clutter = [i for i in inbox if i["priority"] in {"p2", "p3"}]
    return {
        "authorised": True,
        "can_send": await _send_authorised(session, user_id),
        "student_email": student_email,
        "smtp": False,
        "note": (
            "The bot can draft, alert and archive clutter in this desk. "
            "Sends copy to the demo outbox after on-screen approval. No SMTP."
        ),
        "hierarchy": HIERARCHY,
        "counts": {
            "inbox": len(inbox),
            "archived": sum(1 for i in items if i["state"] == "archived"),
            "p0": sum(1 for i in inbox if i["priority"] == "p0"),
            "p1": sum(1 for i in inbox if i["priority"] == "p1"),
            "p2": sum(1 for i in inbox if i["priority"] == "p2"),
            "p3": sum(1 for i in inbox if i["priority"] == "p3"),
        },
        "alerts": alerts,
        "clutter": clutter,
        "items": items,
    }


async def cleanup_mailbox(session: AsyncSession, user_id: str) -> dict[str, Any]:
    desk = await mailbox_desk(session, user_id)
    now = clock.now()
    archived: list[str] = []
    kept: list[str] = []
    rows = (
        (
            await session.execute(
                select(MailItem).where(MailItem.user_id == user_id, MailItem.state == "inbox")
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        if row.priority in {"p2", "p3"}:
            row.state = "archived"
            row.archived_at = now
            archived.append(row.id)
        else:
            kept.append(row.id)
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=new_id("cln"),
        agent=AgentName.GUARDIAN.value,
        event_type="mailbox_cleanup",
        object_type="mailbox",
        object_id="desk",
        summary=f"Archived {len(archived)} clutter messages. Kept {len(kept)} P0/P1.",
        policy_check="clutter_only",
    )
    return {
        "archived": archived,
        "kept": kept,
        "counts": {
            "archived_now": len(archived),
            "kept_p0_p1": len(kept),
        },
        "hierarchy_step": "mailbox.cleanup_clutter",
        "smtp": False,
        "can_send": desk["can_send"],
    }


async def draft_from_item(session: AsyncSession, user_id: str, item_id: str) -> dict[str, Any]:
    if not await _send_authorised(session, user_id):
        raise ConsentError(
            "mailbox_send_disconnected",
            "Connect the student mailbox to draft a send. Drafts still need on-screen approval.",
        )
    row = await session.get(MailItem, item_id)
    if row is None or row.user_id != user_id:
        raise LookupError("mail_not_found")
    if row.priority in {"p2", "p3"}:
        raise ConsentError(
            "clutter_no_draft",
            "Promo and newsletters are archived, not answered. I will not impersonate you to a vendor.",
        )
    body = (
        f"Hello,\n\nI am writing about: {row.subject}.\n\n"
        f"{row.excerpt}\n\nThis is a TermPilot draft from the authorised mailbox of "
        f"{STUDENT_EMAIL}. It has not been sent.\n"
    )
    drafted = await draft_email(
        session,
        user_id,
        row.from_address,
        f"Re: {row.subject}"[:240],
        body,
        "email",
    )
    row.suggested_action = "drafted"
    return {
        **drafted,
        "mail_id": row.id,
        "priority": row.priority,
        "hierarchy_step": "mailbox.draft",
        "smtp": False,
    }
