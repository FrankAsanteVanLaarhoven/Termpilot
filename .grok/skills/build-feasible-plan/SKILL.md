---
name: build-feasible-plan
description: Explain a CP-SAT 14-day plan. Never invent time slots. Use when planning study blocks or running /build-feasible-plan.
---

# build-feasible-plan

Call the TermPilot planning service. Do not invent a schedule in prose.

## Inputs

- Verified obligations
- User preferences
- Fixed events
- Planning horizon

## Output

Proposed plan blocks, unscheduled obligations, conflicts, constraint explanations, risk level.

## Rules

1. Only use explicitly available time.
2. Fixed classes, work, sleep and protected time cannot move.
3. Expose unsatisfied constraints.
4. Explain operational reasons, never private chain-of-thought.
