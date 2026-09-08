"use client";

import { useState } from "react";
import { api, type ConnectorCard, type Meeting, type WorkspaceBundle } from "@/lib/api";
import { Badge, Panel, clockFmt, fmt, stateTone } from "@/components/ui";
import { useI18n } from "@/components/Providers";

const AUTO_KEY = "tp-auto-connectors";

export function rememberedConnectors(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(AUTO_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export function rememberConnector(id: string, on: boolean): void {
  if (typeof window === "undefined") return;
  const current = new Set(rememberedConnectors());
  if (on) current.add(id);
  else current.delete(id);
  window.localStorage.setItem(AUTO_KEY, JSON.stringify([...current]));
}

const CONNECTOR_GROUPS: { title: string; ids: string[] }[] = [
  { title: "Email", ids: ["src_email", "src_mailbox"] },
  {
    title: "Work & notes",
    ids: ["src_github", "src_jira", "src_notion", "src_slack", "src_teams", "src_discord", "src_gdrive"],
  },
  { title: "Career", ids: ["src_linkedin", "src_orcid", "src_x"] },
  { title: "University", ids: ["src_lms", "src_cal", "src_upload"] },
];

export function ConnectorsPanel({
  items,
  onChange,
}: {
  items: ConnectorCard[];
  onChange: () => Promise<void>;
}) {
  const pending = items.filter((item) => !item.connected).length;
  const { uiMode } = useI18n();
  const proof = uiMode === "proof";
  const [busy, setBusy] = useState<string | null>(null);
  const byId = new Map(items.map((item) => [item.id, item]));

  async function connectOne(id: string, connected: boolean) {
    setBusy(id);
    try {
      if (connected) {
        await api.disconnect(id);
        rememberConnector(id, false);
      } else {
        await api.connect(id);
        rememberConnector(id, true);
      }
      await onChange();
    } finally {
      setBusy(null);
    }
  }

  async function connectEverything() {
    setBusy("all");
    try {
      const result = await api.connectAll();
      result.connected.forEach((row) => rememberConnector(row.id, true));
      await onChange();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="tp-glass tp-card flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-medium">One-click connect</h2>
          <p className="mt-1 text-xs text-mute">
            GitHub, LinkedIn, email, Notion, Slack, Jira and the rest connect in one click. The public demo
            uses labelled fixture adapters. Live OAuth is optional when provider keys are set. Writes still
            need on-screen approval.
          </p>
          <p className="mt-1 font-mono text-[11px] text-mute">
            {items.length - pending}/{items.length} connected
          </p>
        </div>
        <button
          className="rounded-full border border-cyan bg-cyan/10 px-4 py-3 text-xs uppercase tracking-wide text-cyan disabled:opacity-40"
          onClick={() => void connectEverything()}
          disabled={busy !== null || pending === 0}
        >
          {busy === "all" ? "Connecting…" : pending ? `Connect all in one click (${pending})` : "All connected"}
        </button>
      </div>
      {[
        ...CONNECTOR_GROUPS,
        {
          title: "More",
          ids: items
            .map((item) => item.id)
            .filter((id) => !CONNECTOR_GROUPS.some((group) => group.ids.includes(id))),
        },
      ].map((group) => {
        const groupItems = group.ids.map((id) => byId.get(id)).filter((item): item is ConnectorCard => Boolean(item));
        if (!groupItems.length) return null;
        return (
          <div key={group.title} className="space-y-2">
            <h3 className="font-mono text-[11px] uppercase tracking-[0.14em] text-mute">{group.title}</h3>
            <div className="tp-widget-grid">
              {groupItems.map((item) => (
                <Panel
                  key={item.id}
                  title={item.label}
                  action={
                    <button
                      className="tp-pill"
                      disabled={busy !== null}
                      onClick={() => void connectOne(item.id, item.connected)}
                    >
                      {busy === item.id ? "…" : item.connected ? "Disconnect" : "One-click connect"}
                    </button>
                  }
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={item.connected ? "go" : "mute"}>{item.connected ? "connected" : "disconnected"}</Badge>
                    <Badge tone={item.connected ? "go" : stateTone(item.health)}>
                      {item.connected ? "healthy" : item.health}
                    </Badge>
                    <Badge tone="cyan">one-click</Badge>
                    {proof && (
                      <Badge tone={item.oauth_ready ? "cyan" : "mute"}>
                        {item.oauth_ready ? "live oauth ready" : "fixture"}
                      </Badge>
                    )}
                  </div>
                  <p className="mt-2 text-sm text-mute">{item.capability}</p>
                  {proof && (
                    <p className="mt-1 font-mono text-[11px] text-mute">
                      adapter {item.oauth} · last {fmt(item.last_success_at)}
                    </p>
                  )}
                  {item.oauth_ready && item.authorize_url && (
                    <a
                      className="mt-3 inline-flex tp-pill"
                      href={item.authorize_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Optional live OAuth
                    </a>
                  )}
                </Panel>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function QuickCalendar({
  days,
}: {
  days: { date: string; label: string; meetings: Meeting[] }[];
}) {
  return (
    <div className="grid grid-cols-7 gap-2">
      {days.map((day) => (
        <div key={day.date} className="tp-glass tp-card min-h-36 p-2">
          <div className="font-mono text-[10px] uppercase text-mute">{day.label}</div>
          <ul className="mt-2 space-y-2">
            {day.meetings.map((meeting) => (
              <li key={meeting.id} className="text-xs">
                <div>{meeting.title}</div>
                <div className="font-mono text-mute">{clockFmt(meeting.start_at)}</div>
                {meeting.join_url && (
                  <a className="text-cyan underline" href={meeting.join_url} target="_blank" rel="noreferrer">
                    Join
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export function WorkspaceHub({
  data,
  onChange,
}: {
  data: WorkspaceBundle | null;
  onChange: () => Promise<void>;
}) {
  if (!data) return <p className="text-sm text-mute">Loading live workspace…</p>;
  const mailboxOn = data.connectors.find((c) => c.id === "src_mailbox")?.connected;
  const notionOn = data.connectors.find((c) => c.id === "src_notion")?.connected;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="font-mono text-sm uppercase tracking-[0.18em] text-cyan">Live workspace</h1>
        <span className="font-mono text-[11px] text-mute">clock {fmt(data.now)} · live poll</span>
      </div>
      <Panel title="Team meetings">
        <ul className="space-y-2 text-sm">
          {data.meetings
            .filter((m) => m.join_url)
            .map((meeting) => (
              <li key={meeting.id} className="flex items-center justify-between border border-steel px-2 py-2">
                <div>
                  <div>{meeting.title}</div>
                  <div className="font-mono text-[11px] text-mute">{fmt(meeting.start_at)}</div>
                </div>
                <a className="border border-cyan px-2 py-1 font-mono text-xs text-cyan" href={meeting.join_url ?? "#"} target="_blank" rel="noreferrer">
                  Join meeting
                </a>
              </li>
            ))}
        </ul>
      </Panel>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel
          title="Notion notes"
          action={
            <button
              className="font-mono text-[10px] text-cyan disabled:opacity-40"
              disabled={!notionOn}
              onClick={() => void api.organiseNotes().then(onChange)}
            >
              Organise
            </button>
          }
        >
          {!notionOn && <p className="text-sm text-mute">Connect Notion to import notes.</p>}
          <ul className="space-y-2 text-sm">
            {data.notes.map((note) => (
              <li key={note.id} className="border border-steel p-2">
                <div className="flex gap-2">
                  <span>{note.title}</span>
                  {note.organised && <Badge tone="go">filed</Badge>}
                </div>
                <div className="text-xs text-mute">{note.body}</div>
                <div className="font-mono text-[10px] text-mute">{note.tags.join(" · ")}</div>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Demo outbox">
          {!mailboxOn && <p className="text-sm text-mute">Connect the student mailbox to draft mail.</p>}
          <ul className="space-y-2 text-sm">
            {data.messages.map((message) => (
              <li key={message.id} className="border border-steel p-2">
                <div className="flex items-center gap-2">
                  <Badge tone={message.state === "sent" ? "go" : "warn"}>{message.state}</Badge>
                  <span className="font-mono text-[11px]">{message.channel}</span>
                </div>
                <div>
                  {message.subject} → {message.to}
                </div>
                {message.state === "draft" && message.approval_id && (
                  <p className="text-xs text-mute">Approve in Approvals, then send. Nothing leaves TermPilot until then.</p>
                )}
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}

export function WorkflowBoard({
  data,
  onChange,
}: {
  data: WorkspaceBundle | null;
  onChange: () => Promise<void>;
}) {
  if (!data) return null;
  return (
    <div className="space-y-4">
      <p className="text-sm text-mute">
        Grok coordinates specialist bots. External sends still stop at Guardian.
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {data.workflows.map((flow) => (
          <Panel key={flow.name} title={flow.title}>
            <p className="text-sm text-mute">{flow.description}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {flow.graph.map((bot, idx) => (
                <span key={bot + idx} className="font-mono text-[11px] text-cyan">
                  {bot}
                  {idx < flow.graph.length - 1 ? " →" : ""}
                </span>
              ))}
            </div>
            <button
              className="mt-3 border border-cyan px-3 py-1 font-mono text-xs uppercase text-cyan"
              onClick={() => void api.runWorkflow(flow.name).then(onChange)}
            >
              Run workflow
            </button>
          </Panel>
        ))}
      </div>
      <Panel title="Runs">
        <ul className="space-y-2 font-mono text-xs">
          {data.workflow_runs.map((run) => (
            <li key={run.id}>
              {run.name} · {run.state} · {(run.graph ?? []).map((s) => s.bot).join(" → ")}
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
