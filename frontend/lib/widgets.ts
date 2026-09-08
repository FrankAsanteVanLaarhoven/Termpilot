export const WIDGET_CATALOG = [
  { id: "world_clock", key: "clock.title" },
  { id: "currency", key: "fx.title" },
  { id: "weather", key: "weather.title" },
  { id: "language", key: "widget.language" },
  { id: "news", key: "widget.news" },
  { id: "reminders", key: "widget.reminders" },
  { id: "mailbox_alerts", key: "widget.mail" },
  { id: "wellbeing", key: "widget.wellbeing" },
] as const;

export type WidgetId = (typeof WIDGET_CATALOG)[number]["id"];

export const DEFAULT_WIDGETS: WidgetId[] = ["world_clock", "currency", "weather"];

const KEY = "tp-widgets";

export function loadWidgets(): WidgetId[] {
  if (typeof window === "undefined") return DEFAULT_WIDGETS;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return DEFAULT_WIDGETS;
    const parsed = JSON.parse(raw) as string[];
    const allowed = new Set(WIDGET_CATALOG.map((w) => w.id));
    const next = parsed.filter((id): id is WidgetId => allowed.has(id as WidgetId));
    return next.length ? next : DEFAULT_WIDGETS;
  } catch {
    return DEFAULT_WIDGETS;
  }
}

export function saveWidgets(ids: WidgetId[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(ids));
}
