"use client";

import { useEffect, useState } from "react";
import { api, type FeedItem, type FeedReminder, type MailItem } from "@/lib/api";
import { Badge, WidgetCard } from "@/components/ui";
import { useI18n } from "@/components/Providers";
import { LanguageWidget } from "@/components/AccountMenu";
import { DEFAULT_WIDGETS, loadWidgets, saveWidgets, type WidgetId } from "@/lib/widgets";

type ClockRow = { zone: string; label: string; time: string; date: string };
type Fx = {
  base: string;
  quote: string;
  rate: number | null;
  amount: number;
  converted: number | null;
  as_of: string | null;
  source: string;
  stale: boolean;
};
type DayWx = { date: string; tmax: number; tmin: number; rain: number; code: number; label: string };

export function LifeWidgets() {
  const { tr } = useI18n();
  const [enabled, setEnabled] = useState<WidgetId[]>(DEFAULT_WIDGETS);
  const [clocks, setClocks] = useState<ClockRow[]>([]);
  const [fx, setFx] = useState<Fx | null>(null);
  const [amount, setAmount] = useState(1000);
  const [from, setFrom] = useState("GBP");
  const [to, setTo] = useState("EUR");
  const [weather, setWeather] = useState<{ days: DayWx[]; place: string; source: string } | null>(null);
  const [wxError, setWxError] = useState<string | null>(null);
  const [headlines, setHeadlines] = useState<FeedItem[]>([]);
  const [reminders, setReminders] = useState<FeedReminder[]>([]);
  const [alerts, setAlerts] = useState<MailItem[]>([]);

  useEffect(() => {
    const sync = () => setEnabled(loadWidgets());
    sync();
    window.addEventListener("tp-widgets-changed", sync);
    return () => window.removeEventListener("tp-widgets-changed", sync);
  }, []);

  function remove(id: WidgetId) {
    const next = enabled.filter((item) => item !== id);
    const saved = next.length ? next : enabled;
    setEnabled(saved);
    saveWidgets(saved);
    window.dispatchEvent(new Event("tp-widgets-changed"));
  }

  useEffect(() => {
    void api.worldClock().then((d) => setClocks(d.items)).catch(() => undefined);
    const id = window.setInterval(() => {
      void api.worldClock().then((d) => setClocks(d.items)).catch(() => undefined);
    }, 15000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    void api
      .fx(amount, from, to)
      .then(setFx)
      .catch(() => setFx(null));
  }, [amount, from, to]);

  useEffect(() => {
    void api
      .weather()
      .then((d) => {
        setWeather(d);
        setWxError(null);
      })
      .catch((err: unknown) => setWxError(err instanceof Error ? err.message : "weather_unavailable"));
    void api
      .feeds()
      .then((d) => {
        setHeadlines(d.items.slice(0, 4));
        setReminders(d.reminders.slice(0, 4));
      })
      .catch(() => undefined);
    void api
      .mailbox()
      .then((d) => setAlerts(d.alerts))
      .catch(() => setAlerts([]));
  }, []);

  const codes = ["GBP", "EUR", "USD", "NGN", "INR", "CNY", "JPY", "PHP", "BRL", "PLN"];
  const show = (id: WidgetId) => enabled.includes(id);
  const kill = (id: WidgetId) => (
    <button type="button" className="tp-pill" onClick={() => remove(id)}>
      {tr("acct.remove")}
    </button>
  );

  return (
    <div className="tp-widget-grid">
      {show("world_clock") && (
      <WidgetCard
        title={tr("clock.title")}
        tint="blue"
        icon={<span aria-hidden>◎</span>}
        action={kill("world_clock")}
        meta={<span>{clocks[0]?.time ?? "—"}</span>}
      >
        <ul className="space-y-1 text-xs">
          {clocks.map((row) => (
            <li key={row.zone} className="flex justify-between gap-2">
              <span className="text-mute">{row.label}</span>
              <span>
                {row.time} <span className="text-mute">{row.date}</span>
              </span>
            </li>
          ))}
        </ul>
      </WidgetCard>
      )}
      {show("currency") && (
      <WidgetCard
        title={tr("fx.title")}
        tint="orange"
        icon={<span aria-hidden>£</span>}
        action={kill("currency")}
        meta={<span>{fx?.source ?? "—"}{fx?.stale ? " · stale" : ""}</span>}
      >
        <div className="flex flex-wrap gap-2 text-sm">
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            className="w-24 rounded-xl border border-transparent bg-navy/40 px-2 py-1"
            aria-label={tr("fx.amount")}
          />
          <select value={from} onChange={(e) => setFrom(e.target.value)} className="rounded-xl border border-transparent bg-navy/40 px-2 py-1">
            {codes.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <select value={to} onChange={(e) => setTo(e.target.value)} className="rounded-xl border border-transparent bg-navy/40 px-2 py-1">
            {codes.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
        <p className="mt-3 text-lg font-semibold tracking-tight">
          {fx?.converted == null ? "—" : fx.converted.toFixed(2)} {to}
        </p>
      </WidgetCard>
      )}
      {show("weather") && (
      <WidgetCard
        title={tr("weather.title")}
        description={weather?.place ?? tr("weather.source")}
        tint="cyan"
        icon={<span aria-hidden>☀</span>}
        action={kill("weather")}
        meta={<span>{weather?.source ?? tr("weather.source")}</span>}
      >
        {wxError && <p className="text-sm text-warn">{wxError}</p>}
        <ul className="grid grid-cols-7 gap-1 text-center text-[10px]">
          {(weather?.days ?? []).map((day) => (
            <li key={day.date} className="rounded-xl bg-navy/30 p-1">
              <div>{day.label}</div>
              <div>{Math.round(day.tmax)}°</div>
              <div className="text-mute">{Math.round(day.tmin)}°</div>
              <div className="text-cyan">{day.rain}%</div>
            </li>
          ))}
        </ul>
      </WidgetCard>
      )}
      {show("language") && (
        <WidgetCard title={tr("widget.language")} tint="purple" icon={<span aria-hidden>文</span>} action={kill("language")}>
          <LanguageWidget />
        </WidgetCard>
      )}
      {show("news") && (
        <WidgetCard title={tr("widget.news")} tint="blue" icon={<span aria-hidden>☰</span>} action={kill("news")}>
          <ul className="space-y-1 text-xs">
            {headlines.map((item) => (
              <li key={item.id}>
                <Badge tone="mute">{item.channel}</Badge> {item.title}
              </li>
            ))}
          </ul>
        </WidgetCard>
      )}
      {show("reminders") && (
        <WidgetCard title={tr("widget.reminders")} tint="pink" icon={<span aria-hidden>!</span>} action={kill("reminders")}>
          <ul className="space-y-1 text-xs">
            {reminders.map((row) => (
              <li key={row.id}>
                <Badge tone={row.priority === "asap" ? "stop" : "warn"}>{row.priority}</Badge> {row.title}
              </li>
            ))}
          </ul>
        </WidgetCard>
      )}
      {show("mailbox_alerts") && (
        <WidgetCard title={tr("widget.mail")} tint="pink" icon={<span aria-hidden>✉</span>} action={kill("mailbox_alerts")}>
          {alerts.length === 0 && <p className="text-xs text-mute">{tr("mail.noAlerts")}</p>}
          <ul className="space-y-1 text-xs">
            {alerts.map((item) => (
              <li key={item.id}>
                <Badge tone="stop">{item.priority}</Badge> {item.subject}
              </li>
            ))}
          </ul>
        </WidgetCard>
      )}
      {show("wellbeing") && (
        <WidgetCard title={tr("widget.wellbeing")} description={tr("news.crisis")} tint="green" icon={<span aria-hidden>+</span>} action={kill("wellbeing")}>
          <a className="mt-2 block text-sm text-cyan" href="https://www.studentminds.org.uk/" target="_blank" rel="noreferrer">
            Student Minds
          </a>
        </WidgetCard>
      )}
    </div>
  );
}
