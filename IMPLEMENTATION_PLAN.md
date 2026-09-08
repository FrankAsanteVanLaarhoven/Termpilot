# TermPilot implementation plan

Frozen demo clock: `2026-09-05T08:00:00+01:00` (Europe/London).
Planning horizon: 14 days (`2026-09-05` → `2026-09-18`).

## Phase 0 — Inspect and decide (this file)

### Verified local capabilities

| Capability | Status |
| --- | --- |
| Python 3.12 | Available (`/opt/homebrew/bin/python3.12`) |
| Node.js / npm | Available (v25.5.0 / 11.8.0) |
| Docker Compose | Available |
| uv | Available |
| Grok CLI | Available (`grok` 1.0.13) |
| Grok skills / agents / personas / headless `-p` | Available |
| xAI / Grok API (`XAI_API_KEY`) | **Not set** — live model calls optional |
| Google OR-Tools | Not preinstalled — added as a project dependency |
| Real LMS / mailbox / Google Calendar | **Not available** — fixture adapters only |

### Grok-native mapping (documented deviation)

Grok CLI does **not** expose a hosted “Grok Bot” runtime with cloud routines. TermPilot therefore implements the required specialist bots twice, on purpose:

1. **Runtime (demo/tests):** in-process Orchestrator / Scout / Verifier / Planner / Guardian / Monitor services. Live xAI function-calling is used when `XAI_API_KEY` is present; otherwise a deterministic `FakeGrokAdapter` is used.
2. **Grok CLI (competition artefact):** project skills in `.grok/skills/`, agent definitions in `.grok/agents/`, and a monitoring workflow in `grok/routines/`. Copies also live under `grok/` as required by the brief.

The dual layout is intentional: Grok CLI discovers `.grok/`; the brief asked for `grok/`. See `docs/grok-bot-setup.md`.

### Architecture decisions

* SQLite default for zero-config demo; PostgreSQL via Docker Compose / `DATABASE_URL`.
* Next.js + TypeScript + Tailwind for the command-centre UI.
* Deterministic fixture parsers are the source of truth for the frozen demo.
* OR-Tools CP-SAT is the only schedule generator. The language model never invents slots.
* Calendar writes target an in-process demo calendar (exportable ICS). No real calendar is mutated.
* Demo user is synthetic: `usr_demo_a7f3` / display name “A. Rivera”.

### Demo scenario (seeded)

Two modules (`CSC0000`, `ENG0001`), six obligations, duplicate lab-report deadline, material problem-set contradiction, ambiguous reading date, prompt-injection sentence in a recruiting email, Saturday work collision, and an LMS outage flag.

## Phase status

```
PHASE: 0–7
STATUS: PASS (local demo + tests). Live xAI optional.

COMPLETED:
- In-process multi-bot pipeline with FakeGrokAdapter
- OR-Tools CP-SAT planner
- Next.js command-centre UI
- 32 pytest tests, demo-smoke 5/5
- Grok CLI skills/agents + grok/ mirror

VERIFICATION:
- backend ruff/mypy/pytest: pass
- make demo-smoke: PASS 5/5
- next build: pass
- live API reconcile: 6 obligations, 1 conflict, approval pending

REMAINING RISKS:
- XAI_API_KEY unset; live model untested
- Playwright browsers not installed in this environment
- UI screenshots not captured (servers running; no headed browser tool)
```
