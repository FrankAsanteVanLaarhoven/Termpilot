"""Monitoring routine: recheck authorised sources and alert only on material change."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AgentName, AgentRunState, ConsentPurpose
from app.domain.models import Obligation, SourceObservation
from app.policies.consent import ConsentError, require_consent
from app.services.audit import record_audit, run_agent
from app.services.pipeline import extract_and_verify, sync_sources
from app.settings import get_settings


async def run_monitor(session: AsyncSession, user_id: str) -> dict[str, Any]:
    request_id = "mon_" + user_id[-4:]
    settings = get_settings()
    if settings.simulate_offline:
        return {"status": "skipped", "reason": "offline"}

    async def work(_run: Any) -> tuple[AgentRunState, str, str | None]:
        try:
            await require_consent(session, user_id, ConsentPurpose.MONITORING)
        except ConsentError as exc:
            return AgentRunState.BLOCKED, "consent_missing", str(exc)
        before_obs = (
            (
                await session.execute(
                    select(SourceObservation).where(SourceObservation.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        before_obligations = (
            (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
            .scalars()
            .all()
        )
        before_digests = {o.content_digest for o in before_obs}
        before_due = {
            (o.fingerprint, o.due_at.isoformat() if o.due_at else None) for o in before_obligations
        }
        await sync_sources(session, user_id, request_id)
        await extract_and_verify(session, user_id, request_id)
        after_obs = (
            (
                await session.execute(
                    select(SourceObservation).where(SourceObservation.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        after_obligations = (
            (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
            .scalars()
            .all()
        )
        new_obs = [o for o in after_obs if o.content_digest not in before_digests]
        after_due = {
            (o.fingerprint, o.due_at.isoformat() if o.due_at else None) for o in after_obligations
        }
        material = bool(new_obs) or before_due != after_due
        if material:
            await record_audit(
                session,
                user_id=user_id,
                correlation_id=request_id,
                agent=AgentName.MONITOR.value,
                event_type="material_change",
                summary="Authorised source changed a deadline or added evidence.",
            )
            return AgentRunState.PASSED, "alert", None
        await record_audit(
            session,
            user_id=user_id,
            correlation_id=request_id,
            agent=AgentName.MONITOR.value,
            event_type="no_material_change",
            summary="Recheck complete. No student-facing alert.",
        )
        return AgentRunState.PASSED, "quiet", None

    run = await run_agent(
        session,
        user_id=user_id,
        request_id=request_id,
        agent=AgentName.MONITOR,
        assignment="Recheck authorised sources; alert only on material change",
        tool_name="monitor-routine",
        work=work,
    )
    return {"status": run.state, "artifact": run.output_artifact}
