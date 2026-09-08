from __future__ import annotations

from datetime import datetime, timedelta

from app.services.matching import material_due_conflict, newer_not_automatically_authoritative


def test_material_deadline_conflict() -> None:
    a = datetime.fromisoformat("2026-09-16T12:00:00+01:00")
    b = datetime.fromisoformat("2026-09-14T09:00:00+01:00")
    assert material_due_conflict(a, b)


def test_same_deadline_is_not_a_conflict() -> None:
    a = datetime.fromisoformat("2026-09-18T16:00:00+01:00")
    b = a + timedelta(minutes=5)
    assert not material_due_conflict(a, b)


def test_recency_is_not_authority() -> None:
    assert newer_not_automatically_authoritative(
        datetime.fromisoformat("2026-09-16T12:00:00+01:00"),
        datetime.fromisoformat("2026-09-14T09:00:00+01:00"),
    )
