# Install TermPilot as a Grok Bot template

Others should be able to work with this Bot from the share, without your computer or secrets.

Official Grok Bot sharing: [Create and manage Bots](https://docs.x.ai/grok-bot/bots).

## Option A — Add from a public x.ai share (best)

Public TermPilot template:

**https://x.ai/bot/OeUkDHEV4ykNb2EDpUO1m**

If that link is in the LinkedIn post:

1. Open the link.
2. Review identity, description, skills and requested tools.
3. Choose **Add to Grok Bot**.
4. Connect only the tools you authorise. Calendar and mail stay behind approval.

To *publish* that link from your Grok Bot app: open TermPilot → **Share as template** (or copy share link). Strip API keys and student data first. The link is public.

## Option B — Paste this repo (works today)

1. In Grok Bot: **New → Create new agent**.
2. **Bot actions → Edit Profile**. Name it **TermPilot**.
3. Paste [`PROFILE.md`](./PROFILE.md) as the description.
4. Attach the skills in [`../skills/`](../skills/) (`extract-obligations`, `verify-deadlines`, `build-feasible-plan`, `safe-calendar-write`, `privacy-and-integrity-check`).
5. Send the first task from PROFILE.md. Do not enable calendar write until you have seen a pending approval.

Raw profile URL (once this branch is on GitHub):

```
https://raw.githubusercontent.com/FrankAsanteVanLaarhoven/Termpilot/main/grok/template/PROFILE.md
```

## Option C — Run the interactive product

The hosted TermPilot app is the full Grok Bot student surface (Home, My week, Messages, one-click GitHub/LinkedIn/Notion/Slack/Jira). Sign in with any student email. No OAuth keys required for the labelled fixture adapters.

Repo: https://github.com/FrankAsanteVanLaarhoven/Termpilot

## Safety

- Guardian never bypasses.
- Spoken yes is not a write.
- Assessed work is not completed.
- Shared templates must not include secrets, custom MCP, or personal memories.
