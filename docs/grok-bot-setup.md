# Grok Bot setup

## Verified capability (2026-09-05)

Grok CLI 1.0.13 provides skills, agents, personas, project rules and headless `grok -p`. It does **not** provide a hosted multi-bot runtime with cloud routines.

TermPilot therefore:

1. Runs Orchestrator / Scout / Verifier / Planner / Guardian / Monitor **in process**.
2. Ships the same roles as `.grok/skills` and `.grok/agents` for Grok CLI.
3. Mirrors them under `grok/` as required by the brief.

## Live model (optional)

```bash
export XAI_API_KEY=...   # never commit
export GROK_MODE=live
```

API: `https://api.x.ai/v1` model `grok-4.5`.

Without a key, `GROK_MODE=auto` uses `FakeGrokAdapter`. Demo traces label this as `fake`.

## CLI demo

```bash
cd termpilot
grok -p "Using TermPilot skills, explain how you would reconcile the next 14 days without writing a calendar."
```
