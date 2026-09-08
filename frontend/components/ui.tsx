"use client";

export function Badge({
  tone,
  children,
}: {
  tone: "go" | "warn" | "stop" | "wait" | "cyan" | "mute";
  children: React.ReactNode;
}) {
  const map = {
    go: "text-go border-go/40",
    warn: "text-warn border-warn/40",
    stop: "text-stop border-stop/40",
    wait: "text-wait border-wait/40",
    cyan: "text-cyan border-cyan/40",
    mute: "text-mute border-steel",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${map[tone]}`}
    >
      {children}
    </span>
  );
}

export function stateTone(state: string): "go" | "warn" | "stop" | "wait" | "cyan" | "mute" {
  const value = state.toLowerCase();
  if (["verified", "healthy", "passed", "applied", "approved", "green", "ok"].includes(value)) {
    return "go";
  }
  if (["conflicted", "unavailable", "failed", "blocked", "red", "critical"].includes(value)) {
    return "stop";
  }
  if (["needs_review", "degraded", "pending", "amber", "stale"].includes(value)) {
    return "warn";
  }
  if (["probable", "proposed", "running"].includes(value)) return "wait";
  if (["live", "cyan"].includes(value)) return "cyan";
  return "mute";
}

export function Panel({
  title,
  action,
  children,
  className = "",
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`tp-glass tp-card ${className}`}>
      <header className="mb-3 flex items-start justify-between gap-3">
        <h2 className="tp-card-title">{title}</h2>
        {action}
      </header>
      <div>{children}</div>
    </section>
  );
}

export function WidgetCard({
  title,
  description,
  tint = "blue",
  icon,
  action,
  meta,
  children,
  className = "",
}: {
  title: string;
  description?: string;
  tint?: "blue" | "purple" | "pink" | "orange" | "cyan" | "green" | "slate";
  icon?: React.ReactNode;
  action?: React.ReactNode;
  meta?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`tp-glass tp-card ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div className={`tp-icon-tile ${tint}`}>{icon}</div>
        {action}
      </div>
      <h3 className="tp-card-title mt-3">{title}</h3>
      {description && <p className="tp-card-copy">{description}</p>}
      {children && <div className="mt-3">{children}</div>}
      {meta && <div className="tp-widget-meta">{meta}</div>}
    </section>
  );
}

export function Metric({
  label,
  value,
  tone = "mute",
}: {
  label: string;
  value: string | number;
  tone?: string;
}) {
  return (
    <div className="tp-glass tp-card px-3 py-2">
      <div className="text-[11px] text-mute">{label}</div>
      <div className={`mt-1 text-xl font-semibold tracking-tight ${tone}`}>{value}</div>
    </div>
  );
}

function displayLocale(): string {
  if (typeof document === "undefined") return "en-GB";
  return document.documentElement.lang || "en-GB";
}

export function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(displayLocale(), {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function clockFmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString(displayLocale(), { hour: "2-digit", minute: "2-digit" });
}
