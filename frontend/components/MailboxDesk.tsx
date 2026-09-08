"use client";

import { useEffect, useState } from "react";
import { api, type MailboxDesk as Desk } from "@/lib/api";
import { Badge, Panel, stateTone } from "@/components/ui";
import { useI18n } from "@/components/Providers";
import { MAIL_PRIORITY_KEY } from "@/lib/localeRegistry";

export function MailboxDesk({ onChange }: { onChange: () => Promise<void> }) {
  const { tr, uiMode } = useI18n();
  const proof = uiMode === "proof";
  const [desk, setDesk] = useState<Desk | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  async function pull() {
    try {
      setDesk(await api.mailbox());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "mailbox_unavailable");
    }
  }

  useEffect(() => {
    void pull();
  }, []);

  async function cleanup() {
    setBusy(true);
    try {
      const result = await api.mailboxCleanup();
      setStatus(
        `${tr("mail.cleanup")}: ${result.counts.archived_now} · ${tr("mail.pri.urgent")}/${tr("mail.pri.action")} ${result.counts.kept_p0_p1}`,
      );
      await pull();
    } catch (err) {
      setError(err instanceof Error ? err.message : "cleanup_failed");
    } finally {
      setBusy(false);
    }
  }

  async function draft(id: string) {
    setBusy(true);
    try {
      const result = await api.mailboxDraft(id);
      setStatus(`Draft ${result.message_id} · not sent · approve ${result.approval_id}`);
      await onChange();
      await pull();
    } catch (err) {
      setError(err instanceof Error ? err.message : "draft_failed");
    } finally {
      setBusy(false);
    }
  }

  const inbox = (desk?.items ?? []).filter((item) => item.state === "inbox");
  const archived = (desk?.items ?? []).filter((item) => item.state === "archived");

  return (
    <div className="space-y-4">
      <Panel
        title={tr("mail.title")}
        action={
          <button className="tp-pill disabled:opacity-40" onClick={() => void cleanup()} disabled={busy}>
            {tr("mail.cleanup")}
          </button>
        }
      >
        <p className="text-sm text-mute">{tr("mail.note")}</p>
        <div className="mt-2 flex flex-wrap gap-2 font-mono text-[10px] text-mute">
          <span>{desk?.student_email}</span>
          {proof && <Badge tone="mute">no smtp</Badge>}
          <Badge tone={desk?.can_send ? "go" : "warn"}>{desk?.can_send ? tr("mail.sendReady") : tr("mail.connectSend")}</Badge>
          <span>
            {tr("mail.pri.urgent")} {desk?.counts.p0 ?? 0}
          </span>
          <span>
            {tr("mail.inbox")} {desk?.counts.inbox ?? 0}
          </span>
        </div>
        {status && <p className="mt-2 font-mono text-[11px] text-cyan">{status}</p>}
        {error && (
          <div className="mt-2 text-sm text-stop" role="alert">
            <p>{error}</p>
            <button
              className="mt-2 tp-pill"
              onClick={() =>
                void api
                  .prepare()
                  .then(() => pull())
                  .then(onChange)
              }
            >
              Connect demo mailbox
            </button>
          </div>
        )}
      </Panel>

      {proof && (
      <Panel title={tr("mail.hierarchy")}>
        <ol className="space-y-1 text-xs">
          {(desk?.hierarchy ?? []).map((step) => (
            <li key={step.fn} className="flex gap-2">
              <span className="font-mono text-mute">{step.order}</span>
              <span className="font-mono text-cyan">{step.fn}</span>
              <span className="text-mute">{step.note}</span>
            </li>
          ))}
        </ol>
      </Panel>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={tr("mail.inbox")}>
          <ul className="space-y-2">
            {inbox.map((item) => (
              <li key={item.id} className="tp-glass rounded-2xl px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={item.priority === "p0" ? "stop" : item.priority === "p1" ? "warn" : "mute"}>
                    {tr(MAIL_PRIORITY_KEY[item.priority] ?? "mail.pri.useful")}
                  </Badge>
                  <Badge tone={stateTone(item.category)}>{item.category}</Badge>
                  <span className="font-mono text-[10px] text-mute">{item.from}</span>
                </div>
                <div className="mt-1 text-sm">{item.subject}</div>
                <p className="text-xs text-mute">{item.excerpt}</p>
                {item.priority === "p0" || item.priority === "p1" ? (
                  <button
                    className="mt-2 border border-cyan px-2 py-1 font-mono text-[10px] text-cyan disabled:opacity-40"
                    disabled={busy}
                    onClick={() => void draft(item.id)}
                  >
                    {tr("mail.draft")}
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title={tr("mail.archived")}>
          <ul className="space-y-2 text-sm">
            {archived.length === 0 && <li className="text-mute">{tr("mail.noArchived")}</li>}
            {archived.map((item) => (
              <li key={item.id} className="text-mute">
                {item.subject}
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
