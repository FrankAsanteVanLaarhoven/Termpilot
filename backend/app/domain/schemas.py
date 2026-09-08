"""Pydantic v2 API and agent schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    AgentName,
    AgentRunState,
    ApprovalState,
    ConflictResolution,
    GuardianDecision,
    HealthState,
    ObligationStatus,
    ObligationType,
    PermissionState,
    PlanBlockKind,
    PlanBlockState,
    Priority,
    RiskLevel,
    Sensitivity,
    SourceAuthority,
    SourceType,
    VerificationState,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ObligationOut(ORMModel):
    obligation_id: str = Field(validation_alias="id")
    user_id: str
    type: ObligationType
    title: str
    course_or_context: str
    description: str
    due_at: datetime | None
    estimated_minutes: int
    priority: Priority
    status: ObligationStatus
    source_type: SourceType
    source_reference: str
    source_observed_at: datetime
    source_authority: SourceAuthority
    confidence: float
    verification_state: VerificationState
    sensitivity: Sensitivity
    requires_approval: bool
    fingerprint: str
    date_precision: str
    missing_fields: list[str] = Field(validation_alias="missing_fields_json")
    created_at: datetime
    updated_at: datetime


class CandidateObligation(BaseModel):
    title: str
    type: ObligationType = ObligationType.ASSIGNMENT
    course_or_context: str
    description: str = ""
    due_at: datetime | None = None
    estimated_minutes: int = 60
    priority: Priority = Priority.MEDIUM
    source_type: SourceType
    source_reference: str
    source_observed_at: datetime
    source_authority: SourceAuthority = SourceAuthority.PRIMARY
    confidence: float
    date_precision: str = "exact"
    missing_fields: list[str] = Field(default_factory=list)
    evidence_excerpt: str = ""
    fingerprint_hint: str | None = None


class ExtractionResult(BaseModel):
    candidates: list[CandidateObligation]
    evidence_reference: str
    extraction_confidence: float
    missing_fields: list[str] = Field(default_factory=list)
    injection_detected: bool = False
    discarded_instructions: list[str] = Field(default_factory=list)


class ConnectorHealth(BaseModel):
    source_type: SourceType
    label: str
    health: HealthState
    permission_state: PermissionState
    last_success_at: datetime | None = None
    stale: bool = False
    error_code: str | None = None
    error_message: str | None = None
    degraded_mode: str | None = None


class SourceObservationIn(BaseModel):
    source_type: SourceType
    source_reference: str
    source_authority: SourceAuthority
    observed_at: datetime
    excerpt: str
    payload: dict[str, Any] = Field(default_factory=dict)
    content_digest: str
    injection_flagged: bool = False


class ClaimOut(ORMModel):
    id: str
    obligation_id: str | None
    observation_id: str
    field_name: str
    value: str
    source_type: SourceType
    source_authority: SourceAuthority
    observed_at: datetime
    confidence: float
    evidence_excerpt: str
    discarded: bool


class ConflictOut(ORMModel):
    id: str
    obligation_id: str
    claim_a_id: str
    claim_b_id: str
    field_name: str
    reason_code: str
    recommended_action: str
    resolution: str | None
    clarification_draft: str | None
    created_at: datetime
    resolved_at: datetime | None


class ConflictResolveIn(BaseModel):
    resolution: ConflictResolution
    note: str | None = None


class PlanBlockOut(ORMModel):
    id: str
    plan_id: str
    obligation_id: str | None
    kind: PlanBlockKind
    title: str
    start_at: datetime
    end_at: datetime
    state: PlanBlockState
    reason: str
    calendar_uid: str | None


class PlanOut(ORMModel):
    id: str
    user_id: str
    horizon_start: datetime
    horizon_end: datetime
    feasible: bool
    risk_level: RiskLevel
    explanation: str
    unscheduled: list[dict[str, Any]] = Field(validation_alias="unscheduled_json")
    violated_soft: list[str] = Field(validation_alias="violated_soft_json")
    unsatisfied_hard: list[str] = Field(validation_alias="unsatisfied_hard_json")
    created_at: datetime
    blocks: list[PlanBlockOut] = Field(default_factory=list)


class ApprovalOut(ORMModel):
    id: str
    action_type: str
    target_system: str
    reason: str
    diff: dict[str, Any] = Field(validation_alias="diff_json")
    state: ApprovalState
    idempotency_key: str
    reversible: bool
    expires_at: datetime
    decided_at: datetime | None
    applied_at: datetime | None
    rollback: dict[str, Any] | None = Field(validation_alias="rollback_json")
    created_at: datetime


class ApprovalCreateIn(BaseModel):
    action_type: str = "calendar_write"
    target_system: str = "demo_calendar"
    plan_id: str | None = None
    idempotency_key: str | None = None


class AgentRunOut(ORMModel):
    id: str
    request_id: str
    agent: AgentName
    assignment: str
    state: AgentRunState
    source_inspected: str | None
    tool_name: str | None
    output_artifact: str | None
    handover_to: str | None
    error_or_uncertainty: str | None
    duration_ms: int
    started_at: datetime
    finished_at: datetime | None


class AuditEventOut(ORMModel):
    id: str
    correlation_id: str
    agent: str | None
    event_type: str
    object_type: str | None
    object_id: str | None
    result: str
    confidence: float | None
    policy_check: str | None
    approval_state: str | None
    summary: str
    created_at: datetime


class CommandIn(BaseModel):
    text: str
    simulate_lms_outage: bool = False


class OrchestratorOut(BaseModel):
    request_id: str
    delegated_tasks: list[dict[str, Any]]
    bot_results: dict[str, Any]
    unresolved_uncertainties: list[str]
    proposed_actions: list[dict[str, Any]]
    approval_state: str
    final_status: str


class GuardianVerdict(BaseModel):
    decision: GuardianDecision
    reason_code: str
    summary: str
    blocked_actions: list[str] = Field(default_factory=list)


class PlanningResult(BaseModel):
    feasible: bool
    blocks: list[dict[str, Any]]
    unscheduled: list[dict[str, Any]]
    violated_soft: list[str]
    unsatisfied_hard: list[str]
    explanation: str
    risk_level: RiskLevel


class HealthOut(BaseModel):
    status: str
    service: str = "termpilot"
    mode: str
    grok: str
    time: datetime
    access_code_required: bool = False
    student_login: bool = True
    password_required: bool = True
    email_verification: bool = False
    mfa: bool = False
    mail: str = "unset"
    mail_from: str | None = None


class ReadyOut(BaseModel):
    ready: bool
    database: str
    fixtures: bool
    grok: str


class MetricOut(BaseModel):
    kind: str
    key: str
    value_float: float | None = None
    value_int: int | None = None
    value_text: str | None = None
    label: str
    recorded_at: datetime


class EvaluationSessionIn(BaseModel):
    participant_code: str
    kind: str = "pilot"
    planning_time_minutes: float | None = None
    deadline_surprise: bool | None = None
    verified_action_rate: float | None = None
    survey: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class ControlTowerOut(BaseModel):
    mode: str
    readiness: str
    now: datetime
    timezone: str
    horizon_days: int
    last_reconciliation_at: datetime | None
    grok_state: str
    monitoring_enabled: bool
    verified_obligations: int
    open_conflicts: int
    pending_approvals: int
    high_risk_obligations: int
    plan_feasible: bool | None
    plan_risk: str | None
    source_coverage: dict[str, str]
    last_sync: dict[str, datetime | None]
