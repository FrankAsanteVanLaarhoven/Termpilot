"""Duplicate matching and conflict rules."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.domain.schemas import CandidateObligation
from app.services.extraction import fingerprint


def same_obligation(a: CandidateObligation, b: CandidateObligation) -> bool:
    if a.fingerprint_hint and b.fingerprint_hint and a.fingerprint_hint == b.fingerprint_hint:
        return True
    if a.course_or_context == b.course_or_context:
        left = set(fingerprint(a.title, a.course_or_context).split(":")[-1].split("-"))
        right = set(fingerprint(b.title, b.course_or_context).split(":")[-1].split("-"))
        if left and right:
            overlap = len(left & right) / len(left | right)
            if overlap >= 0.5:
                return True
    return False


def material_due_conflict(
    a: datetime | None, b: datetime | None, threshold: timedelta | None = None
) -> bool:
    if a is None or b is None:
        return False
    threshold = threshold or timedelta(hours=1)
    return abs((a - b).total_seconds()) > threshold.total_seconds()


def newer_not_automatically_authoritative(primary_due: datetime, other_due: datetime) -> bool:
    """Authority is not recency. Kept as an explicit rule for tests and docs."""
    del primary_due, other_due
    return True
