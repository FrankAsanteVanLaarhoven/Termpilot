import type { ViewId } from "@/lib/api";

const ICONS: Record<string, string> = {
  chat: "M4 6h16v10H7l-3 3V6z",
  tower: "M4 20V9l8-5 8 5v11H4zm8-7v7",
  news: "M4 5h12v14H4zM16 8h4v11h-4",
  mailbox: "M3 7h18v12H3zM3 7l9 7 9-7",
  workspace: "M4 10h7v10H4zM13 4h7v16h-7z",
  calendar: "M5 4h14v16H5zM5 9h14M9 4v4M15 4v4",
  obligations: "M8 6h12M8 12h12M8 18h8M4 6h.01M4 12h.01M4 18h.01",
  timeline: "M4 12h16M12 4v16",
  conflicts: "M12 3l9 16H3L12 3zM12 10v4M12 16h.01",
  sources: "M8 6h13M8 12h13M8 18h13M3 6h2M3 12h2M3 18h2",
  workflows: "M4 6h6v6H4zM14 12h6v6h-6zM7 12v3h7",
  agents: "M12 3a4 4 0 110 8 4 4 0 010-8zM5 21a7 7 0 0114 0",
  approvals: "M5 12l4 4 10-10",
  evidence: "M7 4h10l3 4v12H4V8z",
  impact: "M4 18h16M7 18V9m5 9V6m5 12v-7",
  settings: "M12 8a4 4 0 100 8 4 4 0 000-8zM4 12h2M18 12h2M6.5 6.5l1.5 1.5M16 16l1.5 1.5M6.5 17.5L8 16M16 8l1.5-1.5",
  help: "M12 18h.01M9 8a3 3 0 115.2 2.2C13.5 11 12 12 12 14",
};

export function NavGlyph({ id, size = 18 }: { id: ViewId | "help"; size?: number }) {
  const d = ICONS[id] ?? ICONS.tower;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d={d} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
