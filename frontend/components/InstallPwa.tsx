"use client";

import { useEffect, useState } from "react";

type InstallPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export function InstallPwa({ compact = false }: { compact?: boolean }) {
  const [promptEvent, setPromptEvent] = useState<InstallPrompt | null>(null);
  const [installed, setInstalled] = useState(false);
  const [ios, setIos] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const nav = window.navigator as Navigator & { standalone?: boolean };
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches || Boolean(nav.standalone);
    setInstalled(standalone);
    setIos(/iPad|iPhone|iPod/.test(nav.userAgent));
    const onPrompt = (event: Event) => {
      event.preventDefault();
      setPromptEvent(event as InstallPrompt);
    };
    const onInstalled = () => setInstalled(true);
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  async function install() {
    if (!promptEvent) return;
    setBusy(true);
    try {
      await promptEvent.prompt();
      const choice = await promptEvent.userChoice;
      if (choice.outcome === "accepted") setInstalled(true);
      setPromptEvent(null);
    } finally {
      setBusy(false);
    }
  }

  if (installed) {
    return (
      <p className="tp-install-hint">
        TermPilot is installed on this device. Launch it from the home screen — the G1 robot is the icon.
      </p>
    );
  }

  return (
    <div className={`tp-install ${compact ? "is-compact" : ""}`}>
      <img src="/icons/icon-192.png" alt="" width={compact ? 40 : 72} height={compact ? 40 : 72} />
      {promptEvent ? (
        <button type="button" className="tp-splash-enter" disabled={busy} onClick={() => void install()}>
          {busy ? "Installing…" : "Install on this device"}
        </button>
      ) : ios ? (
        <p className="tp-install-hint">
          On iPhone or iPad: tap Share, then Add to Home Screen. The G1 robot is the icon that launches TermPilot.
        </p>
      ) : (
        <p className="tp-install-hint">
          In Chrome or Edge, use Install app / Add to Home Screen. The G1 robot is the icon that launches TermPilot
          as a local app.
        </p>
      )}
    </div>
  );
}
