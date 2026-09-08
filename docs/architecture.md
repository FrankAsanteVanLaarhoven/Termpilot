# Architecture

TermPilot is a single FastAPI service plus a Next.js command-centre UI.

## Why Grok interprets and code decides

Grok (or the deterministic FakeGrokAdapter when `XAI_API_KEY` is absent) extracts meaning from messy LMS pages and email. It does **not** invent timestamps, grant consent, or place study blocks.

Deterministic Python owns:

- schema validation
- timezone handling
- duplicate matching
- conflict creation
- consent and approval expiry
- OR-Tools CP-SAT scheduling
- demo-calendar writes and idempotency

## Provenance

`SourceObservation` → `Claim` → `Obligation` → `PlanBlock` → `ApprovalRequest` → `CalendarEvent`.

Every claim keeps its source type, authority, observation time and evidence excerpt. Merged duplicates retain both evidence rows.

## Specialist bots

In-process services, traced as agent runs:

| Bot | Job |
| --- | --- |
| Orchestrator | Decompose the goal. Never bypass Guardian or Verifier. |
| Scout | Fetch authorised sources and extract candidates. |
| Verifier | Merge duplicates, escalate contradictions. |
| Planner | Call CP-SAT. Explain the solver result. |
| Guardian | Consent, integrity, approval gate. |
| Monitor | Recheck sources; alert only on material change. |

Grok CLI skills and agents live in `.grok/` (discovered by `grok`) and are mirrored under `grok/` for the competition layout.

## Human approval

Calendar writes require a pending approval, an unexpired TTL, matching target `demo_calendar`, and calendar-write consent. Replay is idempotent.

## Safe degradation

An LMS outage uses the last snapshot and marks the connector degraded. A missing xAI key uses FakeGrokAdapter and labels metrics as demo/system-test. Offline mode refuses live calls.
