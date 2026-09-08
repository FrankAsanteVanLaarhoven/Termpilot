# TermPilot

**Verified control tower for student operations.**

TermPilot is an enterprise-grade student workspace that turns authorised campus systems into a single, auditable operating picture: deadlines, conflicts, mail triage, and a feasible 14-day plan. Interpretation is bounded. Dates, consent, identity, and calendar writes are owned by deterministic code — never by a model guessing.

Live product: [https://termpilot.org](https://termpilot.org)  
Repository: [github.com/FrankAsanteVanLaarhoven/Termpilot](https://github.com/FrankAsanteVanLaarhoven/Termpilot)

> No important deadline should become a surprise. TermPilot organises work. It will not complete assessed homework or impersonate a student.

---

## About

Students live across LMS, email, calendar, GitHub, Notion, Slack, Jira and more. TermPilot does not scrape those systems in secret. The student signs in with a **real university email**, consents to each source, and Grok Bot runs the tools already in the app.

**What it is**

- A Next.js command centre plus a FastAPI control plane, deployed as one Vercel project (`/` UI, `/api` backend).
- A provenance pipeline: source observation → claim → obligation → plan block → on-screen approval → demo calendar event.
- A specialist bot layer (Orchestrator, Scout, Verifier, Planner, Guardian, Monitor) that cannot bypass policy.
- A reusable G1 humanoid stage for the live console.

**What it is not**

- Not a homework-completion agent.
- Not institutional surveillance or cohort scoring.
- Not a silent calendar writer. Spoken “yes” is not a write.

---

## How it works (step by step)

### 1. Campus identity

1. Open [termpilot.org](https://termpilot.org) (or local `http://127.0.0.1:3000`).
2. Sign in with the email your university issued (`.edu`, `.ac.uk`, `.edu.au`, `.ac.jp`, and other campus domains worldwide). Personal Gmail/Outlook is rejected.
3. First visit creates an isolated account (password hashed with PBKDF2-SHA256). Next visit signs you back in with an **httpOnly** session cookie.
4. Optional: verify email / SMS 2FA when Resend or Twilio is configured. Until mail is connected, the product will not trap you on a code screen.
5. **Public demo** (no campus inbox required): `info@frankvanlaarhoven.co.uk` / `termpilot`.

Each student is namespaced (`stu_<hash>`). Demo identity stays `FAVL`. Queries never cross accounts.

### 2. Connect sources (one click)

From **Connected services**, the student connects:

GitHub, LinkedIn, university email, mailbox, Notion, Slack, Jira, Teams, Discord, Google Drive, demo calendar, LMS, ORCID, X.

- Fixture adapters load immediately so the tower is testable.
- Live OAuth starts only when the matching client id/secret is set in the environment.
- Connect does not auto-open a provider window. Calendar and outbound mail still need a later on-screen approval.

### 3. Scout authorised content

The **Scout** bot reads only sources the student granted. LMS pages, mail and uploads are treated as untrusted. Prompt-injection sentences are stripped and never executed.

Extracted items become `SourceObservation` rows with source type, authority, observation time, and an evidence excerpt. Raw HTML mail is not stored.

### 4. Verify, do not guess

The **Verifier** deduplicates claims, keeps both evidence rows on a merge, and escalates contradictory deadlines. TermPilot **does not invent** due dates or free slots. If a date is missing, the obligation is marked incomplete — it is not fabricated.

### 5. Surface conflicts and attention

The control tower (**My week**) shows:

- verified obligations
- open conflicts the student must decide
- mail that needs triage
- connector health (degraded if a source is stale or down)

The student — not the model — resolves conflicts.

### 6. Build a feasible 14-day plan

**Planner** calls Google OR-Tools CP-SAT with:

- a 14-day horizon
- a 20-hour weekly study cap (configurable)
- sleep windows, commute, existing calendar busy times
- safety buffer before deadlines

Grok may *explain* the plan. It does not place the blocks. If the solver is infeasible, TermPilot says so.

### 7. Approve writes on screen

**Guardian** fail-closes without consent. Calendar writes require:

- a pending approval record
- unexpired TTL
- target `demo_calendar` only in this deployment
- matching idempotency keys so replay cannot double-write

Outbound mail is drafted, never sent on a spoken yes. The student confirms in the UI.

### 8. Monitor for material change

**Monitor** rechecks authorised sources on a schedule and alerts only when something material changes (new deadline, moved due date, new P0 mail). It does not nag and it does not complete work.

---

## System architecture

```
Browser (Next.js)  ──same origin /api──►  FastAPI control plane
        │                                      │
        │  Grok Bot UI, G1 humanoid            │  Identity, consent, connectors
        │  Mail desk, My week, Approvals       │  Scout → Verifier → Planner
        └──────────────────────────────────────┤  Guardian + approval ledger
                                               │  OR-Tools CP-SAT
                                               ▼
                                         SQLite / Postgres
```

| Layer | Owner | Responsibility |
| --- | --- | --- |
| Grok Bot | Interpretation | Intent, extraction from messy text, explanations |
| FastAPI | System of record | Identity, hashing, cookies, rate limits, schema, timezones |
| Verifier | Integrity | Duplicates, conflicting claims, verification state |
| Planner | Operations research | Feasible 14-day blocks under hard caps |
| Guardian | Policy | Consent, injection strip, assessed-work block, approval |
| Next.js | Experience | Splash, home, connectors, mail, week, G1 stage |

Full design: [docs/architecture.md](docs/architecture.md).  
Privacy model: [docs/privacy-and-safety.md](docs/privacy-and-safety.md).  
Failure modes: [docs/failure-modes.md](docs/failure-modes.md).

### Specialist bots

| Bot | Job | Cannot |
| --- | --- | --- |
| Orchestrator | Decompose the student goal | Bypass Guardian or Verifier |
| Scout | Fetch consented sources | Invent deadlines |
| Verifier | Merge and escalate | Silently drop a conflict |
| Planner | Call CP-SAT and explain | Place slots the solver did not return |
| Guardian | Consent, integrity, approval | Complete assessed work |
| Monitor | Recheck sources | Hidden surveillance |

---

## Product surfaces

| Surface | What the student sees |
| --- | --- |
| Home | “What needs your attention today?” plus Grok Bot |
| Connected services | One-click connectors |
| Automations | Bounded workflows |
| Messages | Authorised mailbox desk |
| News | Government / campus / community feeds (source labelled) |
| My week | Verified obligations, conflicts, 14-day plan |
| Approvals | Pending calendar and mail writes |
| Evidence | Why TermPilot made a claim |

---

## Security and governance

- **Campus email gate** — worldwide academic domains (`.edu`, `.ac.*`, `.edu.*`, known campuses). Consumer Gmail/Outlook blocked.
- **Passwords** — PBKDF2-SHA256, 120k iterations. Dummy-hash on unknown users (no account enumeration).
- **Sessions** — `tp_session` httpOnly, SameSite=Lax, Secure in production. Cache-Control: no-store on API responses.
- **Rate limits** — login / register / verify buckets committed independently so a 401 cannot roll the counter back.
- **Email codes** — hashed OTPs via Resend from `student@termpilot.org` when `RESEND_API_KEY` is set and the domain is verified. Reply-To: `support@termpilot.org`.
- **Logs** — tokens, passwords, OTPs, and raw mail bodies redacted.
- **Tenancy** — every row is `user_id` scoped. Production ignores spoofable `X-User-Id` when a session cookie is required.

---

## Stack

| Concern | Technology |
| --- | --- |
| UI | Next.js 15, React 19, TypeScript |
| API | FastAPI, SQLAlchemy 2, Pydantic v2 |
| Plan | OR-Tools CP-SAT |
| 3D stage | Three.js + Unitree G1 URDF (FAVL chest mark) |
| Hosting | Vercel Services (web + Python) |
| Mail (optional) | Resend |
| SMS 2FA (optional) | Twilio |

---

## Quick start (local)

```bash
git clone https://github.com/FrankAsanteVanLaarhoven/Termpilot.git
cd Termpilot
make install
make backend    # terminal 1 — FastAPI :8000
make frontend   # terminal 2 — Next.js :3000
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). The UI proxies `/api` to FastAPI.

```bash
docker compose up --build
```

### Public demo

| | |
| --- | --- |
| Email | `info@frankvanlaarhoven.co.uk` |
| Password | `termpilot` |

Or create an isolated student account with any real campus email.

### Tests

```bash
make test
make lint
make typecheck
make demo-smoke
```

Demo seed (disabled in production):

```bash
curl -X POST http://127.0.0.1:8000/demo/reset
```

Frozen competition clock (optional): `2026-09-05T08:00:00+01:00`.

Reusable G1 pack: `node packages/g1-humanoid/scripts/pack.mjs`

---

## Production deployment

One Vercel project, two services: Next.js at `/`, FastAPI at `/api`. Setup detail: [docs/vercel-setup.md](docs/vercel-setup.md).

1. Import this repository. Root directory = repository root. Keep the **Services** preset.
2. Environment (Production and Preview):

```text
TERMPILOT_ENV=production
TERMPILOT_FRONTEND_ORIGIN=https://termpilot.org
DATABASE_URL=sqlite+aiosqlite:////tmp/termpilot.db
GROK_MODE=auto
XAI_API_KEY=
RESEND_API_KEY=
TERMPILOT_AUTH_FROM=TermPilot <student@termpilot.org>
TERMPILOT_REPLY_TO=support@termpilot.org
TERMPILOT_ACCESS_CODE=
```

Leave unused keys **unset**, not blank.

3. Domains: `termpilot.org` (A `76.76.21.21`), `www` CNAME to Vercel.
4. For durable student data use Neon/Postgres in `DATABASE_URL`.
5. For campus verification mail: add `termpilot.org` in Resend, Hostinger DNS for DKIM + `send`/`rsend` CNAMEs (do not Reset DNS; keep Hostinger MX for inbound aliases).

---

## Limitations (current release)

- Connector catalogue uses fixture adapters unless OAuth secrets are present.
- Calendar writes target the **demo calendar** only, after on-screen approval.
- SQLite on Vercel `/tmp` is per-instance; use Postgres for persistence.
- No institutional analytics or staff dashboards in this MVP.

## Roadmap

Governed live connectors, optional staff views with aggregation safeguards, mobile-native approvals, and durable multi-region identity.

---

## Author

**Frank Asante Van Laarhoven**  
[github.com/FrankAsanteVanLaarhoven](https://github.com/FrankAsanteVanLaarhoven) · [termpilot.org](https://termpilot.org)

Grok Bot template: [x.ai/bot/OeUkDHEV4ykNb2EDpUO1m](https://x.ai/bot/OeUkDHEV4ykNb2EDpUO1m)
