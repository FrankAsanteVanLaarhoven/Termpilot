# TermPilot

**The verified control tower for student life.**

> No important deadline should become a surprise.

TermPilot inspects authorised student sources, extracts obligations with provenance, refuses to guess material conflicts, builds a feasible 14-day plan with OR-Tools, and waits for explicit approval before writing a **demo** calendar.

It organises work. It will not complete assessed homework or impersonate a student.

## Student Build Challenge

Submission pack: [docs/competition-submission.md](docs/competition-submission.md)

- LinkedIn copy: [docs/linkedin-post.md](docs/linkedin-post.md)
- Video: [docs/demo/termpilot-in-action.mp4](docs/demo/termpilot-in-action.mp4)
- Shared Grok Bot template: https://x.ai/bot/OeUkDHEV4ykNb2EDpUO1m ([grok/template/](grok/template/))
- Hashtag: `#GrokBotForStudents`
- Interactive app: import this repo in Vercel (`vercel.json` already declares web + `/api`)

## Architecture summary

Grok interprets messy text. Deterministic code owns dates, consent, conflicts and schedules. See [docs/architecture.md](docs/architecture.md).

## Why Grok Bot is essential

Specialist bots (Scout, Verifier, Planner, Guardian) keep interpretation bounded. The Orchestrator cannot bypass Guardian or Verifier. Skills encode the contracts. A monitoring routine rechecks sources and alerts only on material change.

Grok CLI has no hosted bot runtime; TermPilot implements the bots in-process and ships CLI skills in `.grok/`. See [docs/grok-bot-setup.md](docs/grok-bot-setup.md).

## Quick start

```bash
cd termpilot
make install
# terminal 1
make backend
# terminal 2
make frontend
```

Open http://127.0.0.1:3000 (or http://127.0.0.1:3001 in the local Grok session).

Sign in with **your university email and a password you choose**. First visit creates your isolated account; next visit signs you back in. Grok Bot is the only student engine. **One-click Connect** links GitHub, LinkedIn, email, Notion, Slack, Jira, Teams, Discord and Drive (fixture adapters immediately; live OAuth when the matching client id is set). Then prompt Grok Bot. Guardian, injection stripping and on-screen approval stay in force. Calendar and outbound mail never send on spoken yes.

The Next.js app proxies `/api/*` to FastAPI, so the browser never needs `localhost:8000`.

Reusable G1 robot: `node packages/g1-humanoid/scripts/pack.mjs` writes a zip for other projects.

Docker: `docker compose up --build`

## Live student deployment (Vercel)

TermPilot ships as one Vercel project with two services: the Next.js UI at `/` and FastAPI at `/api`.

Live site: **https://termpilot.org** (Vercel team [frank-asante-van-laarhovens-projects](https://vercel.com/frank-asante-van-laarhovens-projects)). Setup: [docs/vercel-setup.md](docs/vercel-setup.md).

1. Import [FrankAsanteVanLaarhoven/Termpilot](https://github.com/FrankAsanteVanLaarhoven/Termpilot) in Vercel. Root directory is the repository root. `vercel.json` already declares the services.
2. Set these environment variables on the project (Production + Preview):

```text
TERMPILOT_ENV=production
TERMPILOT_NOW=
TERMPILOT_FRONTEND_ORIGIN=https://termpilot.org
DATABASE_URL=sqlite+aiosqlite:////tmp/termpilot.db
GROK_MODE=auto
XAI_API_KEY=
TERMPILOT_ACCESS_CODE=
```

3. Add domains `termpilot.org` and `www.termpilot.org`. DNS: apex `A` → `76.76.21.21`, `www` `CNAME` → `cname.vercel-dns-0.com` (or use Vercel nameservers).
4. Deploy. Testers open https://termpilot.org, sign in with any student email, and get an isolated workspace. One-click connectors work without OAuth keys. Calendar and outbound mail still need on-screen approval.
4. Optional: set `XAI_API_KEY` for live Grok, `TERMPILOT_ACCESS_CODE` as a classroom gate, and a Neon/Postgres `DATABASE_URL` so student data survives cold starts.

Same-origin `/api` means no CORS or public backend URL is required. SQLite on `/tmp` is ephemeral (fine for a class trial). Neon persists.

## Environment variables

Copy `.env.example` to `.env`. `XAI_API_KEY` is optional. Never commit it.

## Demo reset and seed

```bash
curl -X POST http://127.0.0.1:8000/demo/reset
```

Frozen clock: `2026-09-05T08:00:00+01:00`.

## Test commands

```bash
make test
make lint
make typecheck
make demo-smoke
```

## Privacy model

Consent-scoped reads, pseudonymous IDs, redacted logs, demo calendar only. [docs/privacy-and-safety.md](docs/privacy-and-safety.md)

## Limitations

- Synthetic LMS / mail / ICS only
- Demo calendar writes only, after on-screen approval
- Live Grok optional
- SQLite on Vercel is per-instance; use Postgres/Neon for durable student data
- No institutional analytics

## Known failures

See [docs/failure-modes.md](docs/failure-modes.md)

## Roadmap

Governed real connectors, optional staff views with aggregation safeguards, mobile-native approvals.

## Competition pitch

[docs/competition-submission.md](docs/competition-submission.md)
