"""Read models for the Control Tower and related views."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import stale
from app.domain.enums import ApprovalState, VerificationState
from app.domain.models import (
    AgentRun,
    ApprovalRequest,
    AuditEvent,
    Claim,
    ConflictingClaim,
    DemoMetric,
    EvaluationSession,
    Obligation,
    Plan,
    PlanBlock,
    SourceConnection,
    SourceObservation,
    StudentPreference,
)
from app.domain.schemas import ControlTowerOut
from app.services import clock
from app.settings import get_settings


async def control_tower(session: AsyncSession, user_id: str) -> ControlTowerOut:
    settings = get_settings()
    obligations = (
        (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
        .scalars()
        .all()
    )
    conflicts = (
        (
            await session.execute(
                select(ConflictingClaim).where(
                    ConflictingClaim.user_id == user_id, ConflictingClaim.resolution.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    approvals = (
        (
            await session.execute(
                select(ApprovalRequest).where(
                    ApprovalRequest.user_id == user_id,
                    ApprovalRequest.state == ApprovalState.PENDING.value,
                )
            )
        )
        .scalars()
        .all()
    )
    connections = (
        (await session.execute(select(SourceConnection).where(SourceConnection.user_id == user_id)))
        .scalars()
        .all()
    )
    prefs = (
        await session.execute(select(StudentPreference).where(StudentPreference.user_id == user_id))
    ).scalar_one_or_none()
    latest_plan = (
        (
            await session.execute(
                select(Plan).where(Plan.user_id == user_id).order_by(Plan.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
    last_sync = {c.source_type: c.last_success_at for c in connections}
    coverage = {c.source_type: c.health for c in connections}
    last_recon = max((c.last_success_at for c in connections if c.last_success_at), default=None)
    verified = [o for o in obligations if o.verification_state == VerificationState.VERIFIED.value]
    high_risk = [
        o
        for o in obligations
        if o.priority == "high" and o.verification_state in {"conflicted", "needs_review"}
    ]
    readiness = "SYSTEM READY"
    if any(c.health != "healthy" for c in connections):
        readiness = "DEGRADED"
    if conflicts:
        readiness = "ATTENTION REQUIRED"
    if settings.simulate_offline:
        readiness = "OFFLINE"
    return ControlTowerOut(
        mode=settings.env.upper() if not settings.simulate_offline else "OFFLINE",
        readiness=readiness,
        now=clock.now(),
        timezone=settings.timezone,
        horizon_days=settings.plan_horizon_days,
        last_reconciliation_at=last_recon,
        grok_state=settings.grok_connection_state,
        monitoring_enabled=bool(prefs.monitoring_enabled) if prefs else True,
        verified_obligations=len(verified),
        open_conflicts=len(conflicts),
        pending_approvals=len(approvals),
        high_risk_obligations=len(high_risk) + len(conflicts),
        plan_feasible=latest_plan.feasible if latest_plan else None,
        plan_risk=latest_plan.risk_level if latest_plan else None,
        source_coverage=coverage,
        last_sync=last_sync,
    )


async def graph_payload(session: AsyncSession, user_id: str) -> dict[str, Any]:
    obligations = (
        (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
        .scalars()
        .all()
    )
    claims = (await session.execute(select(Claim).where(Claim.user_id == user_id))).scalars().all()
    observations = (
        (
            await session.execute(
                select(SourceObservation).where(SourceObservation.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    conflicts = (
        (await session.execute(select(ConflictingClaim).where(ConflictingClaim.user_id == user_id)))
        .scalars()
        .all()
    )
    blocks = (
        (await session.execute(select(PlanBlock).where(PlanBlock.user_id == user_id)))
        .scalars()
        .all()
    )
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for obs in observations:
        nodes.append(
            {
                "id": obs.id,
                "kind": "source",
                "label": obs.source_type,
                "state": "flagged" if obs.injection_flagged else "ok",
            }
        )
    for obl in obligations:
        nodes.append(
            {
                "id": obl.id,
                "kind": "obligation",
                "label": obl.title,
                "state": obl.verification_state,
            }
        )
    for claim in claims:
        nodes.append({"id": claim.id, "kind": "claim", "label": claim.value, "state": "claim"})
        edges.append({"from": claim.observation_id, "to": claim.id, "rel": "ASSERTS"})
        if claim.obligation_id:
            edges.append({"from": claim.id, "to": claim.obligation_id, "rel": "DEFINES"})
    for conflict in conflicts:
        nodes.append(
            {
                "id": conflict.id,
                "kind": "conflict",
                "label": conflict.reason_code,
                "state": conflict.resolution or "open",
            }
        )
        edges.append({"from": conflict.claim_a_id, "to": conflict.id, "rel": "CONTRADICTS"})
        edges.append({"from": conflict.claim_b_id, "to": conflict.id, "rel": "CONTRADICTS"})
    for block in blocks:
        if block.obligation_id:
            nodes.append(
                {
                    "id": block.id,
                    "kind": "plan_block",
                    "label": block.title,
                    "state": block.state,
                }
            )
            edges.append({"from": block.obligation_id, "to": block.id, "rel": "REQUIRES"})
    return {"nodes": nodes, "edges": edges}


async def demo_metrics(session: AsyncSession, user_id: str) -> dict[str, Any]:
    obligations = (
        (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
        .scalars()
        .all()
    )
    conflicts = (
        (await session.execute(select(ConflictingClaim).where(ConflictingClaim.user_id == user_id)))
        .scalars()
        .all()
    )
    approvals = (
        (await session.execute(select(ApprovalRequest).where(ApprovalRequest.user_id == user_id)))
        .scalars()
        .all()
    )
    runs = (
        (await session.execute(select(AgentRun).where(AgentRun.user_id == user_id))).scalars().all()
    )
    duration = sum(r.duration_ms for r in runs)
    stored = (
        (await session.execute(select(DemoMetric).where(DemoMetric.kind == "demo"))).scalars().all()
    )
    return {
        "kind": "demo",
        "disclaimer": "Simulated demo-run metrics. Not a student pilot.",
        "obligations_reconciled": len(obligations),
        "conflicts_seeded_and_found": len(conflicts),
        "calendar_actions_proposed": sum(1 for a in approvals),
        "calendar_actions_approved": sum(
            1 for a in approvals if a.state in {"approved", "applied"}
        ),
        "execution_time_ms": duration,
        "agent_runs": len(runs),
        "stored": [
            {"key": m.key, "value_int": m.value_int, "value_float": m.value_float, "label": m.label}
            for m in stored
        ],
    }


async def impact_bundle(session: AsyncSession, user_id: str) -> dict[str, Any]:
    demo = await demo_metrics(session, user_id)
    tests = (
        (await session.execute(select(DemoMetric).where(DemoMetric.kind == "system_test")))
        .scalars()
        .all()
    )
    pilots = (await session.execute(select(EvaluationSession))).scalars().all()
    return {
        "demo": demo,
        "system_test": {
            "kind": "system_test",
            "disclaimer": "Automated test metrics only.",
            "rows": [
                {
                    "key": m.key,
                    "value_int": m.value_int,
                    "value_float": m.value_float,
                    "label": m.label,
                }
                for m in tests
            ],
        },
        "pilot": {
            "kind": "pilot",
            "disclaimer": (
                "No pilot results recorded. Demo and system-test results are shown separately."
                if not pilots
                else "Observed evaluation sessions only. No fabricated responses."
            ),
            "sessions": [
                {
                    "id": p.id,
                    "participant_code": p.participant_code,
                    "kind": p.kind,
                    "planning_time_minutes": p.planning_time_minutes,
                    "created_at": p.created_at.isoformat(),
                }
                for p in pilots
            ],
        },
    }


async def attention_queue(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    conflicts = (
        (
            await session.execute(
                select(ConflictingClaim).where(
                    ConflictingClaim.user_id == user_id, ConflictingClaim.resolution.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    for conflict in conflicts:
        obl = await session.get(Obligation, conflict.obligation_id)
        items.append(
            {
                "id": conflict.id,
                "severity": "red",
                "kind": "conflict",
                "title": obl.title if obl else "Deadline conflict",
                "required_decision": "Choose the authoritative deadline",
                "evidence_status": "two_claims",
                "recommended_action": conflict.recommended_action,
                "object_id": conflict.id,
            }
        )
    reviews = (
        (
            await session.execute(
                select(Obligation).where(
                    Obligation.user_id == user_id,
                    Obligation.verification_state == VerificationState.NEEDS_REVIEW.value,
                )
            )
        )
        .scalars()
        .all()
    )
    for obl in reviews:
        items.append(
            {
                "id": obl.id,
                "severity": "amber",
                "kind": "needs_review",
                "title": obl.title,
                "required_decision": "Supply an exact date or reject the extraction",
                "evidence_status": "ambiguous_date",
                "recommended_action": "Do not invent a deadline",
                "object_id": obl.id,
            }
        )
    connections = (
        (await session.execute(select(SourceConnection).where(SourceConnection.user_id == user_id)))
        .scalars()
        .all()
    )
    for conn in connections:
        if conn.health != "healthy" or stale(conn.last_success_at, conn.stale_after_minutes):
            items.append(
                {
                    "id": conn.id,
                    "severity": "amber" if conn.health != "unavailable" else "red",
                    "kind": "source",
                    "title": conn.label,
                    "required_decision": "Inspect source health",
                    "evidence_status": conn.health,
                    "recommended_action": conn.degraded_mode or "retry",
                    "object_id": conn.id,
                }
            )
    return items


async def list_audit(session: AsyncSession, user_id: str) -> list[AuditEvent]:
    result = await session.execute(
        select(AuditEvent)
        .where(AuditEvent.user_id == user_id)
        .order_by(AuditEvent.created_at.asc())
    )
    return list(result.scalars().all())
