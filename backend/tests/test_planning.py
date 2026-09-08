from __future__ import annotations

from datetime import datetime, timedelta

from app.domain.enums import RiskLevel
from app.planning.solver import FixedBusy, SolverInput, TaskSpec, solve
from app.services.clock import now


def _base_tasks() -> list[TaskSpec]:
    return [
        TaskSpec(
            obligation_id="obl_lab",
            title="Robotics Lab Report",
            course="CSC0000",
            due_at=datetime.fromisoformat("2026-09-18T16:00:00+01:00"),
            minutes=120,
            priority="high",
            verification_state="verified",
        )
    ]


def test_feasible_plan_respects_fixed_busy() -> None:
    start = now()
    busy = [
        FixedBusy(
            title="Work",
            start=datetime.fromisoformat("2026-09-12T09:00:00+01:00"),
            end=datetime.fromisoformat("2026-09-12T17:00:00+01:00"),
            kind="work",
        )
    ]
    result = solve(
        SolverInput(
            now=start,
            horizon_end=start + timedelta(days=14),
            tasks=_base_tasks(),
            busy=busy,
            weekly_limit_hours=20,
        )
    )
    assert result.feasible is True
    assert result.blocks
    for block in result.blocks:
        b_start = datetime.fromisoformat(block["start_at"])
        b_end = datetime.fromisoformat(block["end_at"])
        assert not (b_start < busy[0].end and b_end > busy[0].start)


def test_infeasible_when_deadline_is_inside_sleep() -> None:
    start = now()
    due = start + timedelta(hours=1)
    result = solve(
        SolverInput(
            now=start,
            horizon_end=start + timedelta(days=1),
            tasks=[
                TaskSpec(
                    obligation_id="obl_impossible",
                    title="Impossible",
                    course="CSC0000",
                    due_at=due,
                    minutes=20 * 60,
                    priority="high",
                    verification_state="verified",
                )
            ],
            busy=[],
            weekly_limit_hours=1,
            daily_limit_minutes=30,
        )
    )
    assert result.feasible is False
    assert result.unsatisfied_hard
    assert result.risk_level == RiskLevel.RED


def test_ambiguous_task_is_not_invented() -> None:
    start = now()
    result = solve(
        SolverInput(
            now=start,
            horizon_end=start + timedelta(days=14),
            tasks=[
                TaskSpec(
                    obligation_id="obl_read",
                    title="Weekly Reading Response",
                    course="ENG0001",
                    due_at=None,
                    minutes=90,
                    priority="low",
                    verification_state="needs_review",
                )
            ],
            busy=[],
        )
    )
    assert result.unscheduled
    assert "needs_review" in result.unscheduled[0]["reason"]
