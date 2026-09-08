from __future__ import annotations

from datetime import datetime

from app.domain.enums import SourceType
from app.domain.schemas import CandidateObligation
from app.services.extraction import fingerprint
from app.services.matching import same_obligation


def _cand(title: str, course: str, source: SourceType) -> CandidateObligation:
    return CandidateObligation(
        title=title,
        course_or_context=course,
        source_type=source,
        source_reference="x",
        source_observed_at=datetime.fromisoformat("2026-09-04T08:15:00+01:00"),
        confidence=0.9,
        fingerprint_hint=fingerprint(title, course),
    )


def test_lab_report_duplicate_matches() -> None:
    lms = _cand("Robotics Lab Report", "CSC0000", SourceType.LMS)
    email = _cand("Reminder Lab Report Robotics", "CSC0000", SourceType.EMAIL)
    assert same_obligation(lms, email)


def test_distinct_assignments_do_not_match() -> None:
    a = _cand("Robotics Lab Report", "CSC0000", SourceType.LMS)
    b = _cand("Control Systems Problem Set", "CSC0000", SourceType.LMS)
    assert not same_obligation(a, b)
