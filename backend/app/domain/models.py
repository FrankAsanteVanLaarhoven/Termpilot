"""SQLAlchemy 2 mapped entities. All datetimes are timezone-aware."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class TZDateTime(TypeDecorator[datetime]):
    """SQLite drops tzinfo; restore UTC then convert at the call site as needed."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class Base(DeclarativeBase):
    pass


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(240), nullable=True, default=None, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    email_verified_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True, default=None)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    phone_verified_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True, default=None)
    mfa_sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/London")
    created_at: Mapped[datetime] = mapped_column(TZDateTime())
    updated_at: Mapped[datetime] = mapped_column(TZDateTime())

    consents: Mapped[list[ConsentGrant]] = relationship(back_populates="user")
    preferences: Mapped[StudentPreference | None] = relationship(back_populates="user")


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(40), nullable=True, default=None)
    dest_hash: Mapped[str] = mapped_column(String(80), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    purpose: Mapped[str] = mapped_column(String(24))
    code_hash: Mapped[str] = mapped_column(String(96))
    expires_at: Mapped[datetime] = mapped_column(TZDateTime())
    consumed_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True, default=None)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())
    expires_at: Mapped[datetime] = mapped_column(TZDateTime())
    last_seen_at: Mapped[datetime] = mapped_column(TZDateTime())
    ip_hash: Mapped[str] = mapped_column(String(80), default="")
    revoked_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True, default=None)


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(TZDateTime())
    count: Mapped[int] = mapped_column(Integer, default=0)


class ConsentGrant(Base):
    __tablename__ = "consent_grants"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    purpose: Mapped[str] = mapped_column(String(40))
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    granted_at: Mapped[datetime] = mapped_column(TZDateTime())
    expires_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    scope_note: Mapped[str] = mapped_column(String(240), default="")

    user: Mapped[UserProfile] = relationship(back_populates="consents")


class StudentPreference(Base):
    __tablename__ = "student_preferences"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), unique=True)
    weekly_study_limit_hours: Mapped[int] = mapped_column(Integer, default=20)
    max_study_block_minutes: Mapped[int] = mapped_column(Integer, default=120)
    break_minutes: Mapped[int] = mapped_column(Integer, default=15)
    sleep_start: Mapped[str] = mapped_column(String(8), default="23:00")
    sleep_end: Mapped[str] = mapped_column(String(8), default="07:00")
    preferred_windows_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    commute_minutes: Mapped[int] = mapped_column(Integer, default=30)
    historical_estimate_factor: Mapped[float] = mapped_column(Float, default=1.0)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime())

    user: Mapped[UserProfile] = relationship(back_populates="preferences")


class SourceConnection(Base):
    __tablename__ = "source_connections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    source_type: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(120))
    health: Mapped[str] = mapped_column(String(40), default="healthy")
    permission_state: Mapped[str] = mapped_column(String(40), default="granted")
    last_success_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(400), nullable=True)
    stale_after_minutes: Mapped[int] = mapped_column(Integer, default=180)
    degraded_mode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())

    observations: Mapped[list[SourceObservation]] = relationship(back_populates="connection")


class SourceObservation(Base):
    __tablename__ = "source_observations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    connection_id: Mapped[str] = mapped_column(ForeignKey("source_connections.id"))
    source_type: Mapped[str] = mapped_column(String(40))
    source_reference: Mapped[str] = mapped_column(String(240))
    source_authority: Mapped[str] = mapped_column(String(40), default="primary")
    observed_at: Mapped[datetime] = mapped_column(TZDateTime())
    content_digest: Mapped[str] = mapped_column(String(64))
    excerpt: Mapped[str] = mapped_column(Text, default="")
    raw_retained: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_expires_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    injection_flagged: Mapped[bool] = mapped_column(Boolean, default=False)

    connection: Mapped[SourceConnection] = relationship(back_populates="observations")
    claims: Mapped[list[Claim]] = relationship(back_populates="observation")


class Obligation(Base):
    __tablename__ = "obligations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(240))
    course_or_context: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    due_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=60)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(40), default="not_started")
    source_type: Mapped[str] = mapped_column(String(40))
    source_reference: Mapped[str] = mapped_column(String(240))
    source_observed_at: Mapped[datetime] = mapped_column(TZDateTime())
    source_authority: Mapped[str] = mapped_column(String(40), default="primary")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    verification_state: Mapped[str] = mapped_column(String(40), default="probable")
    sensitivity: Mapped[str] = mapped_column(String(40), default="student_private")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    fingerprint: Mapped[str] = mapped_column(String(160))
    date_precision: Mapped[str] = mapped_column(String(40), default="exact")
    missing_fields_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())
    updated_at: Mapped[datetime] = mapped_column(TZDateTime())

    claims: Mapped[list[Claim]] = relationship(back_populates="obligation")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    obligation_id: Mapped[str | None] = mapped_column(ForeignKey("obligations.id"), nullable=True)
    observation_id: Mapped[str] = mapped_column(ForeignKey("source_observations.id"))
    field_name: Mapped[str] = mapped_column(String(40), default="due_at")
    value: Mapped[str] = mapped_column(String(400))
    source_type: Mapped[str] = mapped_column(String(40))
    source_authority: Mapped[str] = mapped_column(String(40))
    observed_at: Mapped[datetime] = mapped_column(TZDateTime())
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_excerpt: Mapped[str] = mapped_column(Text, default="")
    discarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())

    obligation: Mapped[Obligation | None] = relationship(back_populates="claims")
    observation: Mapped[SourceObservation] = relationship(back_populates="claims")


class ConflictingClaim(Base):
    __tablename__ = "conflicting_claims"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    obligation_id: Mapped[str] = mapped_column(ForeignKey("obligations.id"))
    claim_a_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    claim_b_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    field_name: Mapped[str] = mapped_column(String(40), default="due_at")
    reason_code: Mapped[str] = mapped_column(String(80))
    recommended_action: Mapped[str] = mapped_column(String(240))
    resolution: Mapped[str | None] = mapped_column(String(40), nullable=True)
    clarification_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())
    resolved_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    horizon_start: Mapped[datetime] = mapped_column(TZDateTime())
    horizon_end: Mapped[datetime] = mapped_column(TZDateTime())
    feasible: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="amber")
    explanation: Mapped[str] = mapped_column(Text, default="")
    unscheduled_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    violated_soft_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    unsatisfied_hard_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())

    blocks: Mapped[list[PlanBlock]] = relationship(back_populates="plan")


class PlanBlock(Base):
    __tablename__ = "plan_blocks"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    obligation_id: Mapped[str | None] = mapped_column(ForeignKey("obligations.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(240))
    start_at: Mapped[datetime] = mapped_column(TZDateTime())
    end_at: Mapped[datetime] = mapped_column(TZDateTime())
    state: Mapped[str] = mapped_column(String(40), default="proposed")
    reason: Mapped[str] = mapped_column(Text, default="")
    calendar_uid: Mapped[str | None] = mapped_column(String(120), nullable=True)

    plan: Mapped[Plan] = relationship(back_populates="blocks")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    action_type: Mapped[str] = mapped_column(String(80))
    target_system: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(Text, default="")
    diff_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(40), default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True)
    reversible: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(TZDateTime())
    decided_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    rollback_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())


class ToolAction(Base):
    __tablename__ = "tool_actions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40))
    input_summary: Mapped[str] = mapped_column(String(400), default="")
    output_summary: Mapped[str] = mapped_column(String(400), default="")
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    request_id: Mapped[str] = mapped_column(String(40))
    agent: Mapped[str] = mapped_column(String(40))
    assignment: Mapped[str] = mapped_column(String(240), default="")
    state: Mapped[str] = mapped_column(String(40), default="queued")
    source_inspected: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    output_artifact: Mapped[str | None] = mapped_column(String(120), nullable=True)
    handover_to: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error_or_uncertainty: Mapped[str | None] = mapped_column(String(400), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(TZDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    correlation_id: Mapped[str] = mapped_column(String(40))
    agent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80))
    object_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    object_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    result: Mapped[str] = mapped_column(String(80), default="ok")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    policy_check: Mapped[str | None] = mapped_column(String(80), nullable=True)
    approval_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    summary: Mapped[str] = mapped_column(String(400), default="")
    created_at: Mapped[datetime] = mapped_column(TZDateTime())


class EvaluationSession(Base):
    __tablename__ = "evaluation_sessions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    participant_code: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(40), default="demo")
    planning_time_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadline_surprise: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    verified_action_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    survey_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(TZDateTime())


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (UniqueConstraint("user_id", "uid", name="uq_calendar_user_uid"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    uid: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(240))
    start_at: Mapped[datetime] = mapped_column(TZDateTime())
    end_at: Mapped[datetime] = mapped_column(TZDateTime())
    kind: Mapped[str] = mapped_column(String(40), default="fixed")
    source: Mapped[str] = mapped_column(String(40), default="ics")
    written_by_termpilot: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())


class DemoMetric(Base):
    __tablename__ = "demo_metrics"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), default="demo")
    key: Mapped[str] = mapped_column(String(80))
    value_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_int: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(240), nullable=True)
    label: Mapped[str] = mapped_column(String(160), default="")
    recorded_at: Mapped[datetime] = mapped_column(TZDateTime())


class OrchestratorRequest(Base):
    __tablename__ = "orchestrator_requests"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    goal: Mapped[str] = mapped_column(Text)
    delegated_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    results_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    uncertainties_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    proposed_actions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    approval_state: Mapped[str] = mapped_column(String(40), default="pending")
    final_status: Mapped[str] = mapped_column(String(40), default="running")
    created_at: Mapped[datetime] = mapped_column(TZDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)


class OutboundMessage(Base):
    __tablename__ = "outbound_messages"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    channel: Mapped[str] = mapped_column(String(40), default="email")
    to_address: Mapped[str] = mapped_column(String(240))
    subject: Mapped[str] = mapped_column(String(240), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(String(40), default="draft")
    approval_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())


class WorkspaceNote(Base):
    __tablename__ = "workspace_notes"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    source: Mapped[str] = mapped_column(String(40), default="notion")
    title: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    organised: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    name: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(40), default="running")
    steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)


class MailItem(Base):
    __tablename__ = "mail_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    from_address: Mapped[str] = mapped_column(String(240), default="")
    to_address: Mapped[str] = mapped_column(String(240), default="")
    subject: Mapped[str] = mapped_column(String(240), default="")
    excerpt: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(8), default="p2")
    category: Mapped[str] = mapped_column(String(40), default="newsletter")
    state: Mapped[str] = mapped_column(String(40), default="inbox")
    suggested_action: Mapped[str] = mapped_column(String(40), default="keep")
    observed_at: Mapped[datetime] = mapped_column(TZDateTime())
    archived_at: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)


class CollaborationInvite(Base):
    __tablename__ = "collaboration_invites"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    from_user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    to_code: Mapped[str] = mapped_column(String(40))
    to_name: Mapped[str] = mapped_column(String(120))
    obligation_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    task_title: Mapped[str] = mapped_column(String(240), default="")
    note: Mapped[str] = mapped_column(String(400), default="")
    state: Mapped[str] = mapped_column(String(40), default="pending")
    created_at: Mapped[datetime] = mapped_column(TZDateTime())


class VoiceTurn(Base):
    __tablename__ = "voice_turns"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    language: Mapped[str] = mapped_column(String(16), default="en")
    source: Mapped[str] = mapped_column(String(20), default="typed")
    transcript: Mapped[str] = mapped_column(Text, default="")
    transcript_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    intent: Mapped[str] = mapped_column(String(40), default="ask")
    spoken_text: Mapped[str] = mapped_column(Text, default="")
    display_text: Mapped[str] = mapped_column(Text, default="")
    facts_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    requires_on_screen: Mapped[bool] = mapped_column(Boolean, default=False)
    audio_retained: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime())


class CookieGrant(Base):
    __tablename__ = "cookie_grants"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_hash: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(40), default="")
    necessary: Mapped[bool] = mapped_column(Boolean, default=True)
    analytics: Mapped[bool] = mapped_column(Boolean, default=False)
    export: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_at: Mapped[datetime] = mapped_column(TZDateTime())


class PolicyCache(Base):
    __tablename__ = "policy_cache"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(240), default="")
    version: Mapped[str] = mapped_column(String(40), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    cached_at: Mapped[datetime] = mapped_column(TZDateTime())


class ExportReceipt(Base):
    __tablename__ = "export_receipts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    destination: Mapped[str] = mapped_column(String(40))
    payload_hash: Mapped[str] = mapped_column(String(64), default="")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(40), default="prepared")
    created_at: Mapped[datetime] = mapped_column(TZDateTime())
