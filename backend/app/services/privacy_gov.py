"""Cookie consent and hashed policy cache. No raw student mail in Postgres."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ids import new_id
from app.domain.models import CookieGrant, PolicyCache
from app.services import clock
from app.services.formatter import hash_identifier, payload_digest

COOKIE_VERSION = "2026-09-05"
POLICY_VERSION = "governance-2026-09"


async def record_cookie_choice(
    session: AsyncSession, user_id: str, necessary: bool, analytics: bool, export: bool
) -> dict[str, Any]:
    now = clock.now()
    row = CookieGrant(
        id=new_id("cky"),
        user_hash=hash_identifier(user_id),
        version=COOKIE_VERSION,
        necessary=True,
        analytics=analytics and necessary,
        export=export and necessary,
        granted_at=now,
    )
    session.add(row)
    return {
        "version": COOKIE_VERSION,
        "necessary": True,
        "analytics": row.analytics,
        "export": row.export,
        "user": "hashed",
    }


async def cache_policy(session: AsyncSession, title: str, body: str, approved: bool) -> dict[str, Any]:
    digest = payload_digest({"title": title, "body": body, "version": POLICY_VERSION})
    existing = await session.get(PolicyCache, digest)
    if existing is None:
        existing = PolicyCache(
            id=digest,
            title=title[:240],
            version=POLICY_VERSION,
            approved=approved,
            cached_at=clock.now(),
        )
        session.add(existing)
    else:
        existing.approved = approved
        existing.cached_at = clock.now()
    return {
        "policy_hash": digest,
        "approved": approved,
        "version": POLICY_VERSION,
        "stored_raw_body": False,
    }


async def list_policies(session: AsyncSession) -> list[dict[str, Any]]:
    rows = (await session.execute(select(PolicyCache))).scalars().all()
    return [
        {
            "policy_hash": row.id,
            "title": row.title,
            "approved": row.approved,
            "version": row.version,
            "cached_at": row.cached_at.isoformat(),
        }
        for row in rows
    ]


def cookie_banner() -> dict[str, Any]:
    return {
        "version": COOKIE_VERSION,
        "necessary": "Required for sign-in, approvals and security.",
        "analytics": "Off by default. Never used to score students.",
        "export": "Required only if you send a copy of your own data to a destination you choose.",
        "note": "TermPilot does not sell data. Postgres stores hashes for identifiers, not raw mailbox bodies.",
    }
