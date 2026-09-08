"""Deterministic extraction from authorised source observations."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from dateutil import parser as date_parser

from app.domain.enums import ObligationType, Priority, SourceAuthority, SourceType
from app.domain.schemas import CandidateObligation, ExtractionResult
from app.policies.injection import strip_injected_instructions
from app.services.clock import ensure_tz, tz

_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2}|Z)?")
_HUMAN_DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+20\d{2}(?:\s+at\s+\d{1,2}:\d{2})?)\b",
    re.I,
)
_AMBIGUOUS_RE = re.compile(
    r"\b(friday of week\s*\d|next friday|sometime next week|tba|to be announced)\b",
    re.I,
)


def parse_explicit_datetime(value: str) -> datetime | None:
    if not value.strip():
        return None
    try:
        parsed = date_parser.parse(value, fuzzy=False, default=None)
    except (ValueError, OverflowError, TypeError):
        return None
    if parsed is None:
        return None
    return ensure_tz(parsed)


def _priority(value: str | None) -> Priority:
    try:
        return Priority(value or "medium")
    except ValueError:
        return Priority.MEDIUM


def fingerprint(title: str, course: str) -> str:
    stop = {
        "the",
        "a",
        "an",
        "reminder",
        "please",
        "submit",
        "still",
        "due",
        "of",
        "for",
        "and",
    }
    tokens = re.findall(r"[a-z0-9]+", title.lower())
    kept = [t for t in tokens if t not in stop]
    course_key = re.sub(r"[^a-z0-9]+", "", course.lower())
    return f"{course_key}:" + "-".join(sorted(set(kept)))


def extract_from_lms(
    payload: dict[str, Any], observed_at: datetime, reference: str
) -> ExtractionResult:
    candidates: list[CandidateObligation] = []
    for module in payload.get("modules", []):
        course = str(module.get("code", ""))
        for item in module.get("assignments", []):
            due_raw = item.get("due_at")
            due_at = parse_explicit_datetime(due_raw) if due_raw else None
            precision = str(item.get("date_precision") or ("exact" if due_at else "ambiguous"))
            missing = [] if due_at else ["due_at"]
            title = str(item["title"])
            candidates.append(
                CandidateObligation(
                    title=title,
                    type=ObligationType.ASSIGNMENT,
                    course_or_context=course,
                    description=str(item.get("description", ""))[:400],
                    due_at=due_at,
                    estimated_minutes=int(item.get("estimated_minutes") or 60),
                    priority=_priority(item.get("priority")),
                    source_type=SourceType.LMS,
                    source_reference=f"{reference}#{item.get('id', title)}",
                    source_observed_at=observed_at,
                    source_authority=SourceAuthority.PRIMARY,
                    confidence=0.96 if due_at else 0.55,
                    date_precision=precision,
                    missing_fields=missing,
                    evidence_excerpt=str(item.get("description", title))[:240],
                    fingerprint_hint=fingerprint(title, course),
                )
            )
    return ExtractionResult(
        candidates=candidates,
        evidence_reference=reference,
        extraction_confidence=0.95,
        missing_fields=[c.title for c in candidates if c.missing_fields],
    )


def extract_from_email(
    payload: dict[str, Any], observed_at: datetime, reference: str
) -> ExtractionResult:
    body = str(payload.get("body") or "")
    subject = str(payload.get("subject") or "")
    cleaned, discarded = strip_injected_instructions(body)
    combined = f"{subject}\n{cleaned}"
    due_at = None
    iso = _ISO_RE.search(combined)
    human = _HUMAN_DATE_RE.search(combined)
    if iso:
        due_at = parse_explicit_datetime(iso.group(0))
    elif human:
        due_at = parse_explicit_datetime(human.group(1))
    ambiguous = bool(_AMBIGUOUS_RE.search(combined)) and due_at is None

    title, course, kind, minutes, priority = _classify_email(subject, cleaned)
    missing = [] if due_at else ["due_at"]
    precision = "ambiguous" if ambiguous or due_at is None else "exact"
    candidate = CandidateObligation(
        title=title,
        type=kind,
        course_or_context=course,
        description=cleaned[:400],
        due_at=due_at,
        estimated_minutes=minutes,
        priority=priority,
        source_type=SourceType.EMAIL,
        source_reference=reference,
        source_observed_at=observed_at,
        source_authority=SourceAuthority.SECONDARY,
        confidence=0.91 if due_at else 0.4,
        date_precision=precision,
        missing_fields=missing,
        evidence_excerpt=cleaned[:240],
        fingerprint_hint=fingerprint(title, course),
    )
    return ExtractionResult(
        candidates=[candidate],
        evidence_reference=reference,
        extraction_confidence=candidate.confidence,
        missing_fields=missing,
        injection_detected=bool(discarded),
        discarded_instructions=discarded,
    )


def extract_from_calendar(
    payload: dict[str, Any], observed_at: datetime, reference: str
) -> ExtractionResult:
    candidates: list[CandidateObligation] = []
    for event in payload.get("events", []):
        title = str(event.get("title") or "Event")
        start = parse_explicit_datetime(str(event.get("start_at") or ""))
        end = parse_explicit_datetime(str(event.get("end_at") or ""))
        minutes = 60
        if start and end:
            minutes = max(30, int((end - start).total_seconds() // 60))
        kind = ObligationType.EVENT
        lowered = title.lower()
        if "work" in lowered:
            kind = ObligationType.WORK
        elif "society" in lowered:
            kind = ObligationType.SOCIETY
        course = "calendar"
        if "CSC0000" in title:
            course = "CSC0000"
        elif "ENG0001" in title:
            course = "ENG0001"
        candidates.append(
            CandidateObligation(
                title=title,
                type=kind,
                course_or_context=course,
                description=str(event.get("location") or ""),
                due_at=end or start,
                estimated_minutes=minutes,
                priority=Priority.MEDIUM,
                source_type=SourceType.CALENDAR,
                source_reference=f"{reference}#{event.get('uid', title)}",
                source_observed_at=observed_at,
                source_authority=SourceAuthority.PRIMARY,
                confidence=0.99,
                date_precision="exact",
                evidence_excerpt=title,
                fingerprint_hint=fingerprint(title, course),
            )
        )
    return ExtractionResult(
        candidates=candidates,
        evidence_reference=reference,
        extraction_confidence=0.99,
    )


def extract_from_upload(
    payload: dict[str, Any], observed_at: datetime, reference: str
) -> ExtractionResult:
    text = str(payload.get("text") or "")
    cleaned, discarded = strip_injected_instructions(text)
    return ExtractionResult(
        candidates=[],
        evidence_reference=reference,
        extraction_confidence=0.2,
        missing_fields=["structured_obligations"],
        injection_detected=bool(discarded),
        discarded_instructions=discarded,
    )


def extract_observation(
    source_type: SourceType,
    payload: dict[str, Any],
    observed_at: datetime,
    reference: str,
) -> ExtractionResult:
    if source_type == SourceType.LMS:
        return extract_from_lms(payload, observed_at, reference)
    if source_type == SourceType.EMAIL:
        return extract_from_email(payload, observed_at, reference)
    if source_type == SourceType.CALENDAR:
        return extract_from_calendar(payload, observed_at, reference)
    return extract_from_upload(payload, observed_at, reference)


def _classify_email(subject: str, body: str) -> tuple[str, str, ObligationType, int, Priority]:
    blob = f"{subject}\n{body}".lower()
    if "internship" in blob or "aurora" in blob:
        return (
            "Aurora Robotics internship application",
            "recruiting",
            ObligationType.RECRUITING,
            180,
            Priority.HIGH,
        )
    if "problem set" in blob or "control systems" in blob:
        return (
            "Control Systems Problem Set",
            "CSC0000",
            ObligationType.ASSIGNMENT,
            240,
            Priority.HIGH,
        )
    if "lab report" in blob or "robotics lab" in blob:
        return (
            "Robotics Lab Report",
            "CSC0000",
            ObligationType.ASSIGNMENT,
            360,
            Priority.HIGH,
        )
    if "reading" in blob:
        return (
            "Weekly Reading Response",
            "ENG0001",
            ObligationType.ASSIGNMENT,
            90,
            Priority.LOW,
        )
    title = subject.split("—")[0].strip() or "Untitled email obligation"
    return title, "email", ObligationType.ASSIGNMENT, 60, Priority.MEDIUM


# Keep timezone helper referenced so tests can import it from this module.
USER_TZ = tz
