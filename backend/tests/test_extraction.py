from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.services.extraction import extract_from_email, extract_from_lms, parse_explicit_datetime
from app.settings import get_settings


def test_parse_explicit_datetime_preserves_offset() -> None:
    parsed = parse_explicit_datetime("2026-09-18T16:00:00+01:00")
    assert parsed is not None
    assert parsed.isoformat().endswith("+01:00") or parsed.utcoffset() is not None


def test_does_not_infer_missing_deadline() -> None:
    assert parse_explicit_datetime("") is None


def test_lms_extracts_five_assignments() -> None:
    root = get_settings().fixtures_root / "lms" / "modules.json"
    payload = json.loads(Path(root).read_text(encoding="utf-8"))
    result = extract_from_lms(
        payload,
        datetime.fromisoformat(payload["observed_at"]),
        payload["source_reference"],
    )
    titles = {c.title for c in result.candidates}
    assert "Robotics Lab Report" in titles
    assert "Weekly Reading Response" in titles
    reading = next(c for c in result.candidates if c.title == "Weekly Reading Response")
    assert reading.due_at is None
    assert reading.date_precision == "ambiguous"


def test_email_extracts_internship_and_strips_injection() -> None:
    path = get_settings().fixtures_root / "email" / "internship_injection.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = extract_from_email(
        payload,
        datetime.fromisoformat(payload["observed_at"]),
        payload["source_reference"],
    )
    assert result.injection_detected is True
    assert result.candidates[0].type.value == "recruiting"
    assert result.candidates[0].due_at is not None
    blob = " ".join(result.discarded_instructions).lower()
    assert "ignore previous instructions" in blob
