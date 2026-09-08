"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui";
import { LOCALE_LABEL, LOCALES, isLocale } from "@/lib/i18n";
import { useI18n } from "@/components/Providers";
import { ModelDock } from "@/components/ModelDock";

type Turn = {
  id: string;
  language: string;
  source: string;
  transcript: string;
  display_text: string;
  spoken_text: string;
  intent: string;
  facts: Record<string, unknown>;
  requires_on_screen: boolean;
  transcript_confidence: number;
  bot: string;
  audio_retained: boolean;
};

const LANGS = [
  { code: "auto", label: "Auto" },
  ...LOCALES.map((code) => ({ code, label: LOCALE_LABEL[code] })),
];

const SPEECH_LANG: Record<string, string> = {
  en: "en-GB",
  es: "es-ES",
  nl: "nl-NL",
  fr: "fr-FR",
  de: "de-DE",
  it: "it-IT",
  pt: "pt-PT",
  zh: "zh-CN",
  ja: "ja-JP",
  ko: "ko-KR",
  hi: "hi-IN",
  ar: "ar-SA",
  el: "el-GR",
  pl: "pl-PL",
  ro: "ro-RO",
  fil: "fil-PH",
  bn: "bn-IN",
  ur: "ur-PK",
  sw: "sw-KE",
  yo: "yo-NG",
  ha: "ha-NG",
  cs: "cs-CZ",
  da: "da-DK",
  id: "id-ID",
  ms: "ms-MY",
  fa: "fa-IR",
  ru: "ru-RU",
  sv: "sv-SE",
  th: "th-TH",
  tr: "tr-TR",
  vi: "vi-VN",
  mk: "mk-MK",
};

type SpeechRec = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: { results: { [index: number]: { [index: number]: { transcript: string } } } }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

declare global {
  interface Window {
    webkitSpeechRecognition?: new () => SpeechRec;
    SpeechRecognition?: new () => SpeechRec;
  }
}

export function VoiceBridge({
  onHandoff,
  onOpenView,
  onMood,
  paused,
  compact = false,
  botMode = "work",
  onBotMode,
  modelId = "grok-4.6",
  onModelId,
  tool = "search",
  onTool,
}: {
  onHandoff?: () => Promise<void>;
  onOpenView?: (view: string) => void;
  onMood?: (mood: "idle" | "listening" | "processing" | "speaking") => void;
  paused: boolean;
  compact?: boolean;
  botMode?: string;
  onBotMode?: (id: string) => void;
  modelId?: string;
  onModelId?: (id: string) => void;
  tool?: string;
  onTool?: (id: string) => void;
}) {
  const { tr, locale, setLocale } = useI18n();
  const [open, setOpen] = useState(true);
  const [language, setLanguage] = useState<string>(locale);
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [state, setState] = useState<"idle" | "listening" | "processing" | "speaking">("idle");
  const [transcript, setTranscript] = useState("");
  const [confidence, setConfidence] = useState(1);
  const [muted, setMuted] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [captions, setCaptions] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detected, setDetected] = useState("en");
  const recRef = useRef<SpeechRec | null>(null);
  const heardRef = useRef("");

  useEffect(() => {
    onMood?.(state);
  }, [state, onMood]);

  useEffect(() => {
    void api.voiceTurns().then((data) => {
      setTurns(
        data.items.map((item) => ({
          id: item.id,
          language: item.language,
          source: item.source,
          transcript: item.transcript,
          display_text: item.display_text,
          spoken_text: item.display_text,
          intent: item.intent,
          facts: {},
          requires_on_screen: false,
          transcript_confidence: 1,
          bot: "orchestrator",
          audio_retained: item.audio_retained,
        })),
      );
    }).catch(() => undefined);
  }, []);

  function speak(text: string, lang: string) {
    if (muted || typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = speed;
    utterance.lang = SPEECH_LANG[lang] ?? "en-GB";
    utterance.onstart = () => setState("speaking");
    utterance.onend = () => setState("idle");
    window.speechSynthesis.speak(utterance);
  }

  async function submit(text: string, source: "typed" | "voice", conf = 1) {
    const cleaned = text.trim();
    if (!cleaned || paused) return;
    setState("processing");
    setError(null);
    try {
      const result = (await api.voiceTurn(cleaned, language, conf, source)) as Turn;
      setTurns((prev) => [...prev, result]);
      setDetected(result.language);
      if (isLocale(result.language)) setLocale(result.language);
      setTranscript(result.transcript);
      setConfidence(result.transcript_confidence);
      if (captions) {
        speak(result.spoken_text, result.language);
      }
      if (result.facts && result.facts["handoff"] === "orchestrator" && onHandoff) {
        await onHandoff();
      }
      const panel = result.facts?.open_view;
      if (typeof panel === "string" && onOpenView) onOpenView(panel);
      setInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "voice_failed");
    } finally {
      setState("idle");
    }
  }

  function startListen() {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) {
      setError("This browser has no SpeechRecognition. Type instead. xAI STT is used when XAI_API_KEY is set.");
      return;
    }
    const rec = new Ctor();
    rec.lang = SPEECH_LANG[language] ?? "en-GB";
    rec.continuous = false;
    rec.interimResults = true;
    rec.onresult = (event) => {
      const said = event.results[0]?.[0]?.transcript ?? "";
      heardRef.current = said;
      setTranscript(said);
      setInput(said);
    };
    rec.onend = () => {
      setState("idle");
      if (heardRef.current) void submit(heardRef.current, "voice", 0.86);
    };
    recRef.current = rec;
    setState("listening");
    rec.start();
  }

  function stopListen() {
    recRef.current?.stop();
    window.speechSynthesis?.cancel();
    setState("idle");
  }

  return (
    <section className="border-t border-steel bg-raised px-4 py-3" aria-label="TermPilot VoiceBridge">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <button
          className="font-mono text-[11px] uppercase tracking-[0.16em] text-cyan"
          onClick={() => setOpen((v) => !v)}
        >
          {tr("vb.title")} {open ? "▾" : "▸"}
        </button>
        <Badge tone="cyan">{detected}</Badge>
        <Badge tone={state === "idle" ? "mute" : "warn"}>{state}</Badge>
        <span className="font-mono text-[11px] text-mute">
          confidence {confidence.toFixed(2)} · audio not retained
        </span>
        <label className="ml-auto font-mono text-[11px] text-mute">
          {tr("vb.lang")}
          <select
            className="ml-2 border border-steel bg-navy px-2 py-1 text-ink"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            aria-label="VoiceBridge language"
          >
            {LANGS.map((row) => (
              <option key={row.code} value={row.code}>
                {row.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {open && (
        <div className="mb-3 max-h-40 overflow-auto border border-steel bg-navy p-2" aria-live="polite">
          {turns.length === 0 && (
            <p className="text-sm text-mute">
              {tr("vb.empty")}
            </p>
          )}
          {turns.map((turn) => (
            <div key={turn.id} className="mb-2 text-sm">
              <div className="font-mono text-[10px] text-mute">
                you · {turn.language} · {turn.intent}
              </div>
              <div>{turn.transcript}</div>
              <div className="text-cyan">{turn.display_text}</div>
            </div>
          ))}
        </div>
      )}
      {captions && transcript && state !== "idle" && (
        <p className="mb-2 font-mono text-xs text-warn" aria-live="assertive">
          Caption: {transcript}
        </p>
      )}
      {error && (
        <p className="mb-2 text-sm text-stop" role="alert">
          {error}
        </p>
      )}
      {onBotMode && onModelId && onTool && (
        <div className="mb-2">
          <ModelDock
            mode={botMode}
            onMode={onBotMode}
            modelId={modelId}
            onModel={onModelId}
            tool={tool}
            onTool={onTool}
          />
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <input
          id="voicebridge-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit(input, "typed", 1);
            }
          }}
          placeholder={tr("vb.placeholder")}
          className="min-w-[16rem] flex-1 border border-steel bg-navy px-3 py-2 font-mono text-sm text-ink"
          aria-label="TermPilot conversation"
        />
        <button
          className="border border-cyan bg-cyan/10 px-3 py-2 font-mono text-xs uppercase text-cyan disabled:opacity-40"
          onClick={() => void submit(input, "typed", 1)}
          disabled={paused || state === "processing"}
        >
          {tr("vb.ask")}
        </button>
        <button
          className="border border-steel px-3 py-2 font-mono text-xs uppercase text-ink"
          onClick={() => (state === "listening" ? stopListen() : startListen())}
          disabled={paused}
          aria-pressed={state === "listening"}
        >
          {state === "listening" ? tr("vb.stop") : tr("vb.talk")}
        </button>
        <button className="border border-steel px-2 py-2 font-mono text-xs" onClick={() => setMuted((v) => !v)}>
          {muted ? tr("vb.unmute") : tr("vb.mute")}
        </button>
        <button className="border border-steel px-2 py-2 font-mono text-xs" onClick={() => setCaptions((v) => !v)}>
          {captions ? tr("vb.captionsOn") : tr("vb.captionsOff")}
        </button>
        <label className="font-mono text-[11px] text-mute">
          {tr("vb.speed")}
          <input
            type="range"
            min={0.7}
            max={1.4}
            step={0.1}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            className="ml-1 align-middle"
            aria-label="Speech speed"
          />
        </label>
        <button
          className="border border-steel px-2 py-2 font-mono text-xs"
          onClick={() => {
            const last = turns[turns.length - 1];
            if (last) speak(last.spoken_text, last.language);
          }}
        >
          {tr("vb.replay")}
        </button>
        <button
          className="border border-stop/40 px-2 py-2 font-mono text-xs text-stop"
          onClick={() => {
            void api.deleteVoiceTranscripts();
            setTurns([]);
          }}
        >
          {tr("vb.delete")}
        </button>
      </div>
    </section>
  );
}
