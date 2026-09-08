"""HTTP routes for the TermPilot MVP."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.monitor import run_monitor
from app.api.deps import current_user_id, db_session
from app.domain.ids import new_id
from app.domain.models import (
    AgentRun,
    ApprovalRequest,
    AuditEvent,
    CalendarEvent,
    Claim,
    ConflictingClaim,
    EvaluationSession,
    Obligation,
    Plan,
    PlanBlock,
    SourceConnection,
    SourceObservation,
)
from app.domain.schemas import (
    ApprovalCreateIn,
    CommandIn,
    ConflictResolveIn,
    EvaluationSessionIn,
    HealthOut,
    ReadyOut,
)
from app.policies.approval import ApprovalError
from app.policies.consent import ConsentError
from app.services import clock
from app.services.collaborate import invite as collab_invite
from app.services.collaborate import list_invites
from app.services.collaborate import me as current_profile
from app.services.demo import prepare_student_workspace, reset_demo, seed_user
from app.services.feeds import assemble_feeds
from app.services.grokbot import catalog as grokbot_catalog
from app.services.identity import (
    display_name_from_email,
    is_demo_email,
    university_email_error,
    user_id_from_email,
)
from app.services.mailbox import cleanup_mailbox, draft_from_item, mailbox_desk
from app.services.pipeline import (
    apply_calendar,
    decide_approval,
    generate_plan,
    propose_calendar_write,
    reconcile,
    resolve_conflict,
    rollback_calendar,
    sync_sources,
)
from app.services.queries import (
    attention_queue,
    control_tower,
    demo_metrics,
    graph_payload,
    impact_bundle,
)
from app.services.voicebridge import (
    approval_voice_prompt,
    delete_transcripts,
    handle_turn,
    list_turns,
    synthesise,
)
from app.services.voicebridge import (
    registry as voice_registry,
)
from app.services.workspace import (
    connect_all,
    connect_connector,
    disconnect_connector,
    draft_email,
    oauth_start,
    organise_notes,
    run_workflow,
    send_approved_message,
    workspace_bundle,
)
from app.services.world import fx_convert, weather_week, world_clock
from app.settings import get_settings
from app.storage.database import get_engine

router = APIRouter()


class SessionBootstrapIn(BaseModel):
    email: str
    password: str | None = None
    display_name: str | None = None
    access_code: str | None = None
    jobs: list[str] | None = None
    tools: list[str] | None = None
    foci: list[str] | None = None


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    settings = get_settings()
    return HealthOut(
        status="ok",
        mode=settings.env,
        grok=settings.grok_connection_state,
        time=clock.now(),
        access_code_required=bool(settings.access_code),
        student_login=True,
        password_required=True,
        email_verification=settings.strict_auth,
        mfa=settings.strict_auth,
        mail="resend" if settings.resend_api_key else "unset",
        mail_from=settings.auth_from_email,
    )


@router.get("/ready", response_model=ReadyOut)
async def ready() -> ReadyOut:
    settings = get_settings()
    db_state = "ok"
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        db_state = f"error:{type(exc).__name__}"
    fixtures_ok = (settings.fixtures_root / "expected" / "reconciliation.json").exists()
    return ReadyOut(
        ready=db_state == "ok" and fixtures_ok,
        database=db_state,
        fixtures=fixtures_ok,
        grok=settings.grok_connection_state,
    )


@router.post("/demo/reset")
async def demo_reset() -> dict[str, Any]:
    settings = get_settings()
    if settings.env == "production":
        raise HTTPException(status_code=403, detail="demo reset is disabled in production")
    result = await reset_demo()
    return {"status": "reset", **result}


@router.post("/session/bootstrap")
async def session_bootstrap(
    body: SessionBootstrapIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    settings = get_settings()
    email = body.email.strip().lower()
    problem = university_email_error(email)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    if settings.access_code and not is_demo_email(email):
        if (body.access_code or "") != settings.access_code:
            raise HTTPException(status_code=403, detail="Enter the classroom access code.")
    from app.domain.models import UserProfile
    from app.services.auth import (
        DEMO_PASSWORD,
        GENERIC_REGISTER,
        attach_session_cookie,
        cache_guard,
        create_session,
        hash_password,
        issue_otp,
        password_error,
        verify_password,
    )

    cache_guard(response)

    password = (body.password or "").strip()
    user_id = user_id_from_email(email)
    display = body.display_name or display_name_from_email(email)
    existing = await session.get(UserProfile, user_id)
    if existing is None:
        problem = password_error(password)
        if problem:
            raise HTTPException(status_code=400, detail=problem)
        seeded = await seed_user(
            session,
            user_id=user_id,
            display_name=display,
            email=email,
            password=password,
        )
    else:
        stored = existing.password_hash
        if stored:
            allowed = verify_password(password, stored)
            if not allowed and is_demo_email(email) and password == DEMO_PASSWORD:
                allowed = True
            if not allowed:
                raise HTTPException(status_code=401, detail="Email or password is incorrect.")
        else:
            if password:
                problem = password_error(password)
                if problem:
                    raise HTTPException(status_code=400, detail=problem)
                existing.password_hash = hash_password(password)
                existing.updated_at = clock.now()
            elif settings.env == "production":
                raise HTTPException(
                    status_code=401,
                    detail="This account needs a password. Choose one of at least 8 characters.",
                )
        seeded = {
            "user_id": existing.id,
            "display_name": existing.display_name,
            "created": False,
        }
    profile_row = existing or await session.get(UserProfile, user_id)
    if (
        settings.codes_required
        and not is_demo_email(email)
        and profile_row is not None
        and not profile_row.email_verified_at
    ):
        await issue_otp(
            session,
            user_id=user_id,
            dest=email,
            channel="email",
            purpose="signup",
        )
        return {"status": "verify_email", "detail": GENERIC_REGISTER}
    token = await create_session(session, user_id, request)
    attach_session_cookie(response, token)
    try:
        prepared = await prepare_student_workspace(session, user_id)
    except Exception:  # noqa: BLE001
        prepared = {
            "connected": 0,
            "reconciled": False,
            "obligations": 0,
            "public_demo": True,
        }
    profile = await current_profile(session, user_id)
    return {
        "status": "ok",
        "created": bool(seeded.get("created")),
        **profile,
        "jobs": body.jobs or [],
        "tools": body.tools or [],
        "foci": body.foci or [],
        "prepared": prepared,
        "welcome": (
            "Grok Bot is ready with a live demo workspace. Fixture adapters are connected so you "
            "can test mail, week, news, automations and Ask. Live Gmail/Outlook starts when "
            "provider keys are set. Guardian blocks assessed-work completion. Calendar and "
            "outbound mail still need on-screen approval."
        ),
    }


@router.post("/session/prepare")
async def session_prepare(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    result = await prepare_student_workspace(session, user_id)
    return {"status": "ok", **result}


@router.get("/tower")
async def tower(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    tower_out = await control_tower(session, user_id)
    queue = await attention_queue(session, user_id)
    return {"tower": tower_out.model_dump(mode="json"), "attention": queue}


@router.post("/sources/sync")
async def sources_sync(
    simulate_lms_outage: bool = False,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    request_id = new_id("req")
    summary = await sync_sources(session, user_id, request_id, simulate_lms_outage)
    return {"request_id": request_id, "sources": summary}


@router.get("/sources")
async def list_sources(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    connections = (
        (await session.execute(select(SourceConnection).where(SourceConnection.user_id == user_id)))
        .scalars()
        .all()
    )
    observations = (
        (
            await session.execute(
                select(SourceObservation)
                .where(SourceObservation.user_id == user_id)
                .order_by(SourceObservation.observed_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "connections": [
            {
                "id": c.id,
                "source_type": c.source_type,
                "label": c.label,
                "health": c.health,
                "permission_state": c.permission_state,
                "last_success_at": c.last_success_at.isoformat() if c.last_success_at else None,
                "last_error_code": c.last_error_code,
                "last_error_message": c.last_error_message,
                "degraded_mode": c.degraded_mode,
            }
            for c in connections
        ],
        "observations": [
            {
                "id": o.id,
                "source_type": o.source_type,
                "source_reference": o.source_reference,
                "source_authority": o.source_authority,
                "observed_at": o.observed_at.isoformat(),
                "excerpt": o.excerpt,
                "injection_flagged": o.injection_flagged,
                "stale": False,
            }
            for o in observations
        ],
    }


@router.get("/obligations")
async def list_obligations(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    rows = (
        (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
        .scalars()
        .all()
    )
    return {"items": [_obligation_dict(o) for o in rows]}


@router.get("/obligations/{obligation_id}")
async def get_obligation(
    obligation_id: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    row = await session.get(Obligation, obligation_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(404, "obligation_not_found")
    claims = (
        (await session.execute(select(Claim).where(Claim.obligation_id == obligation_id)))
        .scalars()
        .all()
    )
    blocks = (
        (await session.execute(select(PlanBlock).where(PlanBlock.obligation_id == obligation_id)))
        .scalars()
        .all()
    )
    return {
        "obligation": _obligation_dict(row),
        "claims": [_claim_dict(c) for c in claims],
        "plan_blocks": [_block_dict(b) for b in blocks],
    }


@router.post("/obligations/{obligation_id}/complete")
async def complete_obligation(
    obligation_id: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    row = await session.get(Obligation, obligation_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(404, "obligation_not_found")
    row.status = "complete"
    row.updated_at = clock.now()
    return {"obligation": _obligation_dict(row)}


@router.get("/conflicts")
async def list_conflicts(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    rows = (
        (await session.execute(select(ConflictingClaim).where(ConflictingClaim.user_id == user_id)))
        .scalars()
        .all()
    )
    items = []
    for conflict in rows:
        claim_a = await session.get(Claim, conflict.claim_a_id)
        claim_b = await session.get(Claim, conflict.claim_b_id)
        obligation = await session.get(Obligation, conflict.obligation_id)
        items.append(
            {
                "id": conflict.id,
                "obligation_id": conflict.obligation_id,
                "title": obligation.title if obligation else "",
                "field_name": conflict.field_name,
                "reason_code": conflict.reason_code,
                "recommended_action": conflict.recommended_action,
                "resolution": conflict.resolution,
                "clarification_draft": conflict.clarification_draft,
                "claim_a": _claim_dict(claim_a) if claim_a else None,
                "claim_b": _claim_dict(claim_b) if claim_b else None,
            }
        )
    return {"items": items}


@router.post("/conflicts/{conflict_id}/resolve")
async def conflict_resolve(
    conflict_id: str,
    body: ConflictResolveIn,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        row = await resolve_conflict(session, user_id, conflict_id, body.resolution, body.note)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(404, str(exc)) from exc
    return {"id": row.id, "resolution": row.resolution}


@router.post("/plans/generate")
async def plans_generate(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    request_id = new_id("req")
    plan = await generate_plan(session, user_id, request_id)
    approval = await propose_calendar_write(session, user_id, request_id, plan)
    return {
        "plan": await _plan_dict(session, plan),
        "approval_id": approval.id if approval else None,
    }


@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    plan = await session.get(Plan, plan_id)
    if plan is None or plan.user_id != user_id:
        raise HTTPException(404, "plan_not_found")
    return {"plan": await _plan_dict(session, plan)}


@router.get("/plans")
async def list_plans(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    plan = (
        (
            await session.execute(
                select(Plan).where(Plan.user_id == user_id).order_by(Plan.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
    if plan is None:
        return {"plan": None}
    return {"plan": await _plan_dict(session, plan)}


@router.post("/approvals")
async def create_approval(
    body: ApprovalCreateIn,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    if not body.plan_id:
        raise HTTPException(400, "plan_id_required")
    plan = await session.get(Plan, body.plan_id)
    if plan is None or plan.user_id != user_id:
        raise HTTPException(404, "plan_not_found")
    approval = await propose_calendar_write(session, user_id, new_id("req"), plan)
    if approval is None:
        raise HTTPException(409, "nothing_to_approve")
    return _approval_dict(approval)


@router.get("/approvals")
async def list_approvals(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    rows = (
        (
            await session.execute(
                select(ApprovalRequest)
                .where(ApprovalRequest.user_id == user_id)
                .order_by(ApprovalRequest.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {"items": [_approval_dict(a) for a in rows]}


@router.post("/approvals/{approval_id}/approve")
async def approval_approve(
    approval_id: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        row = await decide_approval(session, user_id, approval_id, True)
    except ApprovalError as exc:
        raise HTTPException(409, exc.code) from exc
    return _approval_dict(row)


@router.post("/approvals/{approval_id}/reject")
async def approval_reject(
    approval_id: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        row = await decide_approval(session, user_id, approval_id, False)
    except ApprovalError as exc:
        raise HTTPException(409, exc.code) from exc
    return _approval_dict(row)


@router.post("/calendar/apply")
async def calendar_apply(
    approval_id: str = Query(...),
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await apply_calendar(session, user_id, approval_id)
    except ApprovalError as exc:
        raise HTTPException(409, exc.code) from exc
    except ConsentError as exc:
        raise HTTPException(403, exc.code) from exc


@router.post("/calendar/rollback")
async def calendar_rollback(
    approval_id: str = Query(...),
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await rollback_calendar(session, user_id, approval_id)
    except ApprovalError as exc:
        raise HTTPException(409, exc.code) from exc


@router.get("/calendar")
async def list_calendar(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    rows = (
        (
            await session.execute(
                select(CalendarEvent).where(
                    CalendarEvent.user_id == user_id, CalendarEvent.rolled_back.is_(False)
                )
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": e.id,
                "uid": e.uid,
                "title": e.title,
                "start_at": e.start_at.isoformat(),
                "end_at": e.end_at.isoformat(),
                "kind": e.kind,
                "written_by_termpilot": e.written_by_termpilot,
                "approval_id": e.approval_id,
            }
            for e in rows
        ]
    }


@router.get("/agent-runs")
async def list_agent_runs(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    rows = (
        (
            await session.execute(
                select(AgentRun)
                .where(AgentRun.user_id == user_id)
                .order_by(AgentRun.started_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "request_id": r.request_id,
                "agent": r.agent,
                "assignment": r.assignment,
                "state": r.state,
                "source_inspected": r.source_inspected,
                "tool_name": r.tool_name,
                "output_artifact": r.output_artifact,
                "handover_to": r.handover_to,
                "error_or_uncertainty": r.error_or_uncertainty,
                "duration_ms": r.duration_ms,
                "started_at": r.started_at.isoformat(),
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in rows
        ]
    }


@router.get("/audit-events")
async def list_audit_events(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    rows = (
        (
            await session.execute(
                select(AuditEvent)
                .where(AuditEvent.user_id == user_id)
                .order_by(AuditEvent.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": e.id,
                "correlation_id": e.correlation_id,
                "agent": e.agent,
                "event_type": e.event_type,
                "object_type": e.object_type,
                "object_id": e.object_id,
                "result": e.result,
                "confidence": e.confidence,
                "policy_check": e.policy_check,
                "approval_state": e.approval_state,
                "summary": e.summary,
                "created_at": e.created_at.isoformat(),
            }
            for e in rows
        ]
    }


@router.get("/grokbot/tools")
async def grokbot_tools() -> dict[str, Any]:
    return grokbot_catalog()


@router.post("/command")
async def run_command(
    body: CommandIn,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    result = await reconcile(session, user_id, body.text, body.simulate_lms_outage)
    return result.model_dump(mode="json")


@router.post("/monitor/run")
async def monitor_run(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await run_monitor(session, user_id)


@router.post("/evaluation/session")
async def evaluation_session(
    body: EvaluationSessionIn,
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    row = EvaluationSession(
        id=new_id("evs"),
        participant_code=body.participant_code,
        kind=body.kind,
        planning_time_minutes=body.planning_time_minutes,
        deadline_surprise=body.deadline_surprise,
        verified_action_rate=body.verified_action_rate,
        survey_json=body.survey,
        notes=body.notes,
        created_at=clock.now(),
    )
    session.add(row)
    return {"id": row.id, "kind": row.kind}


@router.get("/metrics/demo")
async def metrics_demo(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await demo_metrics(session, user_id)


@router.get("/metrics/impact")
async def metrics_impact(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await impact_bundle(session, user_id)


@router.get("/graph")
async def ontology_graph(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await graph_payload(session, user_id)


@router.get("/workspace")
async def get_workspace(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await workspace_bundle(session, user_id)


class ConnectAllIn(BaseModel):
    ids: list[str] | None = None


@router.post("/connectors/connect-all")
async def connectors_connect_all(
    body: ConnectAllIn = ConnectAllIn(),
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await connect_all(session, user_id, body.ids)


@router.get("/connectors/{connector_id}/oauth/start")
async def connector_oauth_start(connector_id: str) -> dict[str, Any]:
    try:
        return oauth_start(connector_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/connectors/{connector_id}/connect")
async def connector_connect(
    connector_id: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await connect_connector(session, user_id, connector_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


class OAuthCompleteIn(BaseModel):
    code: str = ""


@router.post("/connectors/{connector_id}/oauth/complete")
async def connector_oauth_complete(
    connector_id: str,
    body: OAuthCompleteIn,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    del body
    try:
        result = await connect_connector(session, user_id, connector_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    result["oauth_code_received"] = True
    result["token_exchanged"] = False
    return result


@router.post("/connectors/{connector_id}/disconnect")
async def connector_disconnect(
    connector_id: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await disconnect_connector(session, user_id, connector_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


class EmailDraftIn(BaseModel):
    to_address: str
    subject: str
    body: str
    channel: str = "email"


@router.post("/workspace/messages/draft")
async def messages_draft(
    body: EmailDraftIn,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await draft_email(
            session, user_id, body.to_address, body.subject, body.body, body.channel
        )
    except ConsentError as exc:
        raise HTTPException(403, exc.code) from exc


@router.post("/workspace/messages/{message_id}/send")
async def messages_send(
    message_id: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await send_approved_message(session, user_id, message_id)
    except ConsentError as exc:
        raise HTTPException(409, exc.code) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/workspace/notes/organise")
async def notes_organise(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await organise_notes(session, user_id)
    except ConsentError as exc:
        raise HTTPException(403, exc.code) from exc


@router.post("/workspace/workflows/{name}/run")
async def workflows_run(
    name: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await run_workflow(session, user_id, name)
    except (LookupError, ConsentError) as exc:
        code = getattr(exc, "code", str(exc))
        raise HTTPException(409, code) from exc


@router.post("/conflicts/{conflict_id}/draft-email")
async def conflict_draft_email(
    conflict_id: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    conflict = await session.get(ConflictingClaim, conflict_id)
    if conflict is None or conflict.user_id != user_id:
        raise HTTPException(404, "conflict_not_found")
    if not conflict.clarification_draft:
        raise HTTPException(409, "no_draft")
    try:
        return await draft_email(
            session,
            user_id,
            "j.okonkwo@northbridge.example",
            "Deadline clarification (not sent)",
            conflict.clarification_draft,
        )
    except ConsentError as exc:
        raise HTTPException(403, exc.code) from exc


class VoiceTurnIn(BaseModel):
    text: str
    language: str = "auto"
    transcript_confidence: float = 1.0
    source: str = "typed"


@router.get("/voicebridge/languages")
async def voice_languages() -> dict[str, Any]:
    return {
        "mvp": voice_registry(),
        "claim": (
            "Interface and conversations are fully localised for every Grok Voice language "
            "(xAI Speech-to-Text supported codes). Canonical dates and module codes stay "
            "untranslated. Speech uses Grok Voice (STT/TTS) when available."
        ),
        "audio_retention_default": False,
        "confidence_threshold": 0.72,
        "stt": "POST https://api.x.ai/v1/stt",
        "tts": "POST https://api.x.ai/v1/tts",
    }


@router.post("/voicebridge/turn")
async def voice_turn(
    body: VoiceTurnIn,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    result = await handle_turn(
        session,
        user_id,
        body.text,
        language=body.language,
        transcript_confidence=body.transcript_confidence,
        source=body.source,
    )
    if result.get("facts", {}).get("handoff") == "orchestrator":
        orch = await reconcile(session, user_id, body.text, False)
        result["orchestrator"] = orch.model_dump(mode="json")
        prompt = await approval_voice_prompt(session, user_id, result["language"])
        result["spoken_text"] = result["spoken_text"] + " " + prompt["spoken_text"]
        result["display_text"] = result["spoken_text"]
        result["requires_on_screen"] = True
    return result


@router.post("/grokbot/turn")
async def grokbot_turn(
    body: VoiceTurnIn,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await voice_turn(body, session, user_id)


@router.get("/voicebridge/turns")
async def voice_turns(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return {"items": await list_turns(session, user_id)}


@router.delete("/voicebridge/transcripts")
async def voice_delete(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await delete_transcripts(session, user_id)


@router.post("/voicebridge/stt")
async def voice_stt(
    language: str = Query("auto"),
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    del session, user_id
    return {
        "ok": False,
        "fallback": "browser",
        "reason": "Upload STT via multipart is available when XAI_API_KEY is set. Browser SpeechRecognition is the demo fallback.",
        "language": language,
        "audio_retained": False,
    }


@router.post("/voicebridge/tts")
async def voice_tts(
    body: VoiceTurnIn,
) -> Response:
    result = await synthesise(body.text, body.language if body.language != "auto" else "en")
    if not result.get("ok"):
        return Response(
            content=b'{"ok":false,"fallback":"browser"}',
            media_type="application/json",
            status_code=200,
        )
    return Response(
        content=result["audio"], media_type=str(result.get("content_type") or "audio/mpeg")
    )


@router.get("/me")
async def get_me(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await current_profile(session, user_id)


class InviteIn(BaseModel):
    to_code: str
    obligation_id: str | None = None
    note: str = ""


@router.get("/collaborate")
async def get_collaborate(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await list_invites(session, user_id)


@router.post("/collaborate/invite")
async def post_invite(
    body: InviteIn,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await collab_invite(session, user_id, body.to_code, body.obligation_id, body.note)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/world-clock")
async def get_world_clock() -> dict[str, Any]:
    return world_clock()


@router.get("/fx")
async def get_fx(
    amount: float = Query(1.0),
    base: str = Query("GBP"),
    quote: str = Query("EUR"),
) -> dict[str, Any]:
    return await fx_convert(amount, base, quote)


@router.get("/weather")
async def get_weather() -> dict[str, Any]:
    try:
        return await weather_week()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, "weather_unavailable") from exc


@router.get("/feeds")
async def get_feeds(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await assemble_feeds(session, user_id)


@router.get("/mailbox")
async def get_mailbox(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await mailbox_desk(session, user_id)
    except ConsentError as exc:
        raise HTTPException(403, exc.code) from exc


@router.post("/mailbox/cleanup")
async def post_mailbox_cleanup(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await cleanup_mailbox(session, user_id)
    except ConsentError as exc:
        raise HTTPException(403, exc.code) from exc


@router.post("/mailbox/{item_id}/draft")
async def post_mailbox_draft(
    item_id: str,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await draft_from_item(session, user_id, item_id)
    except ConsentError as exc:
        raise HTTPException(403, exc.code) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/export")
async def export_user(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    obligations = (
        (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
        .scalars()
        .all()
    )
    return {
        "user_id": user_id,
        "exported_at": clock.now().isoformat(),
        "obligations": [_obligation_dict(o) for o in obligations],
        "note": "Minimum necessary operational export. Raw email bodies are not included.",
    }


@router.delete("/export")
async def delete_user_operational_data(
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    # Demo-only: resetting is the supported delete path.
    del session, user_id
    await reset_demo()
    return {"status": "deleted_via_demo_reset"}


def _obligation_dict(row: Obligation) -> dict[str, Any]:
    return {
        "obligation_id": row.id,
        "user_id": row.user_id,
        "type": row.type,
        "title": row.title,
        "course_or_context": row.course_or_context,
        "description": row.description,
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "estimated_minutes": row.estimated_minutes,
        "priority": row.priority,
        "status": row.status,
        "source_type": row.source_type,
        "source_reference": row.source_reference,
        "source_observed_at": row.source_observed_at.isoformat(),
        "source_authority": row.source_authority,
        "confidence": row.confidence,
        "verification_state": row.verification_state,
        "sensitivity": row.sensitivity,
        "requires_approval": row.requires_approval,
        "fingerprint": row.fingerprint,
        "date_precision": row.date_precision,
        "missing_fields": row.missing_fields_json,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _claim_dict(row: Claim) -> dict[str, Any]:
    return {
        "id": row.id,
        "obligation_id": row.obligation_id,
        "observation_id": row.observation_id,
        "field_name": row.field_name,
        "value": row.value,
        "source_type": row.source_type,
        "source_authority": row.source_authority,
        "observed_at": row.observed_at.isoformat(),
        "confidence": row.confidence,
        "evidence_excerpt": row.evidence_excerpt,
        "discarded": row.discarded,
    }


def _block_dict(row: PlanBlock) -> dict[str, Any]:
    return {
        "id": row.id,
        "plan_id": row.plan_id,
        "obligation_id": row.obligation_id,
        "kind": row.kind,
        "title": row.title,
        "start_at": row.start_at.isoformat(),
        "end_at": row.end_at.isoformat(),
        "state": row.state,
        "reason": row.reason,
        "calendar_uid": row.calendar_uid,
    }


def _approval_dict(row: ApprovalRequest) -> dict[str, Any]:
    return {
        "id": row.id,
        "action_type": row.action_type,
        "target_system": row.target_system,
        "reason": row.reason,
        "diff": row.diff_json,
        "state": row.state,
        "idempotency_key": row.idempotency_key,
        "reversible": row.reversible,
        "expires_at": row.expires_at.isoformat(),
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "applied_at": row.applied_at.isoformat() if row.applied_at else None,
        "rollback": row.rollback_json,
        "created_at": row.created_at.isoformat(),
    }


async def _plan_dict(session: AsyncSession, plan: Plan) -> dict[str, Any]:
    blocks = (
        (await session.execute(select(PlanBlock).where(PlanBlock.plan_id == plan.id)))
        .scalars()
        .all()
    )
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "horizon_start": plan.horizon_start.isoformat(),
        "horizon_end": plan.horizon_end.isoformat(),
        "feasible": plan.feasible,
        "risk_level": plan.risk_level,
        "explanation": plan.explanation,
        "unscheduled": plan.unscheduled_json,
        "violated_soft": plan.violated_soft_json,
        "unsatisfied_hard": plan.unsatisfied_hard_json,
        "created_at": plan.created_at.isoformat(),
        "blocks": [_block_dict(b) for b in blocks],
    }
