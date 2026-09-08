"use client";

import { useEffect, useMemo, useState } from "react";
import { readStudentSession } from "@/lib/api";
import { ORIGIN_MARK } from "@/lib/origin";

function isEditable(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return target.isContentEditable;
}

export function MemberShield({ children }: { children: React.ReactNode }) {
  const [label, setLabel] = useState("TermPilot member");
  const [hidden, setHidden] = useState(false);
  const tiles = useMemo(() => Array.from({ length: 28 }, (_, i) => i), []);

  useEffect(() => {
    const session = readStudentSession();
    if (session?.email) setLabel(session.email);
    const onVis = () => setHidden(document.visibilityState !== "visible");
    const block = (event: Event) => {
      if (isEditable(event.target)) return;
      event.preventDefault();
    };
    document.addEventListener("visibilitychange", onVis);
    document.addEventListener("contextmenu", block);
    document.addEventListener("copy", block);
    document.addEventListener("cut", block);
    document.addEventListener("dragstart", block);
    onVis();
    return () => {
      document.removeEventListener("visibilitychange", onVis);
      document.removeEventListener("contextmenu", block);
      document.removeEventListener("copy", block);
      document.removeEventListener("cut", block);
      document.removeEventListener("dragstart", block);
    };
  }, []);

  return (
    <div className={`tp-member-shell ${hidden ? "is-hidden" : ""}`}>
      <div className="tp-member-mark" aria-hidden>
        {tiles.map((i) => (
          <span key={i}>
            {label} · {ORIGIN_MARK} · confidential
          </span>
        ))}
      </div>
      {children}
    </div>
  );
}
