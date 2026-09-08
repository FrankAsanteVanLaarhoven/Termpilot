"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type FeedItem, type FeedLink, type FeedReminder, type FeedsResponse } from "@/lib/api";
import { Badge, Panel, stateTone } from "@/components/ui";
import { useI18n } from "@/components/Providers";
import { regionInfo } from "@/lib/localeRegistry";

const FILTERS: { id: string; key: string }[] = [
  { id: "all", key: "news.filter.all" },
  { id: "university", key: "news.filter.university" },
  { id: "government", key: "news.filter.government" },
  { id: "school", key: "news.filter.school" },
  { id: "international", key: "news.filter.international" },
  { id: "community", key: "news.filter.community" },
  { id: "career", key: "news.filter.career" },
  { id: "reddit", key: "news.filter.reddit" },
];

const DIRECTORY_GROUPS: { id: string; key: string }[] = [
  { id: "student_union", key: "news.dir.union" },
  { id: "career", key: "news.dir.career" },
  { id: "wellbeing", key: "news.dir.wellbeing" },
  { id: "student_support", key: "news.dir.support" },
  { id: "international", key: "news.dir.international" },
  { id: "community", key: "news.dir.community" },
];

function matchesFilter(item: FeedItem, filter: string): boolean {
  if (filter === "all") return true;
  if (filter === "reddit") return item.source_kind === "reddit" || item.source_label.toLowerCase().includes("reddit");
  if (filter === "career") return item.channel === "career";
  return item.channel === filter;
}

function ItemCard({ item }: { item: FeedItem }) {
  const { tr, uiMode } = useI18n();
  const community = item.source_kind === "reddit" || item.channel === "community";
  return (
    <article className="tp-glass tp-card">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={item.priority === "asap" ? "stop" : stateTone(item.channel)}>{item.channel}</Badge>
        {community && <Badge tone="warn">{tr("news.communitySource")}</Badge>}
        {item.stale && uiMode === "proof" && <Badge tone="warn">stale</Badge>}
        {item.priority === "asap" && <Badge tone="stop">{tr("news.asap")}</Badge>}
        <span className="font-mono text-[10px] text-mute">{item.source_label}</span>
      </div>
      <h3 className="mt-1 text-sm font-medium">{item.title}</h3>
      {item.summary && <p className="mt-1 text-xs text-mute">{item.summary}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-3 font-mono text-[10px] text-mute">
        {item.published && <span>{item.published.replace("T", " ").slice(0, 16)}</span>}
        {item.from && <span>{item.from}</span>}
        {item.url ? (
          <a className="text-cyan" href={item.url} target="_blank" rel="noreferrer">
            Open source
          </a>
        ) : (
          <span>Mailbox notice · no portal scrape</span>
        )}
      </div>
    </article>
  );
}

function DirectoryCard({ link }: { link: FeedLink }) {
  return (
    <a
      href={link.url}
      target="_blank"
      rel="noreferrer"
      className="tp-glass tp-card block hover:border-cyan"
    >
      <div className="text-sm">{link.title}</div>
      <p className="mt-1 text-xs text-mute">{link.note}</p>
    </a>
  );
}

export function NewsFeed() {
  const { tr, uiMode, region } = useI18n();
  const emergency = regionInfo(region).emergency;
  const [data, setData] = useState<FeedsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState(false);

  async function pull() {
    setBusy(true);
    try {
      const payload = await api.feeds();
      setData(payload);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "feeds_unavailable");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void pull();
  }, []);

  const items = useMemo(() => (data?.items ?? []).filter((item) => matchesFilter(item, filter)), [data, filter]);
  const reminders: FeedReminder[] = data?.reminders ?? [];

  return (
    <div className="space-y-4">
      <Panel
        title={tr("news.title")}
        action={
          <button className="font-mono text-[10px] uppercase text-cyan" onClick={() => void pull()} disabled={busy}>
            {busy ? tr("common.loading") : tr("news.refresh")}
          </button>
        }
      >
        <p className="text-sm text-mute">{tr("news.role")}</p>
        <p className="mt-2 text-xs text-stop">
          {tr("news.crisis")} {emergency}
        </p>
        {uiMode === "proof" && data?.role_note && (
          <p className="mt-2 font-mono text-[11px] text-mute">{data.role_note}</p>
        )}
        <div className="mt-3 flex flex-wrap gap-2 font-mono text-[10px] text-mute">
          {uiMode === "proof" && (
            <Badge tone={data?.stale ? "warn" : "cyan"}>{data?.stale ? "fixture" : "live rss"}</Badge>
          )}
          <span>sources {data?.pulled.live_sources ?? 0}</span>
          <span>{data?.university_authorised ? tr("news.uniOn") : tr("news.uniOff")}</span>
        </div>
        {data?.university_lock && (
          <p className="mt-2 border border-warn/40 bg-navy px-3 py-2 text-xs text-warn" role="status">
            {data.university_lock}
          </p>
        )}
      </Panel>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((chip) => (
          <button
            key={chip.id}
            className={`border px-2 py-1 font-mono text-[11px] ${
              filter === chip.id ? "border-cyan text-cyan" : "border-steel text-mute"
            }`}
            onClick={() => setFilter(chip.id)}
          >
            {tr(chip.key)}
          </button>
        ))}
      </div>

      {error && (
        <div className="border border-stop/50 px-3 py-2 text-sm text-stop" role="alert">
          {error}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-2">
          {items.length === 0 && <p className="text-sm text-mute">{tr("news.empty")}</p>}
          {items.map((item) => (
            <ItemCard key={item.id} item={item} />
          ))}
        </div>
        <div className="space-y-4">
          <Panel title={tr("news.reminders")}>
            <ul className="space-y-2">
              {reminders.length === 0 && <li className="text-xs text-mute">{tr("news.noReminders")}</li>}
              {reminders.map((row) => (
                <li key={row.id} className="text-sm">
                  <Badge tone={row.priority === "asap" ? "stop" : "warn"}>{row.priority}</Badge>{" "}
                  {row.title}
                  <div className="font-mono text-[10px] text-mute">
                    {row.source_label}
                    {row.due_at ? ` · ${row.due_at.replace("T", " ").slice(0, 16)}` : ""}
                  </div>
                </li>
              ))}
            </ul>
          </Panel>
          {DIRECTORY_GROUPS.map((group) => (
            <Panel key={group.id} title={tr(group.key)}>
              <div className="space-y-2">
                {(data?.directory ?? [])
                  .filter((link) => link.group === group.id)
                  .map((link) => (
                    <DirectoryCard key={link.id} link={link} />
                  ))}
              </div>
            </Panel>
          ))}
        </div>
      </div>
    </div>
  );
}
