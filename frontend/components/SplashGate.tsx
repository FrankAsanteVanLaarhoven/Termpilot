"use client";

import { useEffect, useMemo, useState } from "react";
import { GrokBotMark, TermPilotLogo } from "@/components/GrokBotMark";
import { GrokHumanoid, type GrokCue } from "@/components/GrokHumanoid";
import { useI18n } from "@/components/Providers";
import { api, readStudentSession, writeStudentSession } from "@/lib/api";
import { universityEmailIssue } from "@/lib/universityEmail";
import { rememberConnector } from "@/components/workspace";
import type { GrokExpression } from "@/lib/splineGrokRig";

export const GROKBOT_SESSION = "termpilot.grokbot.session";
const ONBOARD_KEY = "termpilot.grokbot.onboard";

const JOBS = [
  { id: "scout", label: "Deadline Scout", note: "Watch authorised sources so nothing due becomes a surprise.", tone: "coral" },
  { id: "planner", label: "Week Planner", note: "Build a 14-day plan around your 20-hour cap.", tone: "cyan" },
  { id: "mail", label: "Mail Desk", note: "Triage P0 mail. Drafts wait for on-screen approval.", tone: "amber" },
  { id: "watch", label: "Conflict Watch", note: "Surface colliding deadlines. Never writes the calendar alone.", tone: "violet" },
] as const;

const TOOLS = [
  { id: "src_email", label: "University email" },
  { id: "src_mailbox", label: "Student inbox" },
  { id: "src_github", label: "GitHub" },
  { id: "src_jira", label: "Jira" },
  { id: "src_notion", label: "Notion" },
  { id: "src_slack", label: "Slack" },
  { id: "src_linkedin", label: "LinkedIn" },
  { id: "src_teams", label: "Microsoft Teams" },
  { id: "src_discord", label: "Discord" },
  { id: "src_gdrive", label: "Google Drive" },
  { id: "src_cal", label: "Demo calendar" },
  { id: "src_lms", label: "University LMS" },
  { id: "src_orcid", label: "ORCID" },
  { id: "src_x", label: "X" },
] as const;

const FOCI = [
  { id: "modules", label: "Modules & deadlines" },
  { id: "recruiting", label: "Recruiting" },
  { id: "international", label: "International student life" },
  { id: "research", label: "Research / ORCID" },
  { id: "wellbeing", label: "Wellbeing signpost" },
  { id: "admin", label: "Campus admin" },
] as const;

type Step = "login" | "verify" | "mfa" | "jobs" | "tools" | "focus";

export function readGrokSession(): boolean {
  try {
    return localStorage.getItem(GROKBOT_SESSION) === "1";
  } catch {
    return false;
  }
}

export function writeGrokSession(on: boolean): void {
  try {
    if (on) localStorage.setItem(GROKBOT_SESSION, "1");
    else {
      localStorage.removeItem(GROKBOT_SESSION);
      localStorage.removeItem(ONBOARD_KEY);
      writeStudentSession(null);
    }
  } catch {
    /* private mode */
  }
}

function toggle(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((item) => item !== id) : [...list, id];
}

export function SplashGate({ onEnter }: { onEnter: () => void }) {
  const { tr } = useI18n();
  const [ready, setReady] = useState(false);
  const [step, setStep] = useState<Step>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [mfaChannel, setMfaChannel] = useState<"email" | "sms">("email");
  const [phoneMasked, setPhoneMasked] = useState<string | null>(null);
  const [accessCode, setAccessCode] = useState("");
  const [xaiKey, setXaiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<string[]>(["scout", "planner"]);
  const [tools, setTools] = useState<string[]>(() => TOOLS.map((item) => item.id));
  const [foci, setFoci] = useState<string[]>(["modules"]);
  const [query, setQuery] = useState("");
  const [accessRequired, setAccessRequired] = useState(false);
  const [mailReady, setMailReady] = useState(true);
  const [signingIn, setSigningIn] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [returning, setReturning] = useState<{ email: string; displayName: string } | null>(null);
  const [overCard, setOverCard] = useState(false);
  const [cue, setCue] = useState<GrokCue>("hello");
  const [line, setLine] = useState("Hi — I'm the G1 we engineered for TermPilot.");

  useEffect(() => {
    const id = window.setTimeout(() => setReady(true), 240);
    const bye = window.setTimeout(() => setCue("idle"), 5600);
    const session = readStudentSession();
    if (readGrokSession() && session) {
      setReturning({ email: session.email, displayName: session.displayName });
    }
    return () => {
      window.clearTimeout(id);
      window.clearTimeout(bye);
    };
  }, []);

  useEffect(() => {
    void api
      .health()
      .then((health) => {
        setAccessRequired(Boolean(health.access_code_required));
        setMailReady(health.mail !== "unset");
      })
      .catch(() => undefined);
  }, []);

  const expression: GrokExpression = useMemo(() => {
    if (step === "login") return "welcome";
    if (step === "verify" || step === "mfa") return "listen";
    if (step === "jobs") return "curious";
    if (step === "tools") return "listen";
    return "think";
  }, [step]);

  const filteredTools = TOOLS.filter((item) => item.label.toLowerCase().includes(query.toLowerCase()));

  function say(next: GrokCue, text: string) {
    setCue(next);
    setLine(text);
  }

  async function signIn() {
    const mail = email.trim().toLowerCase();
    const mailIssue = universityEmailIssue(mail);
    if (mailIssue) {
      setError(mailIssue);
      say("no", "That needs a real campus email — not a personal inbox.");
      return;
    }
    if (password.trim().length < 8) {
      setError("Choose a password of at least 8 characters. First visit creates your account.");
      say("no", "Make the password at least 8 characters.");
      return;
    }
    setError(null);
    if (xaiKey.trim()) {
      try {
        sessionStorage.setItem("termpilot.xai.key", xaiKey.trim());
      } catch {
        /* private mode */
      }
    }
    setSigningIn(true);
    try {
      const profile = await api.login({
        email: mail,
        password,
        access_code: accessRequired ? accessCode || undefined : undefined,
      });
      applyAuth(profile, mail);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not reach TermPilot.";
      setError(message.includes("fetch") ? "Cannot reach the TermPilot API. Try again in a moment." : message);
    } finally {
      setSigningIn(false);
    }
  }

  function applyAuth(
    profile: {
      status: string;
      detail?: string;
      user_id?: string;
      email?: string;
      display_name?: string;
      channel?: string;
      phone_masked?: string | null;
    },
    mail: string,
  ) {
    if (profile.status === "check_email" || profile.status === "verify_email") {
      setError(null);
      setStep("verify");
      return;
    }
    if (profile.status === "verify_phone") {
      setPhoneMasked(profile.phone_masked ?? null);
      setError(null);
      setStep("verify");
      return;
    }
    if (profile.status === "mfa_required") {
      setMfaChannel(profile.channel === "sms" ? "sms" : "email");
      setPhoneMasked(profile.phone_masked ?? null);
      setError(null);
      setStep("mfa");
      return;
    }
    if (profile.user_id) {
      writeStudentSession({
        userId: profile.user_id,
        email: profile.email ?? mail,
        displayName: profile.display_name ?? "Student",
      });
      onEnter();
      void finish(false);
    }
  }

  async function enterDemo() {
    if (signingIn || preparing) return;
    setError(null);
    say("invite", "Opening the demo console.");
    setSigningIn(true);
    try {
      const profile = await api.demoLogin();
      applyAuth(profile, profile.email ?? "demo@termpilot.org");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not reach TermPilot.";
      setError(message.includes("fetch") ? "Cannot reach the TermPilot API. Try again in a moment." : message);
      say("no", "I couldn't reach the API. Try again in a moment.");
    } finally {
      setSigningIn(false);
    }
  }

  async function createAccount() {
    const mail = email.trim().toLowerCase();
    const mailIssue = universityEmailIssue(mail);
    if (mailIssue) {
      setError(mailIssue);
      say("no", "That needs a real campus email — not a personal inbox.");
      return;
    }
    if (password.trim().length < 8) {
      setError("Choose a password of at least 8 characters. First visit creates your account.");
      say("no", "Make the password at least 8 characters.");
      return;
    }
    setError(null);
    setSigningIn(true);
    try {
      const result = await api.register({
        email: mail,
        password,
        phone: phone.trim() || undefined,
        access_code: accessRequired ? accessCode || undefined : undefined,
      });
      applyAuth(result, mail);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not reach TermPilot.";
      setError(message);
    } finally {
      setSigningIn(false);
    }
  }

  async function submitCode() {
    const mail = email.trim().toLowerCase();
    if (!/^\d{6}$/.test(code.trim())) {
      setError("Enter the 6-digit code.");
      return;
    }
    setSigningIn(true);
    setError(null);
    try {
      const profile =
        step === "mfa"
          ? await api.mfa({ email: mail, channel: mfaChannel, code: code.trim() })
          : phoneMasked
            ? await api.verifyPhone({ email: mail, code: code.trim(), phone: phone.trim() || undefined })
            : await api.verifyEmail({ email: mail, code: code.trim(), phone: phone.trim() || undefined });
      setCode("");
      applyAuth(profile, mail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not verify that code.");
    } finally {
      setSigningIn(false);
    }
  }

  async function enterFromLogo() {
    if (signingIn || preparing) return;
    if (!readStudentSession()) {
      await enterDemo();
      return;
    }
    await finish();
  }

  async function finish(enter = true) {
    try {
      localStorage.setItem(
        ONBOARD_KEY,
        JSON.stringify({ jobs, tools, foci, email: email.trim().toLowerCase(), at: new Date().toISOString() }),
      );
    } catch {
      /* private mode */
    }
    setPreparing(true);
    try {
      const prepared = await api.prepare();
      TOOLS.forEach((item) => rememberConnector(item.id, true));
      if (!prepared.connected) {
        await api.connectAll(tools.length ? tools : undefined);
      }
    } catch {
      try {
        await api.connectAll(tools.length ? tools : undefined);
      } catch {
        /* connectors still available in-app */
      }
    } finally {
      setPreparing(false);
    }
    if (enter) onEnter();
  }

  return (
    <div className={`tp-splash ${ready ? "is-on" : ""}`} role="dialog" aria-label={tr("splash.product")}>
      <div className="tp-splash-cosmos" />
      <div className="tp-splash-well" />
      <div className="tp-splash-ribbon" />
      <div className="tp-splash-stars" />
      <div className="tp-splash-vignette" />

      <header className="tp-splash-brand">
        <TermPilotLogo
          size={44}
          mood={step === "login" ? "idle" : "listening"}
          onClick={() => void enterFromLogo()}
        />
      </header>

      <div
        className="tp-splash-stage"
        onClick={() =>
          say("hello", "Hi. I wave, turn, and point. After you enter, talk to Grok Bot — I run the tools, I don't complete assessed work.")
        }
      >
        <GrokHumanoid variant="splash" mood="idle" expression={expression} cue={cue} />
        <div className={`tp-bot-hello ${overCard || cue === "point" ? "is-point" : ""}`}>{line}</div>
      </div>

      <aside
        className="tp-splash-card tp-onboard"
        onMouseEnter={() => {
          setOverCard(true);
          say("point", "Sign in here when you want your own campus workspace.");
        }}
        onMouseLeave={() => {
          setOverCard(false);
          say("idle", "Hover a control and I'll follow.");
        }}
      >
        {step === "login" && (
          <>
            <p className="tp-splash-kicker">{tr("splash.powered")}</p>
            <h1>
              {tr("splash.product")}
              <span>{tr("splash.engine")}</span>
            </h1>
            <p className="tp-splash-tag">{tr("splash.tagline")}</p>
            <p className="tp-splash-hint">{tr("splash.publicDemo")}</p>
            {returning && (
              <button
                type="button"
                className="tp-splash-enter"
                disabled={signingIn || preparing}
                onMouseEnter={() => say("invite", "Welcome back. Continue into the console.")}
                onClick={() => onEnter()}
              >
                {signingIn || preparing ? "Opening…" : tr("splash.continue")}
              </button>
            )}
            <button
              type="button"
              className={returning ? "tp-onboard-back" : "tp-splash-enter"}
              disabled={signingIn || preparing}
              onMouseEnter={() => say("invite", "Tap Try the demo — I'll open a synthetic student week.")}
              onClick={() => void enterDemo()}
            >
              {signingIn || preparing ? "Opening demo…" : tr("splash.demo")}
            </button>
            <p className="tp-splash-hint">{tr("splash.members")}</p>
            <form
              className="tp-login"
              autoComplete="off"
              onSubmit={(event) => {
                event.preventDefault();
                signIn();
              }}
            >
              <label>
                University email
                <input
                  type="email"
                  name="tp-campus-email"
                  autoComplete="off"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  data-1p-ignore="true"
                  data-lpignore="true"
                  placeholder="you@your-university.edu"
                  value={email}
                  onFocus={() => say("listen", "I'm listening. Use the campus email your university issued you.")}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  name="tp-campus-secret"
                  autoComplete="new-password"
                  data-1p-ignore="true"
                  data-lpignore="true"
                  placeholder="at least 8 characters"
                  value={password}
                  onFocus={() => say("yes", "At least 8 characters. I'll wait for you.")}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              {accessRequired && (
                <label>
                  Classroom access code
                  <input
                    type="password"
                    autoComplete="off"
                    placeholder="Ask your lecturer"
                    value={accessCode}
                    onChange={(e) => setAccessCode(e.target.value)}
                  />
                </label>
              )}
              {error && (
                <p className="tp-login-error" role="alert">
                  {error}
                </p>
              )}
              <button type="submit" className="tp-onboard-back" disabled={signingIn || preparing}>
                {signingIn ? "Connecting…" : tr("splash.enter")}
              </button>
              <button type="button" className="tp-onboard-back" disabled={signingIn || preparing} onClick={() => void createAccount()}>
                {tr("splash.create")}
              </button>
            </form>
            <p className="tp-splash-honest">{tr("splash.honest")}</p>
          </>
        )}

        {(step === "verify" || step === "mfa") && (
          <>
            <p className="tp-splash-kicker">{step === "mfa" ? "Two-factor sign-in" : "Verify your account"}</p>
            <h1>
              {step === "mfa" ? "Enter your 2FA code" : phoneMasked ? "Confirm your mobile" : "Check your campus inbox"}
              <span>6-digit code</span>
            </h1>
            <p className="tp-splash-tag">
              {!mailReady
                ? "Verification email is not connected yet, so no code was sent. Go back and sign in — or add RESEND_API_KEY in Vercel first."
                : step === "mfa"
                  ? mfaChannel === "sms"
                    ? `We sent a code to ${phoneMasked ?? "your mobile"}.`
                    : "We sent a code to your university email."
                  : phoneMasked
                    ? `Email confirmed. We sent a code to ${phoneMasked}.`
                    : "If that campus inbox is yours, we sent a code. It expires in 10 minutes. Check spam for student@termpilot.org or beth.t@example.com."}
            </p>
            <form
              className="tp-login"
              onSubmit={(event) => {
                event.preventDefault();
                void submitCode();
              }}
            >
              {step === "mfa" && (
                <label>
                  Send code to
                  <select
                    value={mfaChannel}
                    onChange={(e) => setMfaChannel(e.target.value === "sms" ? "sms" : "email")}
                  >
                    <option value="email">University email</option>
                    <option value="sms">Mobile SMS</option>
                  </select>
                </label>
              )}
              <label>
                6-digit code
                <input
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="123456"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                />
              </label>
              {error && (
                <p className="tp-login-error" role="alert">
                  {error}
                </p>
              )}
              <button type="submit" className="tp-splash-enter" disabled={signingIn}>
                {signingIn ? "Checking…" : "Verify"}
              </button>
              <button
                type="button"
                className="tp-onboard-back"
                disabled={signingIn}
                onClick={() => {
                  setCode("");
                  const mail = email.trim().toLowerCase();
                  const again =
                    step === "mfa"
                      ? api.mfa({ email: mail, channel: mfaChannel })
                      : api.register({
                          email: mail,
                          password,
                          phone: phone.trim() || undefined,
                          access_code: accessRequired ? accessCode || undefined : undefined,
                        });
                  void again.then(
                    (result) => applyAuth(result, mail),
                    (err: unknown) => setError(err instanceof Error ? err.message : "Could not resend."),
                  );
                }}
              >
                Resend code
              </button>
              <button type="button" className="tp-onboard-back" onClick={() => { setStep("login"); setCode(""); setError(null); }}>
                Back to sign in
              </button>
            </form>
          </>
        )}

        {step === "jobs" && (
          <>
            <p className="tp-splash-kicker">Step 1 of 3</p>
            <h1 className="tp-onboard-title">Hand Grok Bot a student job</h1>
            <p className="tp-splash-tag">One engine. Several watches. Nothing is a second trained bot.</p>
            <div className="tp-choice-orbit">
              {JOBS.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  className={`tp-choice-pill tone-${job.tone} ${jobs.includes(job.id) ? "is-on" : ""}`}
                  onClick={() => setJobs(toggle(jobs, job.id))}
                >
                  <span className={`tp-job-face tone-${job.tone}`}>
                    <GrokBotMark size={42} />
                  </span>
                  <strong>{job.label}</strong>
                  <em>{job.note}</em>
                </button>
              ))}
            </div>
            <div className="tp-onboard-nav">
              <button type="button" className="tp-splash-enter" onClick={() => setStep("tools")}>
                Next
              </button>
              <button type="button" className="tp-onboard-back" onClick={() => setStep("login")}>
                Back
              </button>
            </div>
          </>
        )}

        {step === "tools" && (
          <>
            <p className="tp-splash-kicker">Step 2 of 3</p>
            <h1 className="tp-onboard-title">Which authorised tools already belong to you?</h1>
            <p className="tp-splash-tag">
              One-click connect for GitHub, LinkedIn, email, Notion, Slack, Jira and the rest. No OAuth keys
              needed for the demo. Writes still need on-screen approval.
            </p>
            <input
              className="tp-onboard-search"
              placeholder="Search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search tools"
            />
            <div className="tp-choice-grid">
              {filteredTools.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`tp-choice-card ${tools.includes(item.id) ? "is-on" : ""}`}
                  onClick={() => setTools(toggle(tools, item.id))}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <div className="tp-onboard-nav">
              <button type="button" className="tp-splash-enter" onClick={() => setStep("focus")}>
                Next
              </button>
              <button type="button" className="tp-onboard-back" onClick={() => setStep("jobs")}>
                Back
              </button>
            </div>
          </>
        )}

        {step === "focus" && (
          <>
            <p className="tp-splash-kicker">Step 3 of 3</p>
            <h1 className="tp-onboard-title">Where should it watch first?</h1>
            <p className="tp-splash-tag">Student life only. Grok Bot will not complete assessed work.</p>
            <div className="tp-choice-grid">
              {FOCI.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`tp-choice-card ${foci.includes(item.id) ? "is-on" : ""}`}
                  onClick={() => setFoci(toggle(foci, item.id))}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <div className="tp-onboard-nav">
              <button type="button" className="tp-splash-enter" onClick={() => void finish()} disabled={preparing}>
                {preparing ? "Preparing workspace…" : "Enter console"}
              </button>
              <button type="button" className="tp-onboard-back" onClick={() => setStep("tools")}>
                Back
              </button>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
