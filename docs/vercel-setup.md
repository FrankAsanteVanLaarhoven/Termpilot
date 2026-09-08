# Point termpilot.org at Vercel

Dashboard: https://vercel.com/frank-asante-van-laarhovens-projects

This machine is logged out of the Vercel CLI, so the domain has to be attached in the browser.

## 1. Import the GitHub repo (once)

1. Open the team dashboard.
2. **Add New… → Project**.
3. Import `FrankAsanteVanLaarhoven/Termpilot`.
4. Root directory: repository root (leave blank / `.`). Do not set it to `frontend/`.
5. Framework: leave detected. `vercel.json` already defines `web` (Next.js) and `api` (FastAPI).
6. Add environment variables (Production **and** Preview):

```text
TERMPILOT_ENV=production
TERMPILOT_NOW=
TERMPILOT_FRONTEND_ORIGIN=https://termpilot.org
DATABASE_URL=sqlite+aiosqlite:////tmp/termpilot.db
GROK_MODE=auto
XAI_API_KEY=
TERMPILOT_ACCESS_CODE=
RESEND_API_KEY=
TERMPILOT_AUTH_FROM=TermPilot <student@termpilot.org>
TERMPILOT_REPLY_TO=support@termpilot.org
```

Leave unused keys **unset** (delete them) rather than blank. Blank `TERMPILOT_PORT` / `GROK_MODE` used to crash login.

## Mail (Resend + termpilot.org)

Receiving aliases (Hostinger mailbox `hello@termpilot.org`):

| Address | Use |
|---|---|
| `student@termpilot.org` | Sign-in / verify codes (From) |
| `support@termpilot.org` | Reply-To |
| `info@termpilot.org` | General inbox |
| `admin@termpilot.org` | Ops |
| `frankvl@termpilot.org` | Personal |
| `hello@termpilot.org` | Primary mailbox |

Sending is Resend, not Hostinger SMTP. Live health currently reports `"mail":"unset"` until the key is on Vercel.

1. Vercel → term-pilot → Settings → Environment Variables → Production **and** Preview → `RESEND_API_KEY`. Paste the key only there. Redeploy. Health must show `"mail":"resend"`.
2. Until `termpilot.org` is verified in Resend, codes send from Resend’s test address `beth.t@example.com` (check spam).
3. In [Resend Domains](https://resend.com/domains) add `termpilot.org`. Copy the **exact** records into Hostinger DNS. Do **not** Reset DNS. Keep `A @ 76.76.21.21`. Do not replace Hostinger’s mailbox SPF/MX — add Resend’s extra `send` / DKIM rows.
4. When Resend shows **Verified**, codes come from `student@termpilot.org`.

7. **Deploy**. Keep Application Preset **Services**, Root Directory `./`. Do not switch the preset to a single FastAPI or Next.js app.

If the API build fails on `../README.md`, that is already fixed on `main`. Redeploy the latest commit.

## 2. Attach the domain

1. Open the TermPilot project → **Settings → Domains**.
2. Add `termpilot.org`.
3. Add `www.termpilot.org` and redirect it to `termpilot.org`.
4. Vercel will show the exact DNS it wants. Use that if it differs.

Default records if you keep DNS at the registrar:

| Type | Name | Value |
|---|---|---|
| A | `@` | `76.76.21.21` |
| CNAME | `www` | `cname.vercel-dns-0.com` |

Or switch the domain’s nameservers to:

- `ns1.vercel-dns.com`
- `ns2.vercel-dns.com`

Then Vercel fills the records itself.

## 3. Check

```bash
dig +short termpilot.org A
# expect 76.76.21.21
curl -sS https://termpilot.org/api/health
```

Health should return `"status":"ok"`. Sign in with any student email. Click the TermPilot mark for Home.

SSL can take a few minutes after DNS answers.
