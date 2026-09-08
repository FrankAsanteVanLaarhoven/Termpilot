"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { InstallPwa } from "@/components/InstallPwa";
import { readGrokSession } from "@/components/SplashGate";
import { readStudentSession } from "@/lib/api";

export default function SdkPage() {
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    setAllowed(Boolean(readGrokSession() && readStudentSession()));
  }, []);

  if (allowed === null) {
    return <div className="min-h-screen bg-navy" aria-hidden />;
  }

  if (!allowed) {
    return (
      <div className="min-h-screen bg-navy px-4 py-10 text-ink">
        <div className="mx-auto max-w-xl">
          <h1 className="text-2xl font-semibold">Members only</h1>
          <p className="mt-3 text-sm text-mute">
            Sign in with a campus account to install TermPilot on this device, download the SDK, and launch the G1
            robot.
          </p>
          <Link className="mt-6 inline-block text-sm text-cyan underline" href="/">
            Create an account or sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-navy px-4 py-10 text-ink">
      <div className="mx-auto max-w-xl">
        <div className="flex items-center gap-3">
          <img
            src="/icons/icon-192.png"
            alt="TermPilot G1 robot"
            width={72}
            height={72}
            className="rounded-[18px] border border-steel"
          />
          <div>
            <h1 className="text-2xl font-semibold">TermPilot on this device</h1>
            <p className="text-sm text-mute">PWA · WebXR · read-only SDK. The G1 robot is the install and launch icon.</p>
          </div>
        </div>
        <p className="mt-4 text-sm text-mute">
          Install TermPilot as a local app. The home-screen icon is our G1 robot. Launch it offline for the shell, or
          open WebXR to stand the same robot in VR or AR. The JavaScript and Python clients only call health, tower
          and the model catalog. Assessed work is never completed. Mail and calendar still need on-screen approval.
        </p>
        <div className="mt-6">
          <InstallPwa />
        </div>
        <div className="mt-6 grid gap-3">
          <Link className="rounded-2xl border border-cyan bg-panel px-4 py-3 text-sm text-cyan" href="/xr">
            Launch G1 robot in WebXR
          </Link>
          <a
            className="rounded-2xl border border-steel bg-panel px-4 py-3 text-sm"
            href="/sdk/termpilot-icon.png"
            download="TermPilot-G1.png"
          >
            Download G1 robot icon (home screen / desktop)
          </a>
          <a
            className="rounded-2xl border border-steel bg-panel px-4 py-3 text-sm"
            href="/sdk/termpilot.js"
            download
          >
            Download JavaScript SDK
          </a>
          <a
            className="rounded-2xl border border-steel bg-panel px-4 py-3 text-sm"
            href="/sdk/termpilot.py"
            download
          >
            Download Python SDK
          </a>
          <a
            className="rounded-2xl border border-steel bg-panel px-4 py-3 text-sm"
            href="/sdk/g1-humanoid.zip"
            download="TermPilot-G1-humanoid.zip"
          >
            Download G1 humanoid pack (URDF + controller)
          </a>
          <Link className="text-sm text-mute underline" href="/">
            Back to TermPilot
          </Link>
        </div>
        <pre className="mt-6 overflow-auto rounded-2xl border border-steel bg-raised p-3 font-mono text-xs text-mute">{`const tp = new TermPilot("/api");
await tp.health();
await tp.tower();
await tp.catalog();
// Install uses /manifest.json. The launch icon is /sdk/termpilot-icon.png (G1).
// Open /xr on this device for VR / AR.`}</pre>
      </div>
    </div>
  );
}
