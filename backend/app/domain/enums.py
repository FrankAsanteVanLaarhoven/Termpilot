"""Canonical enumerations for TermPilot."""

from __future__ import annotations

from enum import StrEnum


class ObligationType(StrEnum):
    ASSIGNMENT = "assignment"
    EXAM = "exam"
    EVENT = "event"
    WORK = "work"
    RECRUITING = "recruiting"
    SOCIETY = "society"
    REMINDER = "reminder"


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ObligationStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


class SourceType(StrEnum):
    LMS = "lms"
    EMAIL = "email"
    CALENDAR = "calendar"
    UPLOAD = "upload"
    MAILBOX = "mailbox"
    LINKEDIN = "linkedin"
    ORCID = "orcid"
    X = "x"
    NOTION = "notion"
    SLACK = "slack"
    GITHUB = "github"
    JIRA = "jira"
    DISCORD = "discord"
    TEAMS = "teams"
    GDRIVE = "gdrive"


class SourceAuthority(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"


class VerificationState(StrEnum):
    VERIFIED = "verified"
    PROBABLE = "probable"
    NEEDS_REVIEW = "needs_review"
    CONFLICTED = "conflicted"
    REJECTED = "rejected"


class Sensitivity(StrEnum):
    STUDENT_PRIVATE = "student_private"
    PUBLIC = "public"


class HealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    PERMISSION_REVOKED = "permission_revoked"


class PermissionState(StrEnum):
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"
    MISSING = "missing"


class ApprovalState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"


class AgentName(StrEnum):
    ORCHESTRATOR = "orchestrator"
    SCOUT = "scout"
    VERIFIER = "verifier"
    PLANNER = "planner"
    GUARDIAN = "guardian"
    MONITOR = "monitor"
    WORKFLOW = "workflow"


class AgentRunState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    PASSED = "passed"
    DEGRADED = "degraded"
    FAILED = "failed"
    BLOCKED = "blocked"


class ToolActionStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class ConsentPurpose(StrEnum):
    SOURCE_READ = "source_read"
    CALENDAR_WRITE = "calendar_write"
    MONITORING = "monitoring"
    EVALUATION = "evaluation"
    MESSAGE_SEND = "message_send"
    NOTES_WRITE = "notes_write"


class ConflictResolution(StrEnum):
    ACCEPT_A = "accept_a"
    ACCEPT_B = "accept_b"
    KEEP_UNRESOLVED = "keep_unresolved"
    REJECT_EXTRACTION = "reject_extraction"


class GuardianDecision(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"
    ESCALATE = "escalate"


class PlanBlockKind(StrEnum):
    STUDY = "study"
    FIXED = "fixed"
    BUFFER = "buffer"
    BREAK = "break"
    WORK = "work"
    SOCIETY = "society"
    SLEEP = "sleep"
    PROTECTED = "protected"


class PlanBlockState(StrEnum):
    EXISTING = "existing"
    PROPOSED = "proposed"
    APPROVED = "approved"
    CONFLICTED = "conflicted"
    COMPLETED = "completed"
    STALE = "stale"


class RiskLevel(StrEnum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class MetricKind(StrEnum):
    DEMO = "demo"
    SYSTEM_TEST = "system_test"
    PILOT = "pilot"


class OperationalMode(StrEnum):
    LIVE = "LIVE"
    DEMO = "DEMO"
    OFFLINE = "OFFLINE"
