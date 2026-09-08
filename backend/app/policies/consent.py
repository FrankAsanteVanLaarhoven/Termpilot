"""Consent and permission enforcement. Fail closed."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ConsentPurpose
from app.domain.models import ConsentGrant
from app.services import clock


class ConsentError(PermissionError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


async def require_consent(
    session: AsyncSession,
    user_id: str,
    purpose: ConsentPurpose,
    source_type: str | None = None,
) -> ConsentGrant:
    now = clock.now()
    stmt = select(ConsentGrant).where(
        ConsentGrant.user_id == user_id,
        ConsentGrant.purpose == purpose.value,
        ConsentGrant.granted.is_(True),
        ConsentGrant.revoked_at.is_(None),
    )
    if source_type is not None:
        stmt = stmt.where(
            (ConsentGrant.source_type == source_type) | (ConsentGrant.source_type.is_(None))
        )
    result = await session.execute(stmt)
    grants = list(result.scalars().all())
    for grant in grants:
        if grant.expires_at is not None and grant.expires_at <= now:
            continue
        if source_type is None or grant.source_type in {None, source_type}:
            return grant
    raise ConsentError(
        "consent_missing",
        f"No active consent for {purpose.value}" + (f"/{source_type}" if source_type else "") + ".",
    )


async def revoke_consent(session: AsyncSession, grant: ConsentGrant) -> None:
    grant.granted = False
    grant.revoked_at = clock.now()
