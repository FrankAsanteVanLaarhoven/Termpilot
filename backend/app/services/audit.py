"""Audit and agent-run recording."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AgentName, AgentRunState, ToolActionStatus
from app.domain.ids import new_id
from app.domain.models import AgentRun, AuditEvent, ToolAction
from app.services import clock


async def record_audit(
    session: AsyncSession,
    *,
    user_id: str,
    correlation_id: str,
    event_type: str,
    summary: str,
    agent: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    result: str = "ok",
    confidence: float | None = None,
    policy_check: str | None = None,
    approval_state: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        id=new_id("aud"),
        user_id=user_id,
        correlation_id=correlation_id,
        agent=agent,
        event_type=event_type,
        object_type=object_type,
        object_id=object_id,
        result=result,
        confidence=confidence,
        policy_check=policy_check,
        approval_state=approval_state,
        summary=summary[:400],
        created_at=clock.now(),
    )
    session.add(event)
    return event


async def run_agent(
    session: AsyncSession,
    *,
    user_id: str,
    request_id: str,
    agent: AgentName,
    assignment: str,
    source_inspected: str | None = None,
    tool_name: str | None = None,
    handover_to: str | None = None,
    work: Callable[[AgentRun], Awaitable[tuple[AgentRunState, str, str | None]]],
) -> AgentRun:
    run = AgentRun(
        id=new_id("run"),
        user_id=user_id,
        request_id=request_id,
        agent=agent.value,
        assignment=assignment[:240],
        state=AgentRunState.RUNNING.value,
        source_inspected=source_inspected,
        tool_name=tool_name,
        handover_to=handover_to,
        started_at=clock.now(),
    )
    session.add(run)
    await session.flush()
    started = perf_counter()
    try:
        state, artifact, uncertainty = await work(run)
        run.state = state.value
        run.output_artifact = artifact[:120] if artifact else None
        run.error_or_uncertainty = uncertainty
    except Exception as exc:  # noqa: BLE001
        run.state = AgentRunState.FAILED.value
        run.error_or_uncertainty = str(exc)[:400]
        raise
    finally:
        run.finished_at = clock.now()
        run.duration_ms = int((perf_counter() - started) * 1000)
        action = ToolAction(
            id=new_id("act"),
            user_id=user_id,
            agent_run_id=run.id,
            name=tool_name or agent.value,
            status=(
                ToolActionStatus.SUCCEEDED.value
                if run.state in {AgentRunState.PASSED.value, AgentRunState.DEGRADED.value}
                else ToolActionStatus.FAILED.value
                if run.state == AgentRunState.FAILED.value
                else ToolActionStatus.BLOCKED.value
            ),
            input_summary=assignment[:400],
            output_summary=(run.output_artifact or run.error_or_uncertainty or "")[:400],
            error_code=None if run.state != AgentRunState.FAILED.value else "agent_failed",
            duration_ms=run.duration_ms,
            created_at=clock.now(),
        )
        session.add(action)
    return run


def dump(obj: Any) -> str:
    return str(obj)[:400]
