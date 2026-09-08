"use client";

import { useEffect, useRef, useState } from "react";
import { useI18n } from "@/components/Providers";
import { LOCALE_LABEL, LOCALES } from "@/lib/i18n";
import { DEFAULT_WIDGETS, WIDGET_CATALOG, loadWidgets, saveWidgets, type WidgetId } from "@/lib/widgets";
import type { ViewId } from "@/lib/api";

type HelpId = "feedback" | "faq" | "release" | "community" | "links";

export function AccountMenu({
  name,
  username,
  email,
  onOpen,
  onSignOut,
  onPin,
}: {
  name: string;
  username: string;
  email: string;
  onOpen: (view: ViewId) => void;
  onSignOut: () => void;
  onPin?: () => void;
}) {
  const { tr } = useI18n();
  const [open, setOpen] = useState(false);
  const [help, setHelp] = useState(false);
  const [customize, setCustomize] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDoc(event: MouseEvent) {
      if (!root.current?.contains(event.target as Node)) {
        setOpen(false);
        setHelp(false);
        setCustomize(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <div className="relative" ref={root}>
      <button
        type="button"
        className="tp-nav-item w-[calc(100%-8px)] text-left"
        onClick={() => {
          setOpen((v) => {
            const next = !v;
            if (next) onPin?.();
            return next;
          });
          setHelp(false);
          setCustomize(false);
        }}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-steel text-xs">
          {name.slice(0, 1)}
        </div>
        <div className="min-w-0">
          <div className="truncate text-xs">{name}</div>
          <div className="truncate font-mono text-[10px] text-mute">{username}</div>
        </div>
      </button>
      {open && (
        <div className="absolute bottom-12 left-0 z-40 flex items-end gap-2">
          <div className="tp-glass-strong w-[260px] rounded-2xl p-2 shadow-xl" role="menu">
            <div className="px-3 py-2 font-mono text-[11px] text-mute">{email}</div>
            <MenuRow label={tr("acct.settings")} onClick={() => { onOpen("settings"); setOpen(false); }} />
            <button
              type="button"
              className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm ${help ? "bg-panel" : "hover:bg-panel"}`}
              onClick={() => {
                setHelp((v) => !v);
                setCustomize(false);
              }}
            >
              {tr("acct.help")}
              <span className="text-mute">›</span>
            </button>
            <MenuRow
              label={tr("acct.customize")}
              onClick={() => {
                setCustomize((v) => !v);
                setHelp(false);
              }}
            />
            <MenuRow
              label={tr("acct.upgrade")}
              onClick={() => {
                onOpen("help");
                setOpen(false);
              }}
            />
            <MenuRow
              label={tr("acct.signout")}
              onClick={() => {
                setOpen(false);
                onSignOut();
              }}
            />
          </div>
          {help && (
            <div className="tp-glass-strong w-[220px] rounded-2xl p-2 shadow-xl">
              {(
                [
                  ["feedback", tr("acct.feedback")],
                  ["faq", tr("acct.faq")],
                  ["release", tr("acct.release")],
                  ["community", tr("acct.community")],
                  ["links", tr("acct.links")],
                ] as [HelpId, string][]
              ).map(([id, label]) => (
                <MenuRow
                  key={id}
                  label={label}
                  onClick={() => {
                    onOpen("help");
                    window.sessionStorage.setItem("tp-help-tab", id);
                    setOpen(false);
                  }}
                />
              ))}
            </div>
          )}
          {customize && <WidgetEditor onDone={() => setCustomize(false)} />}
        </div>
      )}
    </div>
  );
}

function MenuRow({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" className="flex w-full rounded-xl px-3 py-2 text-left text-sm hover:bg-panel" onClick={onClick}>
      {label}
    </button>
  );
}

export function WidgetEditor({ onDone }: { onDone?: () => void }) {
  const { tr } = useI18n();
  const [enabled, setEnabled] = useState<WidgetId[]>(DEFAULT_WIDGETS);

  useEffect(() => {
    setEnabled(loadWidgets());
  }, []);

  function toggle(id: WidgetId) {
    const next = enabled.includes(id) ? enabled.filter((item) => item !== id) : [...enabled, id];
    const saved = next.length ? next : DEFAULT_WIDGETS;
    setEnabled(saved);
    saveWidgets(saved);
    window.dispatchEvent(new Event("tp-widgets-changed"));
  }

  return (
    <div className="tp-glass-strong w-[260px] rounded-2xl p-3 shadow-xl">
      <div className="font-mono text-[11px] uppercase text-mute">{tr("acct.customize")}</div>
      <p className="mt-1 text-xs text-mute">{tr("acct.customizeHint")}</p>
      <ul className="mt-2 space-y-1">
        {WIDGET_CATALOG.map((widget) => (
          <li key={widget.id} className="flex items-center justify-between text-sm">
            <span>{tr(widget.key)}</span>
            <button
              type="button"
              className="tp-pill"
              onClick={() => toggle(widget.id)}
            >
              {enabled.includes(widget.id) ? tr("acct.remove") : tr("acct.add")}
            </button>
          </li>
        ))}
      </ul>
      {onDone && (
        <button type="button" className="mt-2 font-mono text-[10px] text-cyan" onClick={onDone}>
          {tr("acct.done")}
        </button>
      )}
    </div>
  );
}

export function HelpView() {
  const { tr } = useI18n();
  const [tab, setTab] = useState<HelpId>("faq");
  useEffect(() => {
    const saved = window.sessionStorage.getItem("tp-help-tab");
    if (saved === "feedback" || saved === "faq" || saved === "release" || saved === "community" || saved === "links") {
      setTab(saved);
    }
  }, []);
  return (
    <div className="grid gap-4 lg:grid-cols-[200px_1fr]">
      <div className="space-y-1">
        {(
          [
            ["faq", tr("acct.faq")],
            ["release", tr("acct.release")],
            ["community", tr("acct.community")],
            ["links", tr("acct.links")],
            ["feedback", tr("acct.feedback")],
          ] as [HelpId, string][]
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`block w-full rounded-xl px-3 py-2 text-left text-sm ${tab === id ? "bg-panel text-cyan" : "text-mute"}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <section className="tp-glass tp-card text-sm">
        {tab === "faq" && (
          <div className="space-y-3">
            <h2 className="text-lg">{tr("acct.faq")}</h2>
            <p>{tr("help.how")}</p>
            <p>TermPilot organises student life from authorised sources. It does not complete assessed work or impersonate you.</p>
            <p>Calendar writes and outbound mail need on-screen approval. Spoken yes is not enough.</p>
            <p>University notices come from the linked university mailbox only. The portal is not scraped.</p>
          </div>
        )}
        {tab === "release" && (
          <div className="space-y-3">
            <h2 className="text-lg">{tr("acct.release")}</h2>
            <p className="font-mono text-xs text-mute">2026-09-05 · demo</p>
            <ul className="list-disc space-y-1 pl-5">
              <li>Newsfeed: live GOV.UK / BBC RSS, mailbox-gated university notices.</li>
              <li>Mailbox desk: P0–P3 hierarchy, alerts, clutter cleanup, demo-outbox send.</li>
              <li>Custom dashboard widgets students can add or remove.</li>
            </ul>
          </div>
        )}
        {tab === "community" && (
          <div className="space-y-3">
            <h2 className="text-lg">{tr("acct.community")}</h2>
            <p>Invite classmates from the inspector. Student-controlled. No cohort scoring.</p>
            <p>Public student discussion: r/UniUK. Official advice: NUS, UKCISA.</p>
          </div>
        )}
        {tab === "links" && (
          <div className="space-y-2">
            <h2 className="text-lg">{tr("acct.links")}</h2>
            {[
              ["NUS", "https://www.nus.org.uk/"],
              ["UKCISA", "https://www.ukcisa.org.uk/"],
              ["Student visa", "https://www.gov.uk/student-visa"],
              ["Student Minds", "https://www.studentminds.org.uk/"],
              ["Samaritans", "https://www.samaritans.org/"],
            ].map(([label, href]) => (
              <a key={href} className="block text-cyan" href={href} target="_blank" rel="noreferrer">
                {label}
              </a>
            ))}
          </div>
        )}
        {tab === "feedback" && (
          <div className="space-y-3">
            <h2 className="text-lg">{tr("acct.feedback")}</h2>
            <p>This is the competition demo. Feedback stays on this device unless you draft mail and approve a send to the demo outbox. No SMTP.</p>
            <p>{tr("acct.upgradeHint")}</p>
          </div>
        )}
      </section>
    </div>
  );
}

export function SignInGate({ onEnter }: { onEnter: () => void }) {
  const { tr } = useI18n();
  return (
    <div className="flex min-h-screen items-center justify-center bg-navy text-ink">
      <div className="w-[360px] rounded-2xl border border-steel bg-raised p-6">
        <div className="text-sm text-mute">{tr("acct.signedOut")}</div>
        <div className="mt-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full border border-steel">F</div>
          <div>
            <div>Demo student</div>
            <div className="font-mono text-[11px] text-mute">TermPilot demo</div>
          </div>
        </div>
        <button
          type="button"
          className="mt-6 w-full border border-cyan px-3 py-2 font-mono text-xs uppercase text-cyan"
          onClick={onEnter}
        >
          {tr("acct.signin")}
        </button>
      </div>
    </div>
  );
}

export function LanguageWidget() {
  const { tr, locale, setLocale } = useI18n();
  return (
    <label className="block text-sm">
      {tr("settings.language")}
      <select
        className="mt-2 block w-full border border-steel bg-navy px-2 py-1"
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
  );
}
