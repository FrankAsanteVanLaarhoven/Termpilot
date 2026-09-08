# Demo script

Student surface (default). Frozen fixture clock: **Saturday 5 Sep 2026 08:00 Europe/London**.

## Record the challenge video

With API on :8000 and UI on :3001:

```bash
cd frontend
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3001 npx playwright test e2e/record-challenge.spec.ts --project=chromium
```

The file for LinkedIn is `docs/demo/termpilot-in-action.mp4`.

## 90-second student path (what the recording shows)

0:00 Splash — TermPilot mark is Home. Click it to enter.
0:12 Home overview — how to use it, Grok Bot, Ask.
0:20 Ask: “What should I focus on this week?”
0:35 Grok Bot answers from verified obligations (lab report, conflicted problem set, internship).
0:45 Review my week — plan, conflicts, pending approval. Nothing written yet.
0:58 Home mark returns to overview.
1:05 Messages — authorised inbox, P0 alerts, drafts need approval.
1:15 Connected services — one-click GitHub, LinkedIn, Notion, Slack, Jira.
1:25 Back to Home. `#GrokBotForStudents`.

## Proof-mode 2:40 path (evaluators)

Open Preferences → Interface mode → Proof, then reconcile:

> TermPilot, reconcile my academic and recruiting commitments for the next 14 days. Show conflicts, build a realistic plan around my 20-hour weekly limit, and ask before changing my calendar.

Show conflicts, unsent clarification, approvals blocked until Approve, then Apply + Rollback.

## Backup

`GROK_MODE=fake` still completes the frozen fixture if xAI is down.
