from __future__ import annotations

from datetime import datetime

from app.domain.enums import ObligationType, SourceType
from app.domain.schemas import CandidateObligation
from app.services.clock import now


def test_obligation_schema_timezone_aware() -> None:
    candidate = CandidateObligation(
        title="Robotics Lab Report",
        type=ObligationType.ASSIGNMENT,
        course_or_context="CSC0000",
        due_at=datetime.fromisoformat("2026-09-18T16:00:00+01:00"),
        estimated_minutes=360,
        source_type=SourceType.LMS,
        source_reference="fixtures/lms/modules.json",
        source_observed_at=datetime.fromisoformat("2026-09-04T08:15:00+01:00"),
        confidence=0.96,
    )
    assert candidate.due_at is not None
    assert candidate.due_at.tzinfo is not None
    assert now().tzinfo is not None
