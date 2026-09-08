"""OR-Tools CP-SAT study-block scheduler. The language model never invents slots."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

try:
    from ortools.sat.python import cp_model
except Exception:  # pragma: no cover - native wheel can fail on some hosts
    cp_model = None  # type: ignore[assignment]

from app.domain.enums import RiskLevel
from app.domain.schemas import PlanningResult
from app.services import clock
from app.settings import get_settings

SLOT_MINUTES = 30


@dataclass
class FixedBusy:
    title: str
    start: datetime
    end: datetime
    kind: str = "fixed"


@dataclass
class TaskSpec:
    obligation_id: str
    title: str
    course: str
    due_at: datetime | None
    minutes: int
    priority: str
    verification_state: str
    conservative_due: datetime | None = None


@dataclass
class SolverInput:
    now: datetime
    horizon_end: datetime
    tasks: list[TaskSpec]
    busy: list[FixedBusy]
    weekly_limit_hours: int = 20
    daily_limit_minutes: int = 360
    max_block_minutes: int = 120
    break_minutes: int = 15
    sleep_start: str = "23:00"
    sleep_end: str = "07:00"
    preferred_windows: list[dict[str, str]] = field(default_factory=list)
    safety_buffer_hours: int = 24


def _parse_hhmm(value: str) -> tuple[int, int]:
    hours, minutes = value.split(":")
    return int(hours), int(minutes)


def _iter_slots(start: datetime, end: datetime) -> list[datetime]:
    slots: list[datetime] = []
    cursor = start.replace(second=0, microsecond=0)
    minute = (cursor.minute // SLOT_MINUTES) * SLOT_MINUTES
    cursor = cursor.replace(minute=minute)
    if cursor < start:
        cursor += timedelta(minutes=SLOT_MINUTES)
    while cursor + timedelta(minutes=SLOT_MINUTES) <= end:
        slots.append(cursor)
        cursor += timedelta(minutes=SLOT_MINUTES)
    return slots


def _sleep_blocked(slot: datetime, sleep_start: str, sleep_end: str) -> bool:
    sh, sm = _parse_hhmm(sleep_start)
    eh, em = _parse_hhmm(sleep_end)
    start_m = sh * 60 + sm
    end_m = eh * 60 + em
    cur = slot.hour * 60 + slot.minute
    if start_m > end_m:
        return cur >= start_m or cur < end_m
    return start_m <= cur < end_m


def _busy_blocked(slot: datetime, busy: list[FixedBusy]) -> bool:
    end = slot + timedelta(minutes=SLOT_MINUTES)
    for item in busy:
        if slot < item.end and end > item.start:
            return True
    return False


def _in_preferred(slot: datetime, windows: list[dict[str, str]]) -> bool:
    if not windows:
        return 9 <= slot.hour < 12 or 19 <= slot.hour < 22
    for window in windows:
        days = window.get("days", "weekdays")
        if days == "weekdays" and slot.weekday() >= 5:
            continue
        sh, sm = _parse_hhmm(window.get("start", "09:00"))
        eh, em = _parse_hhmm(window.get("end", "12:00"))
        cur = slot.hour * 60 + slot.minute
        if sh * 60 + sm <= cur < eh * 60 + em:
            return True
    return False


def _pack_blocks(
    task: TaskSpec,
    assigned: list[datetime],
    max_block_minutes: int,
    reasons: dict[str, str],
) -> list[dict[str, Any]]:
    if not assigned:
        return []
    ordered = sorted(assigned)
    groups: list[list[datetime]] = [[ordered[0]]]
    for slot in ordered[1:]:
        if slot - groups[-1][-1] == timedelta(minutes=SLOT_MINUTES):
            groups[-1].append(slot)
        else:
            groups.append([slot])
    blocks: list[dict[str, Any]] = []
    max_slots = max(1, max_block_minutes // SLOT_MINUTES)
    for group in groups:
        for i in range(0, len(group), max_slots):
            chunk = group[i : i + max_slots]
            start = chunk[0]
            end = chunk[-1] + timedelta(minutes=SLOT_MINUTES)
            blocks.append(
                {
                    "obligation_id": task.obligation_id,
                    "title": f"Study · {task.title}",
                    "kind": "study",
                    "start_at": start.isoformat(),
                    "end_at": end.isoformat(),
                    "state": "proposed",
                    "reason": reasons.get(
                        task.obligation_id,
                        "Scheduled in an explicitly available slot before the deadline.",
                    ),
                }
            )
    return blocks


def solve(spec: SolverInput) -> PlanningResult:
    settings = get_settings()
    max_block = spec.max_block_minutes or settings.max_study_block_minutes
    weekly_minutes = spec.weekly_limit_hours * 60
    slots = _iter_slots(spec.now, spec.horizon_end)
    available: list[datetime] = []
    for slot in slots:
        if _sleep_blocked(slot, spec.sleep_start, spec.sleep_end):
            continue
        if _busy_blocked(slot, spec.busy):
            continue
        available.append(slot)

    schedulable: list[TaskSpec] = []
    unscheduled: list[dict[str, Any]] = []
    for task in spec.tasks:
        due = task.conservative_due or task.due_at
        if task.verification_state == "needs_review" and task.due_at is None:
            unscheduled.append(
                {
                    "obligation_id": task.obligation_id,
                    "title": task.title,
                    "reason": "No exact deadline. Marked needs_review; time was not invented.",
                }
            )
            continue
        if due is None:
            unscheduled.append(
                {
                    "obligation_id": task.obligation_id,
                    "title": task.title,
                    "reason": "Missing due date.",
                }
            )
            continue
        if task.minutes <= 0:
            unscheduled.append(
                {
                    "obligation_id": task.obligation_id,
                    "title": task.title,
                    "reason": "No estimated duration.",
                }
            )
            continue
        schedulable.append(task)

    if not schedulable:
        return PlanningResult(
            feasible=True,
            blocks=[],
            unscheduled=unscheduled,
            violated_soft=[],
            unsatisfied_hard=[],
            explanation="No dated study tasks required scheduling.",
            risk_level=RiskLevel.GREEN if not unscheduled else RiskLevel.AMBER,
        )

    if cp_model is None:
        for task in schedulable:
            unscheduled.append(
                {
                    "obligation_id": task.obligation_id,
                    "title": task.title,
                    "reason": "Planner library is unavailable on this host.",
                }
            )
        return PlanningResult(
            feasible=False,
            blocks=[],
            unscheduled=unscheduled,
            violated_soft=[],
            unsatisfied_hard=["ortools_unavailable"],
            explanation="The study planner could not start. Deadlines are still listed.",
            risk_level=RiskLevel.AMBER,
        )

    needed_slots = [max(1, (t.minutes + SLOT_MINUTES - 1) // SLOT_MINUTES) for t in schedulable]
    model = cp_model.CpModel()
    x: dict[tuple[int, int], cp_model.IntVar] = {}
    slot_ok: list[list[int]] = []

    for t_idx, task in enumerate(schedulable):
        due = task.conservative_due or task.due_at
        assert due is not None
        ok: list[int] = []
        for s_idx, slot in enumerate(available):
            end = slot + timedelta(minutes=SLOT_MINUTES)
            if end <= due:
                x[t_idx, s_idx] = model.new_bool_var(f"t{t_idx}s{s_idx}")
                ok.append(s_idx)
        slot_ok.append(ok)
        if not ok:
            continue
        model.add(sum(x[t_idx, s] for s in ok) == needed_slots[t_idx])

    hard: list[str] = []
    for t_idx, task in enumerate(schedulable):
        if not slot_ok[t_idx]:
            hard.append(f"no_available_slots_before_deadline:{task.title}")
            unscheduled.append(
                {
                    "obligation_id": task.obligation_id,
                    "title": task.title,
                    "reason": "No available slots before the deadline.",
                }
            )

    viable = [i for i, task in enumerate(schedulable) if slot_ok[i]]
    if not viable:
        return PlanningResult(
            feasible=False,
            blocks=[],
            unscheduled=unscheduled,
            violated_soft=[],
            unsatisfied_hard=hard or ["no_feasible_slots"],
            explanation=(
                "Hard constraints could not be satisfied. "
                "No study slots exist before the deadlines."
            ),
            risk_level=RiskLevel.RED,
        )

    for s_idx, _slot in enumerate(available):
        present = [x[t, s_idx] for t in viable if s_idx in slot_ok[t] and (t, s_idx) in x]
        if present:
            model.add(sum(present) <= 1)

    by_day: dict[object, list[int]] = {}
    for s_idx, slot in enumerate(available):
        by_day.setdefault(slot.date(), []).append(s_idx)
    daily_limit_slots = spec.daily_limit_minutes // SLOT_MINUTES
    for _day, idxs in by_day.items():
        present = [x[t, s] for t in viable for s in idxs if (t, s) in x]
        if present:
            model.add(sum(present) <= daily_limit_slots)

    all_assigned = [x[t, s] for t in viable for s in slot_ok[t] if (t, s) in x]
    if all_assigned:
        model.add(sum(all_assigned) <= weekly_minutes // SLOT_MINUTES)

    objective_terms: list[cp_model.LinearExprT] = []
    for t_idx in viable:
        task = schedulable[t_idx]
        due = task.conservative_due or task.due_at
        assert due is not None
        buffer_cut = due - timedelta(hours=spec.safety_buffer_hours)
        weight = 3 if task.priority == "high" else 2 if task.priority == "medium" else 1
        for s_idx in slot_ok[t_idx]:
            slot = available[s_idx]
            score = 0
            if _in_preferred(slot, spec.preferred_windows):
                score += 4
            if slot + timedelta(minutes=SLOT_MINUTES) <= buffer_cut:
                score += 5
            # Prefer earlier slots for higher-risk work.
            hours_until = (due - slot).total_seconds() / 3600
            score += int(max(0, 40 - hours_until) * weight / 10)
            # Packing bonus is applied after solve.
            objective_terms.append(score * x[t_idx, s_idx])

    if objective_terms:
        model.maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 8.0
    solver.parameters.num_search_workers = 4
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        hard.append("cp_sat_infeasible")
        for t_idx in viable:
            task = schedulable[t_idx]
            unscheduled.append(
                {
                    "obligation_id": task.obligation_id,
                    "title": task.title,
                    "reason": (
                        "Could not allocate the required duration "
                        "without violating hard constraints."
                    ),
                }
            )
        return PlanningResult(
            feasible=False,
            blocks=[],
            unscheduled=unscheduled,
            violated_soft=["preferred_windows", "safety_buffer"],
            unsatisfied_hard=hard,
            explanation=(
                "The constraint solver found no feasible 14-day allocation. "
                "Fixed classes, work, sleep and the weekly study cap consume the available time."
            ),
            risk_level=RiskLevel.RED,
        )

    assigned: dict[int, list[datetime]] = {t: [] for t in viable}
    for (t_idx, s_idx), var in x.items():
        if solver.value(var) == 1:
            assigned[t_idx].append(available[s_idx])

    reasons: dict[str, str] = {}
    violated_soft: list[str] = []
    blocks: list[dict[str, Any]] = []
    for t_idx, task in enumerate(schedulable):
        if t_idx not in assigned or not assigned[t_idx]:
            continue
        due = task.conservative_due or task.due_at
        last = max(assigned[t_idx]) + timedelta(minutes=SLOT_MINUTES)
        preferred_hits = sum(1 for s in assigned[t_idx] if _in_preferred(s, spec.preferred_windows))
        buffer_ok = due is not None and last <= due - timedelta(hours=spec.safety_buffer_hours)
        reason_parts = [
            f"Placed before {due.strftime('%a %d %b %H:%M') if due else 'horizon'}",
            "no fixed event overlap",
        ]
        if preferred_hits:
            reason_parts.append("uses a preferred study window")
        else:
            violated_soft.append(f"preferred_windows:{task.title}")
        if buffer_ok:
            reason_parts.append("preserves a 24-hour submission buffer")
        else:
            violated_soft.append(f"safety_buffer:{task.title}")
        if task.verification_state == "conflicted":
            reason_parts.append(
                "uses the earlier claimed deadline as a safety bound until you decide"
            )
        reasons[task.obligation_id] = "Scheduled because " + ", ".join(reason_parts) + "."
        blocks.extend(_pack_blocks(task, assigned[t_idx], max_block, reasons))

    total_needed = sum(t.minutes for t in schedulable)
    scheduled_min = len(blocks) and sum(
        int(
            (
                datetime.fromisoformat(b["end_at"]) - datetime.fromisoformat(b["start_at"])
            ).total_seconds()
            / 60
        )
        for b in blocks
    )
    risk = RiskLevel.GREEN
    if unscheduled or violated_soft:
        risk = RiskLevel.AMBER
    if hard or scheduled_min < total_needed * 0.9:
        risk = RiskLevel.RED

    explanation = (
        f"Allocated {scheduled_min} of {total_needed} required minutes across "
        f"{len(blocks)} study blocks inside authorised available time. "
        "Sleep, classes, work and society events were treated as immovable."
    )
    if unscheduled:
        explanation += f" {len(unscheduled)} item(s) remain unscheduled."

    return PlanningResult(
        feasible=True,
        blocks=blocks,
        unscheduled=unscheduled,
        violated_soft=sorted(set(violated_soft)),
        unsatisfied_hard=hard,
        explanation=explanation,
        risk_level=risk,
    )


def solve_from_records(
    obligations: list[dict[str, Any]],
    busy: list[FixedBusy],
    preferences: dict[str, Any],
) -> PlanningResult:
    now = clock.now()
    spec = SolverInput(
        now=now,
        horizon_end=clock.horizon_end(now),
        tasks=[
            TaskSpec(
                obligation_id=str(item["id"]),
                title=str(item["title"]),
                course=str(item.get("course_or_context") or ""),
                due_at=item.get("due_at"),
                minutes=int(item.get("estimated_minutes") or 60),
                priority=str(item.get("priority") or "medium"),
                verification_state=str(item.get("verification_state") or "verified"),
                conservative_due=item.get("conservative_due") or item.get("due_at"),
            )
            for item in obligations
        ],
        busy=busy,
        weekly_limit_hours=int(preferences.get("weekly_study_limit_hours") or 20),
        max_block_minutes=int(preferences.get("max_study_block_minutes") or 120),
        break_minutes=int(preferences.get("break_minutes") or 15),
        sleep_start=str(preferences.get("sleep_start") or "23:00"),
        sleep_end=str(preferences.get("sleep_end") or "07:00"),
        preferred_windows=list(preferences.get("preferred_windows_json") or []),
    )
    return solve(spec)
