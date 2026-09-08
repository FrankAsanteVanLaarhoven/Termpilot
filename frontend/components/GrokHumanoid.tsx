"use client";

import Image from "next/image";
import { type BotMood } from "@/components/GrokBotMark";
import { useI18n } from "@/components/Providers";
import { G1Humanoid, G1_URDF, type G1Cue, type G1Expression } from "@/lib/g1/G1Humanoid";

export type GrokExpression = G1Expression;
export type GrokCue = G1Cue;
export type { BotMood };
export const URDF_HUMANOID = G1_URDF;

export function GrokHumanoid({
  mood = "idle",
  expression = "idle",
  variant = "stage",
  className = "",
  allowXr = false,
  cue = "idle",
  speaking = false,
  turning = false,
}: {
  mood?: BotMood;
  expression?: GrokExpression;
  variant?: "splash" | "stage" | "compact";
  className?: string;
  allowXr?: boolean;
  cue?: GrokCue;
  speaking?: boolean;
  turning?: boolean;
}) {
  const { tr } = useI18n();
  return (
    <G1Humanoid
      mood={mood}
      expression={expression}
      variant={variant}
      className={className}
      urdfUrl={URDF_HUMANOID}
      allowXr={allowXr}
      cue={cue}
      speaking={speaking}
      turning={turning}
      ariaLabel={`${tr("grokbot.name")} interactive humanoid`}
      loading={
        <Image
          className="tp-bot-reference"
          src="/splash/grokbot-humanoid.png"
          alt=""
          fill
          priority
          sizes="(max-width: 900px) 100vw, 60vw"
          aria-hidden
        />
      }
      fallback={
        <Image
          className="tp-bot-reference"
          src="/splash/grokbot-humanoid.png"
          alt=""
          fill
          priority
          sizes="(max-width: 900px) 100vw, 60vw"
          aria-hidden
        />
      }
    />
  );
}
