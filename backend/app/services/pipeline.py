"""Reconciliation, planning and approval pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.grok_client import get_grok_adapter
from app.connectors.calendar_write import CalendarWriteError, DemoCalendarAdapter
from app.connectors.email import EmailConnector
from app.connectors.ics import IcsConnector
from app.connectors.lms import LmsConnector
from app.connectors.upload import UploadConnector
from app.domain.enums import (
    AgentName,
    AgentRunState,
    ApprovalState,
    ConflictResolution,
    ConsentPurpose,
    GuardianDecision,
    ObligationStatus,
    ObligationType,
    PlanBlockKind,
    PlanBlockState,
    SourceType,
    VerificationState,
)
from app.domain.ids import new_id
from app.domain.models import (
    ApprovalRequest,
    Claim,
    ConflictingClaim,
    Obligation,
    Plan,
    PlanBlock,
    SourceConnection,
    SourceObservation,
    StudentPreference,
)
from app.domain.schemas import CandidateObligation, OrchestratorOut
from app.planning.solver import FixedBusy, solve_from_records
from app.policies.approval import ApprovalError, assert_usable
from app.policies.consent import ConsentError, require_consent
from app.policies.integrity import inspect_source_text, inspect_user_goal
from app.services import clock
from app.services.audit import record_audit, run_agent
from app.services.matching import material_due_conflict, same_obligation
from app.settings import get_settings

_lms = LmsConnector()
_email = EmailConnector()
_ics = IcsConnector()
_upload = UploadConnector()
_calendar = DemoCalendarAdapter()


def connectors() -> dict[SourceType, Any]:
    return {
        SourceType.LMS: _lms,
        SourceType.EMAIL: _email,
        SourceType.CALENDAR: _ics,
        SourceType.UPLOAD: _upload,
    }


def set_lms_outage(flag: bool) -> None:
    _lms.set_outage(flag)


async def _connection(
    session: AsyncSession, user_id: str, source_type: SourceType
) -> SourceConnection:
    result = await session.execute(
        select(SourceConnection).where(
            SourceConnection.user_id == user_id,
            SourceConnection.source_type == source_type.value,
        )
    )
    conn = result.scalar_one()
    return conn


async def sync_sources(
    session: AsyncSession,
    user_id: str,
    request_id: str,
    simulate_lms_outage: bool | None = None,
) -> dict[str, Any]:
    if simulate_lms_outage is not None:
        set_lms_outage(simulate_lms_outage)
    summaries: dict[str, Any] = {}

    async def _sync_one(source_type: SourceType, connector: Any) -> None:
        conn = await _connection(session, user_id, source_type)
        try:
            await require_consent(session, user_id, ConsentPurpose.SOURCE_READ, source_type.value)
        except ConsentError as exc:
            conn.health = "permission_revoked"
            conn.permission_state = "revoked"
            conn.last_error_code = exc.code
            conn.last_error_message = str(exc)
            summaries[source_type.value] = {"status": "blocked", "error": exc.code}
            return
        health = await connector.health_check()
        conn.health = health.health.value
        conn.permission_state = health.permission_state.value
        conn.last_error_code = health.error_code
        conn.last_error_message = health.error_message
        conn.degraded_mode = health.degraded_mode
        observations = await connector.fetch_observations(user_id)
        stored = 0
        for item in observations:
            existing = await session.execute(
                select(SourceObservation).where(
                    SourceObservation.user_id == user_id,
                    SourceObservation.content_digest == item.content_digest,
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            session.add(
                SourceObservation(
                    id=new_id("obs"),
                    user_id=user_id,
                    connection_id=conn.id,
                    source_type=item.source_type.value,
                    source_reference=item.source_reference,
                    source_authority=item.source_authority.value,
                    observed_at=item.observed_at,
                    content_digest=item.content_digest,
                    excerpt=item.excerpt[:1000],
                    raw_retained=False,
                    raw_expires_at=clock.now()
                    + timedelta(hours=get_settings().raw_source_retention_hours),
                    payload_json=item.payload,
                    injection_flagged=item.injection_flagged,
                )
            )
            stored += 1
        if health.health.value in {"healthy", "degraded"}:
            conn.last_success_at = clock.now()
        summaries[source_type.value] = {
            "status": health.health.value,
            "stored": stored,
            "degraded_mode": health.degraded_mode,
        }

    async def work(_run: Any) -> tuple[AgentRunState, str, str | None]:
        for source_type, connector in connectors().items():
            await _sync_one(source_type, connector)
        degraded = [k for k, v in summaries.items() if v["status"] != "healthy"]
        state = AgentRunState.DEGRADED if degraded else AgentRunState.PASSED
        uncertainty = ",".join(degraded) if degraded else None
        return state, f"sync:{summaries}", uncertainty

    await run_agent(
        session,
        user_id=user_id,
        request_id=request_id,
        agent=AgentName.SCOUT,
        assignment="Inspect authorised LMS, email, calendar and upload sources",
        tool_name="fetch_observations",
        handover_to=AgentName.VERIFIER.value,
        work=work,
    )
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=request_id,
        agent=AgentName.SCOUT.value,
        event_type="source_sync",
        summary="Authorised sources inspected.",
        result="ok",
    )
    return summaries


async def extract_and_verify(
    session: AsyncSession, user_id: str, request_id: str
) -> dict[str, Any]:
    adapter = get_grok_adapter()
    observations = (
        (
            await session.execute(
                select(SourceObservation).where(SourceObservation.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    candidates: list[CandidateObligation] = []
    injection_hits: list[str] = []

    async def scout_work(_run: Any) -> tuple[AgentRunState, str, str | None]:
        nonlocal candidates, injection_hits
        for obs in observations:
            source_text = str(obs.payload_json.get("body") or obs.payload_json)
            verdict = inspect_source_text(source_text)
            if verdict.blocked_actions:
                injection_hits.extend(verdict.blocked_actions)
                await record_audit(
                    session,
                    user_id=user_id,
                    correlation_id=request_id,
                    agent=AgentName.GUARDIAN.value,
                    event_type="prompt_injection_ignored",
                    object_type="observation",
                    object_id=obs.id,
                    result="ignored",
                    policy_check="prompt_injection",
                    summary="Instruction-like source text ignored.",
                )
            result = await adapter.extract_obligations(
                SourceType(obs.source_type),
                obs.payload_json,
                obs.observed_at,
                obs.source_reference,
                get_settings().timezone,
            )
            for candidate in result.candidates:
                candidate.source_reference = candidate.source_reference or obs.source_reference
                candidates.append(candidate)
            if result.discarded_instructions:
                injection_hits.extend(result.discarded_instructions)
        return AgentRunState.PASSED, f"candidates={len(candidates)}", None

    await run_agent(
        session,
        user_id=user_id,
        request_id=request_id,
        agent=AgentName.SCOUT,
        assignment="Extract candidate obligations with provenance",
        source_inspected="authorised_sources",
        tool_name="extract-obligations",
        handover_to=AgentName.VERIFIER.value,
        work=scout_work,
    )

    study_candidates = [
        c
        for c in candidates
        if c.type in {ObligationType.ASSIGNMENT, ObligationType.RECRUITING, ObligationType.EXAM}
    ]

    merged: list[list[CandidateObligation]] = []
    for candidate in study_candidates:
        placed = False
        for group in merged:
            if same_obligation(group[0], candidate):
                group.append(candidate)
                placed = True
                break
        if not placed:
            merged.append([candidate])

    created: list[Obligation] = []
    conflicts = 0

    async def verify_work(_run: Any) -> tuple[AgentRunState, str, str | None]:
        nonlocal conflicts
        for group in merged:
            primary = max(group, key=lambda c: (c.source_authority == "primary", c.confidence))
            dues = [c.due_at for c in group if c.due_at is not None]
            conflicted = False
            if len(dues) >= 2:
                for i, left in enumerate(dues):
                    for right in dues[i + 1 :]:
                        if material_due_conflict(left, right):
                            conflicted = True
            ambiguous = any(c.date_precision == "ambiguous" or c.due_at is None for c in group)
            if conflicted:
                state = VerificationState.CONFLICTED
            elif ambiguous:
                state = VerificationState.NEEDS_REVIEW
            elif max(c.confidence for c in group) >= 0.9:
                state = VerificationState.VERIFIED
            elif max(c.confidence for c in group) >= 0.7:
                state = VerificationState.PROBABLE
            else:
                state = VerificationState.REJECTED
            if state == VerificationState.REJECTED:
                continue
            existing = await session.execute(
                select(Obligation).where(
                    Obligation.user_id == user_id,
                    Obligation.fingerprint == (primary.fingerprint_hint or primary.title),
                )
            )
            obligation = existing.scalar_one_or_none()
            now = clock.now()
            if obligation is None:
                obligation = Obligation(
                    id=new_id("obl"),
                    user_id=user_id,
                    type=primary.type.value,
                    title=primary.title,
                    course_or_context=primary.course_or_context,
                    description=primary.description[:400],
                    due_at=primary.due_at if not conflicted else min(dues) if dues else None,
                    estimated_minutes=max(c.estimated_minutes for c in group),
                    priority=primary.priority.value,
                    status=ObligationStatus.NOT_STARTED.value,
                    source_type=primary.source_type.value,
                    source_reference=primary.source_reference,
                    source_observed_at=primary.source_observed_at,
                    source_authority=primary.source_authority.value,
                    confidence=max(c.confidence for c in group),
                    verification_state=state.value,
                    sensitivity="student_private",
                    requires_approval=True,
                    fingerprint=primary.fingerprint_hint or primary.title,
                    date_precision="ambiguous" if ambiguous else "exact",
                    missing_fields_json=sorted({f for c in group for f in c.missing_fields}),
                    created_at=now,
                    updated_at=now,
                )
                session.add(obligation)
                await session.flush()
            else:
                obligation.verification_state = state.value
                obligation.updated_at = now
                obligation.confidence = max(obligation.confidence, max(c.confidence for c in group))
            created.append(obligation)
            claim_rows: list[Claim] = []
            for candidate in group:
                obs = next(
                    (
                        o
                        for o in observations
                        if o.source_reference in candidate.source_reference
                        or candidate.source_reference.startswith(o.source_reference)
                    ),
                    observations[0],
                )
                claim = Claim(
                    id=new_id("clm"),
                    user_id=user_id,
                    obligation_id=obligation.id,
                    observation_id=obs.id,
                    field_name="due_at",
                    value=candidate.due_at.isoformat() if candidate.due_at else "unspecified",
                    source_type=candidate.source_type.value,
                    source_authority=candidate.source_authority.value,
                    observed_at=candidate.source_observed_at,
                    confidence=candidate.confidence,
                    evidence_excerpt=candidate.evidence_excerpt[:400],
                    discarded=False,
                    created_at=now,
                )
                session.add(claim)
                claim_rows.append(claim)
            await session.flush()
            if conflicted and len(claim_rows) >= 2:
                conflicts += 1
                session.add(
                    ConflictingClaim(
                        id=new_id("cnf"),
                        user_id=user_id,
                        obligation_id=obligation.id,
                        claim_a_id=claim_rows[0].id,
                        claim_b_id=claim_rows[1].id,
                        field_name="due_at",
                        reason_code="deadline_mismatch",
                        recommended_action="Human decision required. Do not guess.",
                        clarification_draft=_clarification_draft(obligation, claim_rows),
                        created_at=now,
                    )
                )
        uncertainty = f"conflicts={conflicts}" if conflicts else None
        return AgentRunState.PASSED, f"obligations={len(created)}", uncertainty

    await run_agent(
        session,
        user_id=user_id,
        request_id=request_id,
        agent=AgentName.VERIFIER,
        assignment="Deduplicate claims and escalate material contradictions",
        tool_name="verify-deadlines",
        handover_to=AgentName.PLANNER.value,
        work=verify_work,
    )
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=request_id,
        agent=AgentName.VERIFIER.value,
        event_type="verification",
        summary=f"{len(created)} obligations verified or escalated; {conflicts} conflicts.",
        result="conflict" if conflicts else "ok",
    )
    return {
        "obligations": len(created),
        "conflicts": conflicts,
        "injection_ignored": sorted(set(injection_hits)),
        "adapter": adapter.mode,
    }


def _clarification_draft(obligation: Obligation, claims: list[Claim]) -> str:
    lines = [
        f"Subject: Clarification on {obligation.title} ({obligation.course_or_context})",
        "",
        "Hello,",
        "",
        "TermPilot found two different deadlines for this work and will not guess.",
        "",
    ]
    for claim in claims:
        lines.append(
            f"- {claim.source_type} ({claim.source_authority}) observed "
            f"{claim.observed_at.isoformat()} states {claim.value}"
        )
    lines += [
        "",
        "Please confirm the authoritative deadline. This message has not been sent.",
        "",
        "Frank Van Laarhoven",
    ]
    return "\n".join(lines)


async def generate_plan(session: AsyncSession, user_id: str, request_id: str) -> Plan:
    prefs = (
        await session.execute(select(StudentPreference).where(StudentPreference.user_id == user_id))
    ).scalar_one()
    obligations = (
        (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
        .scalars()
        .all()
    )
    events = await _calendar.list_events(session, user_id)
    busy = [
        FixedBusy(title=e.title, start=e.start_at, end=e.end_at, kind=e.kind)
        for e in events
        if not e.rolled_back
    ]
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
    conflict_ids = {c.obligation_id for c in conflicts}

    records: list[dict[str, Any]] = []
    for obl in obligations:
        if obl.type not in {
            ObligationType.ASSIGNMENT.value,
            ObligationType.RECRUITING.value,
            ObligationType.EXAM.value,
        }:
            continue
        if obl.status == ObligationStatus.COMPLETE.value:
            continue
        conservative = obl.due_at
        if obl.id in conflict_ids:
            claims = (
                (await session.execute(select(Claim).where(Claim.obligation_id == obl.id)))
                .scalars()
                .all()
            )
            dated = [datetime.fromisoformat(c.value) for c in claims if c.value != "unspecified"]
            if dated:
                conservative = min(dated)
        records.append(
            {
                "id": obl.id,
                "title": obl.title,
                "course_or_context": obl.course_or_context,
                "due_at": obl.due_at,
                "estimated_minutes": obl.estimated_minutes,
                "priority": obl.priority,
                "verification_state": obl.verification_state,
                "conservative_due": conservative,
            }
        )

    result_holder: dict[str, Any] = {}

    async def work(_run: Any) -> tuple[AgentRunState, str, str | None]:
        planning = solve_from_records(
            records,
            busy,
            {
                "weekly_study_limit_hours": prefs.weekly_study_limit_hours,
                "max_study_block_minutes": prefs.max_study_block_minutes,
                "break_minutes": prefs.break_minutes,
                "sleep_start": prefs.sleep_start,
                "sleep_end": prefs.sleep_end,
                "preferred_windows_json": prefs.preferred_windows_json,
            },
        )
        result_holder["planning"] = planning
        state = AgentRunState.PASSED if planning.feasible else AgentRunState.DEGRADED
        return state, f"feasible={planning.feasible}", None if planning.feasible else "infeasible"

    await run_agent(
        session,
        user_id=user_id,
        request_id=request_id,
        agent=AgentName.PLANNER,
        assignment="Build a feasible 14-day plan with CP-SAT",
        tool_name="build-feasible-plan",
        handover_to=AgentName.GUARDIAN.value,
        work=work,
    )
    planning = result_holder["planning"]
    now = clock.now()
    plan = Plan(
        id=new_id("pln"),
        user_id=user_id,
        horizon_start=now,
        horizon_end=clock.horizon_end(now),
        feasible=planning.feasible,
        risk_level=planning.risk_level.value,
        explanation=planning.explanation,
        unscheduled_json=planning.unscheduled,
        violated_soft_json=planning.violated_soft,
        unsatisfied_hard_json=planning.unsatisfied_hard,
        created_at=now,
    )
    session.add(plan)
    await session.flush()
    for event in events:
        if event.rolled_back:
            continue
        session.add(
            PlanBlock(
                id=new_id("blk"),
                plan_id=plan.id,
                user_id=user_id,
                obligation_id=None,
                kind=event.kind if event.kind in {k.value for k in PlanBlockKind} else "fixed",
                title=event.title,
                start_at=event.start_at,
                end_at=event.end_at,
                state=PlanBlockState.EXISTING.value,
                reason="Imported from the authorised calendar. Immovable.",
                calendar_uid=event.uid,
            )
        )
    for block in planning.blocks:
        session.add(
            PlanBlock(
                id=new_id("blk"),
                plan_id=plan.id,
                user_id=user_id,
                obligation_id=block.get("obligation_id"),
                kind=PlanBlockKind.STUDY.value,
                title=block["title"],
                start_at=datetime.fromisoformat(block["start_at"]),
                end_at=datetime.fromisoformat(block["end_at"]),
                state=PlanBlockState.PROPOSED.value,
                reason=block.get("reason") or "",
            )
        )
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=request_id,
        agent=AgentName.PLANNER.value,
        event_type="plan_generated",
        object_type="plan",
        object_id=plan.id,
        summary=planning.explanation[:400],
        result="ok" if planning.feasible else "infeasible",
    )
    return plan


async def propose_calendar_write(
    session: AsyncSession, user_id: str, request_id: str, plan: Plan
) -> ApprovalRequest | None:
    blocks = (
        (
            await session.execute(
                select(PlanBlock).where(
                    PlanBlock.plan_id == plan.id, PlanBlock.state == PlanBlockState.PROPOSED.value
                )
            )
        )
        .scalars()
        .all()
    )
    if not blocks:
        return None
    now = clock.now()
    diff = {
        "create": [
            {
                "id": b.id,
                "title": b.title,
                "start_at": b.start_at.isoformat(),
                "end_at": b.end_at.isoformat(),
                "kind": b.kind,
            }
            for b in blocks
        ],
        "delete": [],
        "target": "demo_calendar",
    }

    async def work(_run: Any) -> tuple[AgentRunState, str, str | None]:
        try:
            await require_consent(session, user_id, ConsentPurpose.CALENDAR_WRITE)
        except ConsentError as exc:
            return AgentRunState.BLOCKED, "consent_missing", str(exc)
        return AgentRunState.PASSED, f"preview={len(blocks)}", None

    run = await run_agent(
        session,
        user_id=user_id,
        request_id=request_id,
        agent=AgentName.GUARDIAN,
        assignment="Preview demo-calendar writes and require approval",
        tool_name="safe-calendar-write",
        work=work,
    )
    if run.state == AgentRunState.BLOCKED.value:
        return None
    approval = ApprovalRequest(
        id=new_id("apr"),
        user_id=user_id,
        action_type="calendar_write",
        target_system="demo_calendar",
        reason="Add proposed study blocks to the demo calendar.",
        diff_json=diff,
        state=ApprovalState.PENDING.value,
        idempotency_key=f"calwrite-{plan.id}",
        reversible=True,
        expires_at=now + timedelta(minutes=get_settings().approval_ttl_minutes),
        created_at=now,
    )
    session.add(approval)
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=request_id,
        agent=AgentName.GUARDIAN.value,
        event_type="approval_requested",
        object_type="approval",
        object_id=approval.id,
        approval_state=approval.state,
        policy_check="human_in_the_loop",
        summary="Calendar write withheld pending explicit approval.",
    )
    return approval


async def reconcile(
    session: AsyncSession,
    user_id: str,
    goal: str,
    simulate_lms_outage: bool = False,
) -> OrchestratorOut:
    request_id = new_id("req")
    now = clock.now()
    from app.domain.models import OrchestratorRequest

    verdict = inspect_user_goal(goal)
    if verdict.decision == GuardianDecision.BLOCK:
        await record_audit(
            session,
            user_id=user_id,
            correlation_id=request_id,
            agent=AgentName.GUARDIAN.value,
            event_type="goal_blocked",
            result="blocked",
            policy_check=verdict.reason_code,
            summary=verdict.summary,
        )
        row = OrchestratorRequest(
            id=request_id,
            user_id=user_id,
            goal=goal,
            delegated_json=[],
            results_json={"guardian": verdict.model_dump()},
            uncertainties_json=[],
            proposed_actions_json=[],
            approval_state="blocked",
            final_status="blocked",
            created_at=now,
            finished_at=clock.now(),
        )
        session.add(row)
        return OrchestratorOut(
            request_id=request_id,
            delegated_tasks=[],
            bot_results={"guardian": verdict.model_dump()},
            unresolved_uncertainties=[],
            proposed_actions=[],
            approval_state="blocked",
            final_status="blocked",
        )

    async def orch_work(_run: Any) -> tuple[AgentRunState, str, str | None]:
        return AgentRunState.RUNNING, "delegated", None

    await run_agent(
        session,
        user_id=user_id,
        request_id=request_id,
        agent=AgentName.ORCHESTRATOR,
        assignment="Decompose the student goal and never bypass Guardian or Verifier",
        tool_name="delegate",
        work=orch_work,
    )

    sync_summary = await sync_sources(session, user_id, request_id, simulate_lms_outage)
    verify_summary = await extract_and_verify(session, user_id, request_id)
    plan = await generate_plan(session, user_id, request_id)
    approval = await propose_calendar_write(session, user_id, request_id, plan)
    uncertainties: list[str] = []
    if verify_summary["conflicts"]:
        uncertainties.append("deadline_conflict_requires_human")
    if verify_summary["injection_ignored"]:
        uncertainties.append("prompt_injection_ignored")
    if not plan.feasible:
        uncertainties.append("plan_infeasible")
    for name, info in sync_summary.items():
        if info["status"] != "healthy":
            uncertainties.append(f"source_degraded:{name}")

    proposed = []
    if approval is not None:
        proposed.append(
            {
                "type": "calendar_write",
                "approval_id": approval.id,
                "target": "demo_calendar",
                "state": approval.state,
            }
        )
    row = OrchestratorRequest(
        id=request_id,
        user_id=user_id,
        goal=goal,
        delegated_json=[
            {"bot": "scout", "task": "inspect_and_extract"},
            {"bot": "verifier", "task": "dedupe_and_conflict"},
            {"bot": "planner", "task": "cp_sat_plan"},
            {"bot": "guardian", "task": "approval_gate"},
        ],
        results_json={
            "sync": sync_summary,
            "verify": verify_summary,
            "plan_id": plan.id,
            "feasible": plan.feasible,
        },
        uncertainties_json=uncertainties,
        proposed_actions_json=proposed,
        approval_state=approval.state if approval else "not_required",
        final_status="awaiting_approval" if approval else "completed",
        created_at=now,
        finished_at=clock.now(),
    )
    session.add(row)
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=request_id,
        agent=AgentName.ORCHESTRATOR.value,
        event_type="orchestration_complete",
        summary="Specialist bots completed bounded roles. Calendar write withheld.",
        result=row.final_status,
        approval_state=row.approval_state,
    )
    return OrchestratorOut(
        request_id=request_id,
        delegated_tasks=row.delegated_json,
        bot_results=row.results_json,
        unresolved_uncertainties=uncertainties,
        proposed_actions=proposed,
        approval_state=row.approval_state,
        final_status=row.final_status,
    )


async def resolve_conflict(
    session: AsyncSession,
    user_id: str,
    conflict_id: str,
    resolution: ConflictResolution,
    note: str | None = None,
) -> ConflictingClaim:
    conflict = (
        await session.execute(
            select(ConflictingClaim).where(
                ConflictingClaim.id == conflict_id, ConflictingClaim.user_id == user_id
            )
        )
    ).scalar_one()
    obligation = (
        await session.execute(select(Obligation).where(Obligation.id == conflict.obligation_id))
    ).scalar_one()
    claim_a = (
        await session.execute(select(Claim).where(Claim.id == conflict.claim_a_id))
    ).scalar_one()
    claim_b = (
        await session.execute(select(Claim).where(Claim.id == conflict.claim_b_id))
    ).scalar_one()
    now = clock.now()
    conflict.resolution = resolution.value
    conflict.resolved_at = now
    if note:
        conflict.clarification_draft = note
    if resolution == ConflictResolution.ACCEPT_A:
        obligation.due_at = datetime.fromisoformat(claim_a.value)
        obligation.verification_state = VerificationState.VERIFIED.value
        claim_b.discarded = True
    elif resolution == ConflictResolution.ACCEPT_B:
        obligation.due_at = datetime.fromisoformat(claim_b.value)
        obligation.verification_state = VerificationState.VERIFIED.value
        claim_a.discarded = True
    elif resolution == ConflictResolution.REJECT_EXTRACTION:
        obligation.verification_state = VerificationState.REJECTED.value
        obligation.status = ObligationStatus.CANCELLED.value
    else:
        obligation.verification_state = VerificationState.CONFLICTED.value
    obligation.updated_at = now
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=conflict.id,
        event_type="conflict_resolved",
        object_type="conflict",
        object_id=conflict.id,
        summary=f"Student chose {resolution.value}.",
        result="ok",
    )
    return conflict


async def decide_approval(
    session: AsyncSession, user_id: str, approval_id: str, approve: bool
) -> ApprovalRequest:
    approval = (
        await session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.id == approval_id, ApprovalRequest.user_id == user_id
            )
        )
    ).scalar_one()
    now = clock.now()
    if approval.state != ApprovalState.PENDING.value:
        raise ApprovalError("not_pending", "This approval is not pending.")
    if approval.expires_at <= now:
        approval.state = ApprovalState.EXPIRED.value
        raise ApprovalError("approval_expired", "This approval has expired.")
    approval.decided_at = now
    approval.state = ApprovalState.APPROVED.value if approve else ApprovalState.REJECTED.value
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=approval.id,
        event_type="approval_decision",
        object_type="approval",
        object_id=approval.id,
        approval_state=approval.state,
        summary="Approved." if approve else "Rejected.",
    )
    return approval


async def apply_calendar(session: AsyncSession, user_id: str, approval_id: str) -> dict[str, Any]:
    approval = (
        await session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.id == approval_id, ApprovalRequest.user_id == user_id
            )
        )
    ).scalar_one()
    assert_usable(approval)
    await require_consent(session, user_id, ConsentPurpose.CALENDAR_WRITE)
    if approval.state == ApprovalState.APPLIED.value:
        return {"status": "idempotent", "created": 0, "approval_id": approval.id}
    try:
        created = await _calendar.apply_blocks(
            session,
            user_id,
            approval.diff_json.get("create", []),
            approval.id,
            approval.idempotency_key,
        )
    except CalendarWriteError as exc:
        await record_audit(
            session,
            user_id=user_id,
            correlation_id=approval.id,
            event_type="calendar_write",
            result="failed",
            summary=str(exc),
        )
        raise
    approval.state = ApprovalState.APPLIED.value
    approval.applied_at = clock.now()
    approval.rollback_json = {
        "event_ids": [e.id for e in created],
        "uids": [e.uid for e in created],
    }
    for item in approval.diff_json.get("create", []):
        block = await session.get(PlanBlock, item["id"])
        if block is not None:
            block.state = PlanBlockState.APPROVED.value
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=approval.id,
        event_type="calendar_write",
        object_type="approval",
        object_id=approval.id,
        approval_state=approval.state,
        result="ok",
        summary=f"Wrote {len(created)} events to the demo calendar.",
    )
    return {
        "status": "applied",
        "created": len(created),
        "approval_id": approval.id,
        "rollback": approval.rollback_json,
    }


async def rollback_calendar(
    session: AsyncSession, user_id: str, approval_id: str
) -> dict[str, Any]:
    approval = (
        await session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.id == approval_id, ApprovalRequest.user_id == user_id
            )
        )
    ).scalar_one()
    if approval.state != ApprovalState.APPLIED.value:
        raise ApprovalError("not_applied", "Nothing to roll back.")
    count = await _calendar.rollback(session, approval.id)
    approval.state = ApprovalState.ROLLED_BACK.value
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=approval.id,
        event_type="calendar_rollback",
        object_type="approval",
        object_id=approval.id,
        approval_state=approval.state,
        summary=f"Rolled back {count} demo calendar events.",
    )
    return {"status": "rolled_back", "count": count, "approval_id": approval.id}
