"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DEMO_COMMAND,
  HOME_VIEW,
  api,
  AuthRequiredError,
  readLastView,
  readStudentSession,
  writeLastView,
  type AgentRun,
  type Approval,
  type AttentionItem,
  type AuditEvent,
  type CommandResult,
  type ConflictItem,
  type GraphEdge,
  type GraphNode,
  type ImpactBundle,
  type Obligation,
  type Plan,
  type SourcesResponse,
  type TowerResponse,
  type ViewId,
  type WorkspaceBundle,
} from "@/lib/api";
import { Badge, Metric, Panel, clockFmt, fmt, stateTone } from "@/components/ui";
import {
  ConnectorsPanel,
  QuickCalendar,
  WorkflowBoard,
  WorkspaceHub,
  rememberConnector,
  rememberedConnectors,
} from "@/components/workspace";
import { VoiceBridge } from "@/components/VoiceBridge";
import { LifeWidgets } from "@/components/LifeWidgets";
import { useI18n } from "@/components/Providers";
import { LOCALE_LABEL, LOCALES } from "@/lib/i18n";
import { REGIONS, TIMEZONES, maturityLabel, packFor, regionInfo } from "@/lib/localeRegistry";
import { GrokBotMark, TermPilotLogo } from "@/components/GrokBotMark";
import { NewsFeed } from "@/components/NewsFeed";
import { AccountMenu, HelpView, WidgetEditor } from "@/components/AccountMenu";
import { MailboxDesk } from "@/components/MailboxDesk";
import { CookieBanner } from "@/components/CookieBanner";
import { ModelDock } from "@/components/ModelDock";
import { GrokHumanoid, type BotMood } from "@/components/GrokHumanoid";
import { MemberShield } from "@/components/MemberShield";
import { SplashGate, readGrokSession, writeGrokSession } from "@/components/SplashGate";
import { NavGlyph } from "@/components/NavGlyph";

const NAV: { id: ViewId; student: string | null; proof: string }[] = [
  { id: "chat", student: "nav.student.home", proof: "nav.chat" },
  { id: "tower", student: "nav.student.tower", proof: "nav.tower" },
  { id: "news", student: "nav.student.news", proof: "nav.news" },
  { id: "mailbox", student: "nav.student.mailbox", proof: "nav.mailbox" },
  { id: "workspace", student: "nav.student.workspace", proof: "nav.workspace" },
  { id: "calendar", student: "nav.student.calendar", proof: "nav.calendar" },
  { id: "obligations", student: "nav.student.obligations", proof: "nav.obligations" },
  { id: "timeline", student: "nav.student.timeline", proof: "nav.timeline" },
  { id: "conflicts", student: "nav.student.conflicts", proof: "nav.conflicts" },
  { id: "sources", student: "nav.student.connectors", proof: "nav.connectors" },
  { id: "workflows", student: "nav.student.workflows", proof: "nav.workflows" },
  { id: "agents", student: null, proof: "nav.agents" },
  { id: "approvals", student: "nav.student.approvals", proof: "nav.approvals" },
  { id: "evidence", student: "nav.student.evidence", proof: "nav.evidence" },
  { id: "impact", student: "nav.student.impact", proof: "nav.impact" },
  { id: "settings", student: "nav.student.settings", proof: "nav.settings" },
];

function navKey(item: (typeof NAV)[number], mode: "student" | "proof"): string {
  if (mode === "proof") return item.proof;
  return item.student ?? item.proof;
}

export default function Page() {
  const { tr, locale, setLocale, theme, setTheme, uiMode, setUiMode } = useI18n();
  const [view, setView] = useState<ViewId>("chat");
  const [tower, setTower] = useState<TowerResponse | null>(null);
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [sources, setSources] = useState<SourcesResponse | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [impact, setImpact] = useState<ImpactBundle | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [command, setCommand] = useState(DEMO_COMMAND);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<CommandResult | null>(null);
  const [paused, setPaused] = useState(false);
  const [outage, setOutage] = useState(false);
  const [workspace, setWorkspace] = useState<WorkspaceBundle | null>(null);
  const [navPinned, setNavPinned] = useState(false);
  const [navHover, setNavHover] = useState(false);
  const [headerHover, setHeaderHover] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [consolePinned, setConsolePinned] = useState(false);
  const [consoleHover, setConsoleHover] = useState(false);
  const consoleOpen = consolePinned || consoleHover;
  const [liveAt, setLiveAt] = useState<string | null>(null);
  const [me, setMe] = useState<{ display_name: string; user_id: string; email?: string } | null>(null);
  const [gate, setGate] = useState<"boot" | "splash" | "app">("boot");
  const [botMood, setBotMood] = useState<BotMood>("idle");
  const [botMode, setBotMode] = useState("work");
  const [modelId, setModelId] = useState("grok-4.6");
  const [tool, setTool] = useState("search");
  const [chatInput, setChatInput] = useState("");
  const [chatTurns, setChatTurns] = useState<{ you: string; bot: string; intent: string }[]>([]);
  const [chatBusy, setChatBusy] = useState(false);
  const [peers, setPeers] = useState<{ code: string; name: string; context: string }[]>([]);
  const [invites, setInvites] = useState<{ id: string; to_name: string; task_title: string; state: string }[]>([]);
  const navOpen = navPinned || navHover;
  const preparedRef = useRef(false);
  const authRetryRef = useRef(0);
  const [hydrated, setHydrated] = useState(false);

  const load = useCallback(async () => {
    try {
      if (!preparedRef.current) {
        try {
          await api.prepare();
          preparedRef.current = true;
        } catch {
          /* retry on the next poll if the API is still waking */
        }
      }
      const [t, o, c, s, p, a, r, e, g, i, w] = await Promise.all([
        api.tower(),
        api.obligations(),
        api.conflicts(),
        api.sources(),
        api.plans(),
        api.approvals(),
        api.runs(),
        api.audit(),
        api.graph(),
        api.impact(),
        api.workspace(),
      ]);
      setTower(t);
      setObligations(o.items);
      setConflicts(c.items);
      setSources(s);
      setPlan(p.plan);
      setApprovals(a.items);
      setRuns(r.items);
      setAudit(e.items);
      setGraph(g);
      setImpact(i);
      let workspaceData = w;
      const remembered = rememberedConnectors();
      const missing = workspaceData.connectors
        .filter((connector) => !connector.connected && remembered.includes(connector.id))
        .map((connector) => connector.id);
      if (missing.length) {
        await api.connectAll(missing);
        workspaceData = await api.workspace();
      }
      workspaceData.connectors
        .filter((connector) => connector.connected)
        .forEach((connector) => rememberConnector(connector.id, true));
      setWorkspace(workspaceData);
      setLiveAt(workspaceData.now);
      const profile = await api.me();
      setMe({
        display_name: profile.display_name,
        user_id: profile.user_id,
        email: profile.email ?? "demo@termpilot.org",
      });
      const collab = await api.collaborate();
      setPeers(collab.peers);
      setInvites(collab.items);
      setError(null);
      authRetryRef.current = 0;
    } catch (err) {
      if (err instanceof AuthRequiredError) {
        const student = readStudentSession();
        if (student && authRetryRef.current < 1) {
          authRetryRef.current += 1;
          if (student.userId === "FAVL") {
            try {
              await api.demoLogin();
            } catch {
              writeGrokSession(false);
              setGate("splash");
              return;
            }
          }
          preparedRef.current = false;
          await load();
          return;
        }
        writeGrokSession(false);
        setGate("splash");
        return;
      }
      setError(err instanceof Error ? err.message : "load_failed");
    }
  }, []);

  useEffect(() => {
    setGate(readGrokSession() && readStudentSession() ? "app" : "splash");
    setView(readLastView());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    writeLastView(view);
  }, [hydrated, view]);

  useEffect(() => {
    if (gate !== "app") return;
    void load();
    const tick = window.setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, 8000);
    return () => window.clearInterval(tick);
  }, [load, gate]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "[") setNavPinned((v) => !v);
      if (event.key === "]") setInspectorOpen((v) => !v);
      if (event.key === "/" && uiMode === "proof") setConsolePinned((v) => !v);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [uiMode]);

  function goHome() {
    setView(HOME_VIEW);
    setNavPinned(false);
  }

  async function runCommand() {
    setBusy(true);
    setStatus("Orchestrator running");
    setError(null);
    try {
      const result = await api.command(command, outage);
      setLastResult(result);
      setStatus(result.final_status);
      await load();
      if (result.unresolved_uncertainties.includes("deadline_conflict_requires_human")) {
        setView("conflicts");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "command_failed");
      setStatus("failed");
    } finally {
      setBusy(false);
    }
  }

  async function askGrokBot(text: string) {
    const cleaned = text.trim();
    if (!cleaned || paused || chatBusy) return;
    setChatBusy(true);
    setBotMood("processing");
    setError(null);
    try {
      const result = await api.grokTurn(cleaned);
      setChatTurns((prev) => [...prev, { you: cleaned, bot: result.display_text, intent: result.intent }]);
      setChatInput("");
      setBotMood("speaking");
      const panel = result.facts?.open_view;
      const allowed: ViewId[] = [
        "chat",
        "tower",
        "news",
        "mailbox",
        "workspace",
        "calendar",
        "obligations",
        "timeline",
        "conflicts",
        "sources",
        "workflows",
        "approvals",
        "evidence",
        "impact",
        "settings",
        "help",
      ];
      if (typeof panel === "string" && allowed.includes(panel as ViewId) && panel !== "chat") {
        setView(panel as ViewId);
      }
      await load();
      window.setTimeout(() => setBotMood("idle"), 1600);
    } catch (err) {
      setError(err instanceof Error ? err.message : "grokbot_failed");
      setBotMood("idle");
    } finally {
      setChatBusy(false);
    }
  }

  const selectedObligation = obligations.find((o) => o.obligation_id === selectedId) ?? null;
  const selectedConflict = conflicts.find((c) => c.id === selectedId) ?? null;
  const relatedBlocks = useMemo(
    () =>
      (plan?.blocks ?? []).filter(
        (b) =>
          b.obligation_id === selectedId ||
          (selectedConflict && b.obligation_id === selectedConflict.obligation_id),
      ),
    [plan, selectedId, selectedConflict],
  );

  const tools = NAV.filter((item) => item.id !== "chat").filter(
    (item) => uiMode === "proof" || item.student !== null,
  );
  const proof = uiMode === "proof";

  useEffect(() => {
    if (uiMode === "student" && view === "agents") setView("tower");
  }, [uiMode, view]);

  if (gate === "boot") {
    return <div className="tp-boot" aria-hidden />;
  }
  if (gate === "splash") {
    return (
      <SplashGate
        onEnter={() => {
          writeGrokSession(true);
          setGate("app");
        }}
      />
    );
  }

  return (
    <MemberShield>
    <div className="flex min-h-screen bg-navy text-ink">
      <div
        className="relative z-20"
        onMouseEnter={() => setNavHover(true)}
        onMouseLeave={() => setNavHover(false)}
      >
        <button
          className="absolute left-0 top-1/2 z-30 h-16 w-2.5 -translate-y-1/2 rounded-r-full tp-glass"
          aria-label={navPinned ? tr("hdr.hideNav") : tr("hdr.showNav")}
          onClick={() => setNavPinned((v) => !v)}
        />
      {navOpen && (
        <nav className="tp-sidebar flex h-screen w-[248px] shrink-0 flex-col" aria-label="Primary">
          <div className="flex items-center gap-2 px-4 py-5">
            <TermPilotLogo size={32} compact mood={botMood} onClick={goHome} />
          </div>
          <button
            onClick={goHome}
            className={`tp-nav-item ${view === "chat" ? "active" : ""}`}
          >
            <NavGlyph id="chat" />
            {tr(uiMode === "proof" ? "nav.chat" : "nav.student.home")}
          </button>
          <div className="mt-5 px-5 text-[11px] font-medium uppercase tracking-[0.14em] text-mute">
            {tr("hdr.tools")}
          </div>
          <div className="tp-scroll mt-1 flex-1 overflow-auto pb-3">
            {tools.map((item) => (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                className={`tp-nav-item ${view === item.id ? "active" : ""}`}
              >
                <NavGlyph id={item.id} />
                {tr(navKey(item, uiMode))}
              </button>
            ))}
          </div>
          <div className="mt-auto border-t border-transparent px-2 py-3">
            <AccountMenu
              name={me?.display_name ?? "Demo student"}
              username={me?.user_id ?? "FAVL"}
              email={me?.email ?? "demo@termpilot.org"}
              onOpen={(next) => {
                setView(next);
                setNavPinned(true);
              }}
              onPin={() => setNavPinned(true)}
              onSignOut={() => {
                void api.logout().catch(() => undefined);
                writeGrokSession(false);
                setGate("splash");
              }}
            />
          </div>
        </nav>
      )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
      <header
        className="tp-glass-strong relative z-10 border-b"
        onMouseEnter={() => setHeaderHover(true)}
        onMouseLeave={() => setHeaderHover(false)}
      >
        <div className="flex items-center justify-between gap-3 px-4 py-2">
        <div className="flex items-center gap-2 font-semibold tracking-wide">
          {!navOpen && <TermPilotLogo size={28} compact mood={botMood} onClick={goHome} />}
          {navOpen && (
            <button type="button" className="tp-logo compact" onClick={goHome} aria-label={tr("hdr.home")}>
              <span className="tp-logo-word">TermPilot</span>
            </button>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] text-mute">
          {proof ? (
            <Badge tone={tower?.tower.mode === "OFFLINE" ? "stop" : "cyan"}>
              {tower?.tower.mode ?? "DEMO"}
            </Badge>
          ) : (
            <Badge tone={tower?.tower.open_conflicts || tower?.tower.pending_approvals ? "warn" : "go"}>
              {tower?.tower.open_conflicts || tower?.tower.pending_approvals ? tr("tower.attention") : tr("hdr.ready")}
            </Badge>
          )}
          {proof && <span>{tower?.tower.readiness ?? "LOADING"}</span>}
          {proof && <span>{tower ? fmt(tower.tower.now) : "—"} {tower?.tower.timezone}</span>}
          {proof && <span>sync {fmt(tower?.tower.last_reconciliation_at)}</span>}
          {proof && (
            <span>
              {tower?.tower.grok_state === "fake" ? tr("hdr.grokSimulated") : `grok ${tower?.tower.grok_state ?? "—"}`}
            </span>
          )}
          {!proof && <span className="text-[10px]">{tr("hdr.powered")}</span>}
          <span className="text-go">{tr("hdr.live")} {liveAt ? fmt(liveAt) : "…"}</span>
        </div>
        {proof && !headerHover && (
          <span className="font-mono text-[10px] text-mute">hover for controls</span>
        )}
        </div>
        {headerHover && (
        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-steel px-4 py-2">
          <select
            className="border border-steel bg-navy px-2 py-1 font-mono text-[11px]"
            value={locale}
            onChange={(e) => setLocale(e.target.value as typeof locale)}
            aria-label={tr("settings.language")}
          >
            {LOCALES.map((code) => (
              <option key={code} value={code}>
                {LOCALE_LABEL[code]}
              </option>
            ))}
          </select>
          <select
            className="border border-steel bg-navy px-2 py-1 font-mono text-[11px]"
            value={uiMode}
            onChange={(e) => setUiMode(e.target.value as typeof uiMode)}
            aria-label={tr("mode.label")}
          >
            <option value="student">{tr("mode.student")}</option>
            <option value="proof">{tr("mode.proof")}</option>
          </select>
          <select
            className="border border-steel bg-navy px-2 py-1 font-mono text-[11px]"
            value={theme}
            onChange={(e) => setTheme(e.target.value as typeof theme)}
            aria-label={tr("settings.theme")}
          >
            <option value="dark">{tr("theme.dark")}</option>
            <option value="light">{tr("theme.light")}</option>
            <option value="system">{tr("theme.system")}</option>
          </select>
          <button
            className="border border-steel px-2 py-1 font-mono text-[11px] text-mute"
            onClick={() => setNavPinned((v) => !v)}
            aria-pressed={navPinned}
          >
            {navPinned ? tr("hdr.hideNav") : tr("hdr.showNav")}
          </button>
          <button
            className="border border-steel px-2 py-1 font-mono text-[11px] text-mute"
            onClick={() => setInspectorOpen((v) => !v)}
            aria-pressed={inspectorOpen}
          >
            {inspectorOpen ? tr("hdr.hideInspector") : tr("hdr.showInspector")}
          </button>
          <button
            className="border border-steel px-2 py-1 font-mono text-[11px] text-mute"
            onClick={() => setConsolePinned((v) => !v)}
            aria-pressed={consolePinned}
          >
            {consolePinned ? "Auto-hide console" : "Pin console"}
          </button>
          <button
            className="border border-stop/50 px-3 py-1 font-mono text-[11px] uppercase text-stop"
            onClick={() => setPaused((v) => !v)}
          >
            {paused ? tr("hdr.resume") : tr("hdr.pause")}
          </button>
        </div>
        )}
      </header>

        <main className="tp-scroll relative min-h-0 flex-1 overflow-auto">
          {view === "chat" && (
            <div className="mx-auto flex min-h-full max-w-3xl flex-col justify-center px-6 py-10">
              <h1 className="text-center text-3xl font-semibold">{tr("chat.hello")}</h1>
              <p className="mx-auto mt-3 max-w-xl text-center text-sm text-mute">{tr("chat.hint")}</p>
              <p className="mx-auto mt-2 max-w-xl text-center text-xs text-mute">{tr("chat.safety")}</p>
              <p className="mx-auto mt-3 max-w-xl text-center text-xs text-cyan">{tr("chat.howTo")}</p>
              <div className="mx-auto mt-6 w-full max-w-xl">
                <GrokHumanoid
                  variant="stage"
                  mood={botMood}
                  expression={
                    botMood === "speaking" ? "glad" : botMood === "listening" ? "listen" : botMood === "processing" ? "think" : "idle"
                  }
                />
              </div>
              <div className="tp-glass mt-4 flex items-center justify-between rounded-2xl px-4 py-3">
                <div className="flex items-center gap-3">
                  <GrokBotMark size={40} mood={botMood} />
                  <div>
                    <div className="text-sm font-medium">{tr("grokbot.name")}</div>
                    <div className="text-xs text-mute">{tr("grokbot.tagline")}</div>
                    <div className="mt-1 font-mono text-[10px] text-mute">{tr("chat.powered")}</div>
                  </div>
                </div>
                <button
                  className="rounded-full border border-cyan px-4 py-2 text-xs text-cyan"
                  onClick={() => setView("tower")}
                >
                  {tr("chat.reviewWeek")}
                </button>
              </div>
              <div className="mx-auto mt-6 w-full max-w-xl">
                <ModelDock
                  mode={botMode}
                  onMode={(id) => {
                    setBotMode(id);
                    if (id === "computer") setView("sources");
                    if (id === "work") setView("tower");
                  }}
                  modelId={modelId}
                  onModel={setModelId}
                  tool={tool}
                  onTool={(id) => {
                    setTool(id);
                    if (id === "deep_research") setView("news");
                    if (id === "learn") setView("timeline");
                  }}
                />
              </div>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {[
                  { id: "obligations" as const, label: tr("chat.action.deadlines"), ask: "What deadlines need my attention?" },
                  { id: "tower" as const, label: tr("chat.action.plan"), ask: "What should I focus on this week?" },
                  { id: "mailbox" as const, label: "Open messages", ask: "open mailbox" },
                  { id: "news" as const, label: tr("chat.action.support"), ask: "show the newsfeed" },
                  { id: "workflows" as const, label: "Run automations", ask: "show automations" },
                  { id: "workspace" as const, label: "Open workspace", ask: "open my workspace" },
                ].map((chip, index) => (
                  <button
                    key={`${chip.label}-${index}`}
                    className="rounded-full border border-steel px-3 py-1 text-xs text-mute hover:text-ink"
                    onClick={() => {
                      setView(chip.id);
                      if (chip.ask) void askGrokBot(chip.ask);
                    }}
                  >
                    {chip.label}
                  </button>
                ))}
              </div>
              {chatTurns.length > 0 && (
                <div className="mx-auto mt-5 w-full max-w-xl space-y-3">
                  {chatTurns.slice(-4).map((turn, index) => (
                    <div key={`${turn.intent}-${index}`} className="tp-glass rounded-2xl px-4 py-3 text-sm">
                      <div className="font-mono text-[10px] uppercase text-mute">you · {turn.intent}</div>
                      <div className="mt-1 text-ink">{turn.you}</div>
                      <div className="mt-2 text-cyan">{turn.bot}</div>
                    </div>
                  ))}
                </div>
              )}
              <form
                className="mx-auto mt-5 flex w-full max-w-xl gap-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  void askGrokBot(chatInput);
                }}
              >
                <input
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  placeholder="Ask Grok Bot — connect university email, deadlines, mail, plan. Writes still need approval."
                  className="min-w-0 flex-1 rounded-full border border-steel bg-navy px-4 py-3 text-sm text-ink"
                  aria-label="Ask Grok Bot"
                  disabled={paused || chatBusy}
                />
                <button
                  type="submit"
                  className="rounded-full border border-cyan bg-cyan/10 px-4 py-3 text-xs uppercase text-cyan disabled:opacity-40"
                  disabled={paused || chatBusy}
                >
                  {chatBusy ? "…" : "Ask"}
                </button>
              </form>
            </div>
          )}
          {view !== "chat" && (
          <div className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-[11px] uppercase text-mute">
              {proof ? "ephemeral · " : ""}
              {tr(navKey(NAV.find((n) => n.id === view) ?? NAV[1], uiMode))}
            </span>
            <button className="tp-pill" onClick={goHome}>
              {tr("hdr.home")}
            </button>
          </div>
          {error && (
            <div className="tp-glass tp-card mb-3 text-sm text-stop" role="alert">
              {error}
            </div>
          )}
          {view === "tower" && (
            <Tower
              tower={tower}
              obligations={obligations}
              plan={plan}
              runs={runs}
              selectedId={selectedId}
              onSelect={(id) => {
                setSelectedId(id);
              }}
              onOpenConflicts={() => setView("conflicts")}
            />
          )}
          {view === "obligations" && (
            <ObligationTable
              items={obligations}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          )}
          {view === "timeline" && (
            <Timeline plan={plan} selectedId={selectedId} onSelect={setSelectedId} />
          )}
          {view === "conflicts" && (
            <Conflicts
              items={conflicts}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onResolved={load}
            />
          )}
          {view === "news" && <NewsFeed />}
          {view === "mailbox" && <MailboxDesk onChange={load} />}
          {view === "help" && <HelpView />}
          {view === "workspace" && <WorkspaceHub data={workspace} onChange={load} />}
          {view === "calendar" && (
            <Panel title="Seven-day live calendar">
              <QuickCalendar days={workspace?.calendar.days ?? []} />
            </Panel>
          )}
          {view === "workflows" && <WorkflowBoard data={workspace} onChange={load} />}
          {view === "sources" && (
            <div className="space-y-4">
              <ConnectorsPanel items={workspace?.connectors ?? []} onChange={load} />
              <Sources data={sources} />
            </div>
          )}
          {view === "agents" && <Agents runs={runs} />}
          {view === "approvals" && <Approvals items={approvals} onChange={load} />}
          {view === "evidence" && (
            <Evidence audit={audit} graph={graph} selectedId={selectedId} onSelect={setSelectedId} />
          )}
          {view === "impact" && <Impact data={impact} />}
          {view === "settings" && (
            <Settings
              outage={outage}
              setOutage={setOutage}
              onReset={async () => {
                await api.reset();
                await load();
                setStatus("reset");
              }}
              onMonitor={async () => {
                await api.monitor();
                await load();
              }}
            />
          )}
          </div>
          )}
        {inspectorOpen && (
          <aside className="tp-sidebar absolute right-0 top-0 z-20 h-full w-[320px] overflow-auto p-3" aria-label="Inspector" style={{ borderRight: "none", borderLeft: "1px solid var(--tp-glass-border)" }}>
            <Inspector
              obligation={selectedObligation}
              conflict={selectedConflict}
              blocks={relatedBlocks}
              attention={tower?.attention ?? []}
            />
            <div className="mt-4 border-t border-steel pt-3">
              <h3 className="font-mono text-[11px] uppercase text-mute">Invite a student</h3>
              <p className="mt-1 text-xs text-mute">Student-controlled. No cohort scoring.</p>
              <ul className="mt-2 space-y-2">
                {peers.map((peer) => (
                  <li key={peer.code} className="flex items-center justify-between gap-2 text-sm">
                    <span>
                      {peer.name}
                      <span className="block font-mono text-[10px] text-mute">{peer.context}</span>
                    </span>
                    <button
                      className="tp-pill"
                      onClick={() =>
                        void api
                          .invite(peer.code, selectedObligation?.obligation_id ?? null, "Study together")
                          .then(load)
                      }
                    >
                      Invite
                    </button>
                  </li>
                ))}
              </ul>
              {invites.length > 0 && (
                <p className="mt-2 font-mono text-[11px] text-mute">
                  {invites.length} invite(s) · {invites[0].to_name} · {invites[0].state}
                </p>
              )}
            </div>
          </aside>
        )}
        </main>

      <div
        className="relative z-20"
        onMouseEnter={() => {
          if (proof) setConsoleHover(true);
        }}
        onMouseLeave={() => setConsoleHover(false)}
      >
      {proof && !consoleOpen && (
        <button
          className="flex w-full items-center justify-between border-t border-steel bg-raised px-4 py-1 font-mono text-[10px] uppercase tracking-wider text-mute"
          onClick={() => setConsolePinned(true)}
        >
          <span>Hover or click to open console · {me?.display_name ?? "Demo student"} ({me?.user_id ?? "FAVL"})</span>
          <span>Pin</span>
        </button>
      )}
      {proof && consoleOpen && (
      <footer className="tp-glass-strong border-t">
        <div className="border-b border-steel px-4 py-2">
          <div className="mb-1 flex items-center justify-between">
            <label htmlFor="command" className="font-mono text-[10px] uppercase tracking-wider text-mute">
              {tr("cmd.label")} — handler {busy ? "orchestrator" : "idle"} — {status} · {me?.display_name ?? "Demo student"} ({me?.user_id ?? "FAVL"})
            </label>
            <button
              className="font-mono text-[10px] uppercase text-mute"
              onClick={() => setConsolePinned((v) => !v)}
            >
              {consolePinned ? "Auto-hide" : "Pin"}
            </button>
          </div>
          <div className="mt-2 flex gap-2">
            <input
              id="command"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void runCommand();
                }
              }}
              className="flex-1 border border-steel bg-navy px-3 py-2 font-mono text-sm text-ink"
            />
            <button
              className="border border-cyan bg-cyan/10 px-4 py-2 font-mono text-xs uppercase text-cyan disabled:opacity-40"
              onClick={() => void runCommand()}
              disabled={busy || paused}
            >
              {busy ? tr("cmd.running") : tr("cmd.reconcile")}
            </button>
            <button
              className="border border-steel px-3 py-2 font-mono text-xs uppercase text-mute"
              onClick={() => setBusy(false)}
            >
              {tr("cmd.cancel")}
            </button>
          </div>
          {lastResult && proof && (
            <p className="mt-2 font-mono text-[11px] text-mute">
              {lastResult.request_id} · {lastResult.final_status} · approvals {lastResult.approval_state} ·
              uncertainties {lastResult.unresolved_uncertainties.join(", ") || "none"}
            </p>
          )}
        </div>
        <VoiceBridge
          paused={paused}
          botMode={botMode}
          onBotMode={setBotMode}
          modelId={modelId}
          onModelId={setModelId}
          tool={tool}
          onTool={setTool}
          onMood={setBotMood}
          onHandoff={load}
          onOpenView={(panel) => {
            const allowed: ViewId[] = [
              "chat",
              "tower",
              "news",
              "mailbox",
              "workspace",
              "calendar",
              "obligations",
              "timeline",
              "conflicts",
              "sources",
              "workflows",
              "approvals",
              "evidence",
              "impact",
              "settings",
              "help",
            ];
            if (allowed.includes(panel as ViewId)) setView(panel as ViewId);
          }}
        />
      </footer>
      )}
      </div>
      </div>
      <CookieBanner />
    </div>
    </MemberShield>
  );
}

function Tower({
  tower,
  obligations,
  plan,
  runs,
  selectedId,
  onSelect,
  onOpenConflicts,
}: {
  tower: TowerResponse | null;
  obligations: Obligation[];
  plan: Plan | null;
  runs: AgentRun[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onOpenConflicts: () => void;
}) {
  const { tr, uiMode } = useI18n();
  const proof = uiMode === "proof";
  const t = tower?.tower;
  return (
    <div className="space-y-4">
      <section>
        <h2 className="mb-3 text-[13px] font-medium text-mute">{tr("widgets.international")}</h2>
        <LifeWidgets />
      </section>
      <div className="grid grid-cols-4 gap-2 lg:grid-cols-8">
        <Metric label={tr("tower.horizon")} value={`${t?.horizon_days ?? 14}d`} tone="text-ink" />
        <Metric label={tr("tower.verified")} value={t?.verified_obligations ?? 0} tone="text-go" />
        <Metric label={tr("tower.conflicts")} value={t?.open_conflicts ?? 0} tone="text-stop" />
        <Metric label={tr("tower.approvals")} value={t?.pending_approvals ?? 0} tone="text-warn" />
        <Metric label={tr("tower.highRisk")} value={t?.high_risk_obligations ?? 0} tone="text-stop" />
        <Metric
          label={tr("tower.plan")}
          value={t?.plan_feasible == null ? "—" : t.plan_feasible ? tr("tower.feasible") : tr("tower.blocked")}
          tone={t?.plan_feasible ? "text-go" : "text-warn"}
        />
        {proof && (
          <Metric
            label="Grok"
            value={t?.grok_state === "fake" ? tr("hdr.grokSimulated") : (t?.grok_state ?? "—")}
            tone="text-cyan"
          />
        )}
        {proof && <Metric label="Mode" value={t?.mode ?? "DEMO"} tone="text-ink" />}
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel title={tr("tower.timeline")}>
          <TimelineStrip plan={plan} selectedId={selectedId} onSelect={onSelect} />
        </Panel>
        <Panel
          title={tr("tower.attention")}
          action={
            <button className="font-mono text-[10px] text-cyan" onClick={onOpenConflicts}>
              {tr("tower.openConflicts")}
            </button>
          }
        >
          <ul className="space-y-2">
            {(tower?.attention ?? []).length === 0 && (
              <li className="text-sm text-mute">{tr("tower.emptyAttention")}</li>
            )}
            {(tower?.attention ?? []).map((item) => (
              <li key={item.id}>
                <button
                  className="w-full border border-steel px-2 py-2 text-left hover:border-cyan"
                  onClick={() => onSelect(item.object_id)}
                >
                  <div className="flex items-center justify-between">
                    <Badge tone={item.severity === "red" ? "stop" : "warn"}>{item.severity}</Badge>
                    <span className="font-mono text-[10px] text-mute">{item.kind}</span>
                  </div>
                  <div className="mt-1 text-sm">{item.title}</div>
                  <div className="text-xs text-mute">{item.required_decision}</div>
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Obligations">
          <ObligationTable items={obligations} selectedId={selectedId} onSelect={onSelect} compact />
        </Panel>
        <Panel title="Agent operations">
          <AgentStrip runs={runs} />
        </Panel>
      </div>
    </div>
  );
}

function ObligationTable({
  items,
  selectedId,
  onSelect,
  compact = false,
}: {
  items: Obligation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  compact?: boolean;
}) {
  if (!items.length) {
    return <p className="text-sm text-mute">No obligations yet. Run reconcile from the command console.</p>;
  }
  return (
    <table className="w-full text-left text-sm">
      <thead className="font-mono text-[10px] uppercase text-mute">
        <tr>
          <th className="py-1">Title</th>
          <th>Module</th>
          <th>Due</th>
          <th>State</th>
          {!compact && <th>Source</th>}
          <th>Conf</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr
            key={item.obligation_id}
            className={`cursor-pointer border-t border-steel ${
              selectedId === item.obligation_id ? "bg-cyan/10" : ""
            }`}
            onClick={() => onSelect(item.obligation_id)}
          >
            <td className="py-2">{item.title}</td>
            <td className="font-mono text-xs">{item.course_or_context}</td>
            <td className="font-mono text-xs">{fmt(item.due_at)}</td>
            <td>
              <Badge tone={stateTone(item.verification_state)}>{item.verification_state}</Badge>
            </td>
            {!compact && <td className="text-xs text-mute">{item.source_type}</td>}
            <td className="font-mono text-xs">{item.confidence.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Timeline({
  plan,
  selectedId,
  onSelect,
}: {
  plan: Plan | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <Panel title="Plan board">
      <p className="mb-3 text-sm text-mute">{plan?.explanation ?? "Generate a plan to populate the board."}</p>
      {plan && (
        <div className="mb-3 flex gap-2 text-xs">
          <Badge tone={plan.feasible ? "go" : "stop"}>{plan.feasible ? "feasible" : "infeasible"}</Badge>
          <Badge tone={stateTone(plan.risk_level)}>{plan.risk_level}</Badge>
        </div>
      )}
      <TimelineStrip plan={plan} selectedId={selectedId} onSelect={onSelect} />
      {!!plan?.unscheduled.length && (
        <div className="mt-4">
          <h3 className="font-mono text-[11px] uppercase text-warn">Unscheduled</h3>
          <ul className="mt-1 text-sm">
            {plan.unscheduled.map((item) => (
              <li key={item.obligation_id}>
                {item.title} — {item.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}

function TimelineStrip({
  plan,
  selectedId,
  onSelect,
}: {
  plan: Plan | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const { tr } = useI18n();
  const blocks = plan?.blocks ?? [];
  if (!blocks.length) {
    return <p className="text-sm text-mute">{tr("tower.emptyTimeline")}</p>;
  }
  const start = new Date(plan!.horizon_start).getTime();
  const end = new Date(plan!.horizon_end).getTime();
  const span = Math.max(end - start, 1);
  return (
    <div className="tp-grid relative h-56 overflow-hidden border border-steel bg-navy">
      {blocks.map((block) => {
        const left = ((new Date(block.start_at).getTime() - start) / span) * 100;
        const width = Math.max(
          1.2,
          ((new Date(block.end_at).getTime() - new Date(block.start_at).getTime()) / span) * 100,
        );
        const active = block.obligation_id === selectedId;
        const color =
          block.state === "proposed"
            ? "border-dashed border-cyan text-cyan"
            : block.state === "approved"
              ? "border-go bg-go/20"
              : block.kind === "work"
                ? "border-warn bg-warn/10"
                : block.kind === "society"
                  ? "border-wait bg-wait/10"
                  : "border-steel bg-panel";
        return (
          <button
            key={block.id}
            title={`${block.title} ${fmt(block.start_at)}`}
            onClick={() => onSelect(block.obligation_id ?? block.id)}
            className={`absolute h-8 overflow-hidden px-1 text-left font-mono text-[10px] ${color} ${
              active ? "ring-1 ring-cyan" : ""
            }`}
            style={{ left: `${left}%`, width: `${width}%`, top: `${12 + (hash(block.id) % 5) * 36}px` }}
          >
            {block.title}
          </button>
        );
      })}
    </div>
  );
}

function hash(value: string): number {
  return value.split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
}

function Conflicts({
  items,
  selectedId,
  onSelect,
  onResolved,
}: {
  items: ConflictItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onResolved: () => Promise<void>;
}) {
  const item = items.find((c) => c.id === selectedId) ?? items[0];
  if (!item) {
    return <p className="text-sm text-mute">No deadline conflicts.</p>;
  }
  return (
    <div className="space-y-4">
      <h1 className="font-mono text-sm uppercase tracking-[0.2em] text-stop">
        Deadline conflict — human decision required
      </h1>
      <div className="grid gap-3 md:grid-cols-2">
        <ClaimCard label="Source A" claim={item.claim_a} />
        <ClaimCard label="Source B" claim={item.claim_b} />
      </div>
      <p className="text-sm text-mute">{item.recommended_action}</p>
      <div className="flex flex-wrap gap-2">
        <button className="border border-steel px-3 py-1 text-sm" onClick={() => void api.resolve(item.id, "accept_a").then(onResolved)}>
          Accept source A
        </button>
        <button className="border border-steel px-3 py-1 text-sm" onClick={() => void api.resolve(item.id, "accept_b").then(onResolved)}>
          Accept source B
        </button>
        <button className="border border-warn px-3 py-1 text-sm text-warn" onClick={() => void api.resolve(item.id, "keep_unresolved").then(onResolved)}>
          Keep unresolved
        </button>
        <button className="border border-stop px-3 py-1 text-sm text-stop" onClick={() => void api.resolve(item.id, "reject_extraction").then(onResolved)}>
          Reject extraction
        </button>
      </div>
      <Panel
        title="Clarification draft — not sent"
        action={
          <button
            className="font-mono text-[10px] text-cyan"
            onClick={() => void api.draftConflictEmail(item.id).then(onResolved)}
          >
            One-click draft to mailbox
          </button>
        }
      >
        <pre className="whitespace-pre-wrap font-mono text-xs text-mute">{item.clarification_draft}</pre>
      </Panel>
      <ul className="flex gap-2">
        {items.map((c) => (
          <li key={c.id}>
            <button
              className={`border px-2 py-1 font-mono text-[11px] ${selectedId === c.id ? "border-cyan text-cyan" : "border-steel"}`}
              onClick={() => onSelect(c.id)}
            >
              {c.title}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ClaimCard({ label, claim }: { label: string; claim: ConflictItem["claim_a"] }) {
  return (
    <div className="border border-steel bg-panel p-3">
      <div className="font-mono text-[10px] uppercase text-mute">{label}</div>
      <div className="mt-2 font-mono text-lg">{fmt(claim.value === "unspecified" ? null : claim.value)}</div>
      <dl className="mt-2 space-y-1 font-mono text-xs text-mute">
        <div>source {claim.source_type}</div>
        <div>authority {claim.source_authority}</div>
        <div>observed {fmt(claim.observed_at)}</div>
        <div>confidence {claim.confidence.toFixed(2)}</div>
      </dl>
      <p className="mt-2 text-sm">{claim.evidence_excerpt}</p>
    </div>
  );
}

function Sources({ data }: { data: SourcesResponse | null }) {
  if (!data) return <p className="text-sm text-mute">No source data.</p>;
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <Panel title="Live observations" className="md:col-span-2">
        <ul className="space-y-2 text-sm">
          {data.observations.map((o) => (
            <li key={o.id} className="border border-steel p-2">
              <div className="flex gap-2">
                <Badge tone="cyan">{o.source_type}</Badge>
                {o.injection_flagged && <Badge tone="stop">injection ignored</Badge>}
                <span className="font-mono text-[11px] text-mute">{fmt(o.observed_at)}</span>
              </div>
              <div className="mt-1 text-mute">{o.excerpt}</div>
              <div className="font-mono text-[11px] text-mute">{o.source_reference}</div>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}

function Agents({ runs }: { runs: AgentRun[] }) {
  return (
    <div className="space-y-2">
      {!runs.length && <p className="text-sm text-mute">No agent activity yet.</p>}
      {runs.map((run) => (
        <div key={run.id} className="border border-steel bg-panel p-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm uppercase text-cyan">{run.agent}</span>
            <Badge tone={stateTone(run.state)}>{run.state}</Badge>
          </div>
          <p className="mt-1 text-sm">{run.assignment}</p>
          <p className="font-mono text-[11px] text-mute">
            tool {run.tool_name ?? "—"} · {run.duration_ms}ms · {run.output_artifact ?? "—"}
          </p>
          {run.error_or_uncertainty && <p className="text-xs text-warn">{run.error_or_uncertainty}</p>}
        </div>
      ))}
    </div>
  );
}

function AgentStrip({ runs }: { runs: AgentRun[] }) {
  const latest = ["scout", "verifier", "planner", "guardian"].map((name) =>
    [...runs].reverse().find((r) => r.agent === name),
  );
  return (
    <div className="grid grid-cols-2 gap-2">
      {latest.map((run, idx) => (
        <div key={idx} className="border border-steel p-2">
          <div className="font-mono text-[11px] uppercase text-mute">{run?.agent ?? "idle"}</div>
          <Badge tone={stateTone(run?.state ?? "mute")}>{run?.state ?? "queued"}</Badge>
          <div className="mt-1 font-mono text-[11px] text-mute">{run?.tool_name}</div>
        </div>
      ))}
    </div>
  );
}

function Approvals({ items, onChange }: { items: Approval[]; onChange: () => Promise<void> }) {
  if (!items.length) return <p className="text-sm text-mute">No approval requests.</p>;
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <Panel key={item.id} title={`${item.action_type} → ${item.target_system}`}>
          <div className="flex gap-2">
            <Badge tone={stateTone(item.state)}>{item.state}</Badge>
            <span className="font-mono text-[11px] text-mute">expires {fmt(item.expires_at)}</span>
            {item.reversible && <Badge tone="cyan">reversible</Badge>}
          </div>
          <p className="mt-2 text-sm">{item.reason}</p>
          <ul className="mt-2 font-mono text-xs text-mute">
            {(item.diff?.create ?? []).map((row) => (
              <li key={row.id}>
                + {row.title} {fmt(row.start_at)}–{clockFmt(row.end_at)}
              </li>
            ))}
            {item.diff?.message && (
              <li>
                {item.diff.message.subject} → {item.diff.message.to}
              </li>
            )}
          </ul>
          <div className="mt-3 flex gap-2">
            <button className="border border-go px-3 py-1 text-go" onClick={() => void api.approve(item.id).then(onChange)}>
              Approve
            </button>
            <button className="border border-stop px-3 py-1 text-stop" onClick={() => void api.reject(item.id).then(onChange)}>
              Reject
            </button>
            <button className="border border-cyan px-3 py-1 text-cyan" onClick={() => void api.apply(item.id).then(onChange)}>
              Apply
            </button>
            <button className="border border-steel px-3 py-1" onClick={() => void api.rollback(item.id).then(onChange)}>
              Roll back
            </button>
          </div>
        </Panel>
      ))}
    </div>
  );
}

function Evidence({
  audit,
  graph,
  selectedId,
  onSelect,
}: {
  audit: AuditEvent[];
  graph: { nodes: GraphNode[]; edges: GraphEdge[] } | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Evidence ledger">
        <ol className="space-y-2 font-mono text-xs">
          {audit.map((event) => (
            <li key={event.id} className="border-l-2 border-steel pl-2">
              <div className="text-mute">{fmt(event.created_at)}</div>
              <div>
                {event.agent} · {event.event_type} · {event.result}
              </div>
              <div className="text-mute">{event.summary}</div>
            </li>
          ))}
        </ol>
      </Panel>
      <Panel title="Relationship graph">
        <div className="flex flex-wrap gap-2">
          {(graph?.nodes ?? []).slice(0, 40).map((node) => (
            <button
              key={node.id}
              onClick={() => onSelect(node.id)}
              className={`border px-2 py-1 text-[11px] ${
                selectedId === node.id ? "border-cyan text-cyan" : "border-steel text-mute"
              }`}
            >
              {node.kind}:{node.label.slice(0, 28)}
            </button>
          ))}
        </div>
        <p className="mt-3 text-xs text-mute">
          {(graph?.edges ?? []).length} relationships. Table alternative is the ledger on the left.
        </p>
      </Panel>
    </div>
  );
}

function Impact({ data }: { data: ImpactBundle | null }) {
  if (!data) return null;
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Panel title="Demo evidence">
        <p className="mb-2 text-xs text-warn">{String(data.demo.disclaimer)}</p>
        <pre className="font-mono text-xs text-mute">{JSON.stringify(data.demo, null, 2)}</pre>
      </Panel>
      <Panel title="System evaluation">
        <p className="mb-2 text-xs text-warn">{data.system_test.disclaimer}</p>
        <pre className="font-mono text-xs text-mute">{JSON.stringify(data.system_test.rows, null, 2)}</pre>
      </Panel>
      <Panel title="Pilot evidence">
        <p className="mb-2 text-xs text-warn">{data.pilot.disclaimer}</p>
        <pre className="font-mono text-xs text-mute">{JSON.stringify(data.pilot.sessions, null, 2)}</pre>
      </Panel>
    </div>
  );
}

function Settings({
  outage,
  setOutage,
  onReset,
  onMonitor,
}: {
  outage: boolean;
  setOutage: (v: boolean) => void;
  onReset: () => Promise<void>;
  onMonitor: () => Promise<void>;
}) {
  const {
    tr,
    locale,
    setLocale,
    theme,
    setTheme,
    region,
    setRegion,
    timezone,
    setTimezone,
    formality,
    setFormality,
    uiMode,
    setUiMode,
  } = useI18n();
  const pack = packFor(locale);
  const emergency = regionInfo(region).emergency;
  return (
    <Panel title={tr("nav.student.settings")}>
      <div className="space-y-3 text-sm">
        <label className="block">
          {tr("mode.label")}
          <select
            className="ml-2 border border-steel bg-navy px-2 py-1"
            value={uiMode}
            onChange={(e) => setUiMode(e.target.value as typeof uiMode)}
          >
            <option value="student">{tr("mode.student")}</option>
            <option value="proof">{tr("mode.proof")}</option>
          </select>
        </label>
        <label className="block">
          {tr("settings.language")}
          <select
            className="ml-2 border border-steel bg-navy px-2 py-1"
            value={locale}
            onChange={(e) => setLocale(e.target.value as typeof locale)}
          >
            {LOCALES.map((code) => (
              <option key={code} value={code}>
                {LOCALE_LABEL[code]}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          {tr("settings.region")}
          <select
            className="ml-2 border border-steel bg-navy px-2 py-1"
            value={region}
            onChange={(e) => setRegion(e.target.value as typeof region)}
          >
            {REGIONS.map((row) => (
              <option key={row.code} value={row.code}>
                {row.label}
              </option>
            ))}
          </select>
        </label>
        <p className="text-xs text-mute">{tr("settings.regionHint")}</p>
        <label className="block">
          {tr("settings.timezone")}
          <select
            className="ml-2 border border-steel bg-navy px-2 py-1"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
          >
            {TIMEZONES.map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          {tr("settings.formality")}
          <select
            className="ml-2 border border-steel bg-navy px-2 py-1"
            value={formality}
            onChange={(e) => setFormality(e.target.value as typeof formality)}
          >
            <option value="conversational">{tr("settings.formality.conversational")}</option>
            <option value="neutral">{tr("settings.formality.neutral")}</option>
            <option value="formal">{tr("settings.formality.formal")}</option>
          </select>
        </label>
        <p className="text-xs text-mute">
          {tr("settings.maturity")}: {maturityLabel(pack.maturity)} · {pack.bcp47} · {pack.limitations}
        </p>
        <p className="text-xs text-stop">
          {tr("news.crisis")} {emergency}
        </p>
        <label className="block">
          {tr("settings.theme")}
          <select
            className="ml-2 border border-steel bg-navy px-2 py-1"
            value={theme}
            onChange={(e) => setTheme(e.target.value as typeof theme)}
          >
            <option value="dark">{tr("theme.dark")}</option>
            <option value="light">{tr("theme.light")}</option>
            <option value="system">{tr("theme.system")}</option>
          </select>
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={outage} onChange={(e) => setOutage(e.target.checked)} />
          {tr("settings.outage")}
        </label>
        <div className="border border-steel p-3">
          <div className="font-mono text-[11px] uppercase text-mute">Export my data</div>
          <p className="mt-1 text-xs text-mute">Hashed identifiers. No raw mailbox bodies. No portal scrape.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {["json", "csv", "email", "postgres"].map((dest) => (
              <button
                key={dest}
                className="border border-steel px-2 py-1 font-mono text-[10px]"
                onClick={() => void api.exportData(dest)}
              >
                {dest}
              </button>
            ))}
          </div>
          <a className="mt-2 block text-xs text-cyan" href="/sdk">
            Install on this device · SDK · WebXR
          </a>
          <a className="mt-2 block text-xs text-cyan" href="/sdk/termpilot-icon.png" download="TermPilot-G1.png">
            Download G1 robot icon
          </a>
        </div>
        <label className="block text-xs">
          Your OpenRouter key (optional, never stored in Postgres)
          <input
            type="password"
            className="mt-1 w-full border border-steel bg-navy px-2 py-1"
            placeholder="sk-or-…"
            onBlur={(e) => {
              if (e.target.value) window.sessionStorage.setItem("tp-openrouter", e.target.value);
            }}
          />
        </label>
        <button className="border border-cyan px-3 py-1 text-cyan" onClick={() => void onReset()}>
          {tr("settings.reset")}
        </button>
        <button className="ml-2 border border-steel px-3 py-1" onClick={() => void onMonitor()}>
          Monitor
        </button>
        <div className="border border-steel p-3">
          <WidgetEditor />
        </div>
        <p className="text-mute">{tr("settings.disclaimer")}</p>
        <p className="text-mute">
          Consent is scoped to synthetic LMS, forwarded mail, ICS and the demo calendar. No real student
          data is stored. Outbound mail is demo-outbox only after on-screen approval.
        </p>
      </div>
    </Panel>
  );
}

function Inspector({
  obligation,
  conflict,
  blocks,
  attention,
}: {
  obligation: Obligation | null;
  conflict: ConflictItem | null;
  blocks: { id: string; title: string; start_at: string; reason: string; state: string }[];
  attention: AttentionItem[];
}) {
  const object = obligation ?? conflict;
  return (
    <div>
      <h2 className="font-mono text-[11px] uppercase tracking-[0.18em] text-mute">Inspector</h2>
      {!object && (
        <p className="mt-3 text-sm text-mute">
          Select an obligation, conflict or timeline block. {attention.length} attention item(s) open.
        </p>
      )}
      {obligation && (
        <dl className="mt-3 space-y-2 text-sm">
          <dt className="text-mute">What</dt>
          <dd>{obligation.title}</dd>
          <dt className="text-mute">State</dt>
          <dd>
            <Badge tone={stateTone(obligation.verification_state)}>{obligation.verification_state}</Badge>
          </dd>
          <dt className="text-mute">Source</dt>
          <dd className="font-mono text-xs">
            {obligation.source_type} · {obligation.source_authority}
            <div>{obligation.source_reference}</div>
          </dd>
          <dt className="text-mute">Confidence</dt>
          <dd className="font-mono">{obligation.confidence.toFixed(2)}</dd>
          <dt className="text-mute">Due</dt>
          <dd className="font-mono text-xs">{fmt(obligation.due_at)}</dd>
        </dl>
      )}
      {!!blocks.length && (
        <div className="mt-4">
          <h3 className="font-mono text-[11px] uppercase text-mute">Related blocks</h3>
          <ul className="mt-1 space-y-1 text-xs">
            {blocks.map((b) => (
              <li key={b.id}>
                {b.title} · {fmt(b.start_at)} · {b.state}
                <div className="text-mute">{b.reason}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
