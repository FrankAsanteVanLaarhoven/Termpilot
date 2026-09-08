"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function CookieBanner() {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!window.localStorage.getItem("tp-cookies")) setOpen(true);
    void api.cookieBanner().then((d) => setNote(d.note)).catch(() => undefined);
  }, []);

  if (!open) return null;
  return (
    <div className="fixed bottom-16 left-3 right-3 z-50 rounded-2xl border border-steel bg-raised p-3 shadow-xl md:left-auto md:w-[380px]">
      <p className="text-sm">Cookies are necessary for sign-in and approvals. Analytics stay off unless you opt in.</p>
      <p className="mt-1 text-xs text-mute">{note}</p>
      <div className="mt-2 flex gap-2">
        <button
          className="border border-cyan px-3 py-1 text-xs text-cyan"
          onClick={() => {
            void api.saveCookies({ analytics: false, export: false });
            window.localStorage.setItem("tp-cookies", "necessary");
            setOpen(false);
          }}
        >
          Necessary only
        </button>
        <button
          className="border border-steel px-3 py-1 text-xs"
          onClick={() => {
            void api.saveCookies({ analytics: true, export: true });
            window.localStorage.setItem("tp-cookies", "all");
            setOpen(false);
          }}
        >
          Allow export cookies
        </button>
      </div>
    </div>
  );
}
