"use client";

import { useId } from "react";
import { useI18n } from "@/components/Providers";

export type BotMood = "idle" | "listening" | "processing" | "speaking";

export function GrokBotMark({
  size = 36,
  title = "Grok Bot",
  mood = "idle",
  className = "",
}: {
  size?: number;
  title?: string;
  mood?: BotMood;
  className?: string;
}) {
  const gid = useId().replace(/:/g, "");
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label={title}
      className={`tp-mark shrink-0 mood-${mood} ${className}`.trim()}
    >
      <defs>
        <radialGradient id={`shell-${gid}`} cx="34%" cy="28%">
          <stop offset="0%" stopColor="#3a3a3a" />
          <stop offset="55%" stopColor="#161616" />
          <stop offset="100%" stopColor="#050505" />
        </radialGradient>
        <radialGradient id={`glow-${gid}`} cx="50%" cy="50%">
          <stop offset="0%" stopColor="#3ad0ff" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#3ad0ff" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle className="tp-mark-aura" cx="32" cy="32" r="31" fill={`url(#glow-${gid})`} />
      <circle className="tp-mark-ring" cx="32" cy="32" r="30.2" fill="none" stroke="#3ad0ff" strokeWidth="0.9" />
      <circle className="tp-mark-shell" cx="32" cy="32" r="29.2" fill={`url(#shell-${gid})`} />
      <ellipse className="tp-mark-shine" cx="22" cy="18" rx="11" ry="7" fill="#ffffff" />
      <g className="tp-mark-eyes">
        <g transform="rotate(-22 26.5 25)">
          <ellipse className="tp-mark-eye" cx="26.5" cy="25" rx="5.2" ry="8.4" fill="#f5f5f5" />
        </g>
        <g transform="rotate(-22 39.5 25)">
          <ellipse className="tp-mark-eye right" cx="39.5" cy="25" rx="5.2" ry="8.4" fill="#f5f5f5" />
        </g>
      </g>
    </svg>
  );
}

export function TermPilotLogo({
  size = 36,
  powered = true,
  compact = false,
  mood = "idle",
  className = "",
  onClick,
}: {
  size?: number;
  powered?: boolean;
  compact?: boolean;
  mood?: BotMood;
  className?: string;
  onClick?: () => void;
}) {
  const { tr } = useI18n();
  const body = (
    <>
      <GrokBotMark size={size} mood={mood} title={tr("grokbot.name")} />
      <div className="tp-logo-copy">
        <div className="tp-logo-word">{tr("splash.product")}</div>
        {powered && (
          <div className="tp-logo-by">
            {tr("splash.powered")} <strong>{tr("splash.engine")}</strong>
          </div>
        )}
      </div>
    </>
  );
  const cls = `tp-logo ${compact ? "compact" : ""} ${className}`.trim();
  if (onClick) {
    return (
      <button type="button" className={cls} onClick={onClick} aria-label={tr("hdr.home")}>
        {body}
      </button>
    );
  }
  return <div className={cls}>{body}</div>;
}
