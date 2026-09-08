"use client";

import { useEffect, useState } from "react";
import { api, type LlmCatalog, type LlmModel } from "@/lib/api";

const MODE_HINT: Record<string, string> = {
  chat: "Talk. No calendar writes.",
  work: "Deadlines, conflicts, plans.",
  computer: "Connected tools with Guardian.",
};

export function ModelDock({
  mode,
  onMode,
  modelId,
  onModel,
  tool,
  onTool,
}: {
  mode: string;
  onMode: (id: string) => void;
  modelId: string;
  onModel: (id: string) => void;
  tool: string;
  onTool: (id: string) => void;
}) {
  const [catalog, setCatalog] = useState<LlmCatalog | null>(null);
  const [openModels, setOpenModels] = useState(false);
  const [openTools, setOpenTools] = useState(false);

  useEffect(() => {
    void api.llmCatalog().then(setCatalog).catch(() => undefined);
  }, []);

  const current: LlmModel | undefined = catalog?.models.find((row) => row.id === modelId);
  const currentTool = catalog?.tools.find((row) => row.id === tool);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="tp-glass flex rounded-full p-0.5">
        {["chat", "work"].map((id) => (
          <button
            key={id}
            type="button"
            className={`rounded-full px-4 py-1.5 text-sm ${
              mode === id ? "bg-panel text-ink ring-1 ring-cyan" : "text-mute"
            }`}
            onClick={() => onMode(id)}
          >
            {id === "chat" ? "Chat" : "Work"}
          </button>
        ))}
      </div>
      <div className="relative">
        <button
          type="button"
          className="tp-pill"
          onClick={() => {
            setOpenTools((v) => !v);
            setOpenModels(false);
          }}
        >
          {currentTool?.label ?? "Search"} ▾
        </button>
        {openTools && (
          <div className="tp-glass-strong absolute bottom-10 left-0 z-40 w-64 rounded-2xl p-2 shadow-xl">
            {(catalog?.tools ?? []).map((row) => (
              <button
                key={row.id}
                type="button"
                disabled={row.locked}
                className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm ${
                  tool === row.id ? "bg-panel" : ""
                } ${row.locked ? "text-mute opacity-60" : "hover:bg-panel"}`}
                onClick={() => {
                  if (!row.locked) onTool(row.id);
                  setOpenTools(false);
                }}
              >
                <span>
                  {row.label}
                  {row.badge && (
                    <span className="ml-2 rounded-full border border-steel px-1.5 text-[10px]">{row.badge}</span>
                  )}
                </span>
                {row.locked ? <span>🔒</span> : tool === row.id ? <span>✓</span> : null}
              </button>
            ))}
          </div>
        )}
      </div>
      <button
        type="button"
        className={`tp-pill ${mode === "computer" ? "text-cyan" : ""}`}
        onClick={() => onMode("computer")}
      >
        Computer
      </button>
      <div className="relative ml-auto">
        <button
          type="button"
          className="tp-pill"
          onClick={() => {
            setOpenModels((v) => !v);
            setOpenTools(false);
          }}
        >
          {current?.label ?? "Grok 4.6"} ▾
        </button>
        {openModels && (
          <div className="tp-glass-strong absolute bottom-10 right-0 z-40 max-h-80 w-72 overflow-auto rounded-2xl p-2 shadow-xl">
            {(catalog?.models ?? []).map((row) => (
              <button
                key={row.id}
                type="button"
                disabled={row.locked}
                className={`flex w-full items-start justify-between rounded-xl px-3 py-2 text-left text-sm ${
                  modelId === row.id ? "bg-panel" : ""
                } ${row.locked ? "text-mute opacity-50" : "hover:bg-panel"}`}
                onClick={() => {
                  if (!row.locked) onModel(row.id);
                  setOpenModels(false);
                }}
              >
                <span>
                  <span className="block">{row.label}</span>
                  <span className="block text-[11px] text-mute">{row.blurb}</span>
                </span>
                <span className="flex items-center gap-1 text-[10px]">
                  {row.badge && <span className="rounded-full border border-steel px-1.5">{row.badge}</span>}
                  {row.locked ? "🔒" : modelId === row.id ? "✓" : ""}
                </span>
              </button>
            ))}
            <p className="px-3 py-2 text-[10px] text-mute">{catalog?.note}</p>
          </div>
        )}
      </div>
      <span className="w-full font-mono text-[10px] text-mute">{MODE_HINT[mode]}</span>
    </div>
  );
}
