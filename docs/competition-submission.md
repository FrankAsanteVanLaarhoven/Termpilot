# Student Build Challenge — submission pack

Challenge: build a Grok Bot that solves a real back-to-school problem (homework, clubs, schedules, recruiting).

Entry form: https://tinyurl.com/grokbot-student

LinkedIn post must include:

1. A written description of what the Bot does and the tools it uses
2. A video of it in action
3. A shared Bot template so others can work with it
4. `#GrokBotForStudents`

Ready files:

| Criterion | File |
|---|---|
| Written description | [linkedin-post.md](./linkedin-post.md) |
| Video | [demo/termpilot-in-action.mp4](./demo/termpilot-in-action.mp4) |
| Shared template | [../grok/template/](../grok/template/) · [INSTALL.md](../grok/template/INSTALL.md) · [PROFILE.md](../grok/template/PROFILE.md) |
| Hashtag | `#GrokBotForStudents` |
| Demo script | [demo-script.md](./demo-script.md) |

## One-sentence problem

Students miss colliding deadlines because LMS, email, calendar and recruiting never agree.

## What the Bot does

TermPilot is Grok Bot as a verified student control tower. It inspects authorised sources, extracts obligations with provenance, refuses to guess material conflicts, builds a feasible 14-day plan under a 20-hour cap, and waits for on-screen approval before calendar or mail writes. It organises work. It will not complete assessed homework or impersonate a student.

## Tools

Grok Bot operates every student-facing TermPilot tool. No second bot is trained.

- **extract-obligations** — schema-valid deadlines from authorised LMS, email, calendar, uploads
- **verify-deadlines** — dedupe, conflict, evidence
- **build-feasible-plan** — OR-Tools CP-SAT, never invents slots
- **safe-calendar-write** — preview, approve, apply, rollback
- **privacy-and-integrity-check** — Guardian; no assessed-work completion
- **One-click connectors** — GitHub, LinkedIn, email, Notion, Slack, Jira, Teams, Discord, Drive
- **VoiceBridge** — typed or spoken; spoken yes is not a write
- **Monitor** — recheck authorised sources; alert on material change only

## How someone else uses the template

See [grok/template/INSTALL.md](../grok/template/INSTALL.md). They paste PROFILE.md into Grok Bot, or open a public `https://x.ai/bot/...` share if you published **Share as template** from the Grok Bot app. Secrets, MCP servers and personal memories are excluded.

## Interactive product

Repo: https://github.com/FrankAsanteVanLaarhoven/Termpilot

After this commit is on `main`, import the repo in Vercel (root = repository root, `vercel.json` already declares web + api). Testers sign in with any student email.

## Honest limits

- Fixture adapters work without OAuth keys. Live Gmail/Outlook/GitHub start when client ids are set.
- Calendar writes stay on the demo calendar until approved.
- Outbound mail is demo-outbox only. No SMTP.
- Pilot metrics are empty until a real study runs.
