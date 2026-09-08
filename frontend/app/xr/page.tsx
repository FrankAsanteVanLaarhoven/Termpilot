"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { GrokHumanoid } from "@/components/GrokHumanoid";
import { InstallPwa } from "@/components/InstallPwa";
import { MemberShield } from "@/components/MemberShield";
import { readGrokSession } from "@/components/SplashGate";
import { readStudentSession } from "@/lib/api";

export default function XrPage() {
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
            Sign in with a campus account to launch the G1 robot in WebXR on this device.
          </p>
          <Link className="mt-6 inline-block text-sm text-cyan underline" href="/">
            Create an account or sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <MemberShield>
      <div className="tp-xr-page">
        <header className="tp-xr-bar">
          <Link href="/" className="text-sm text-cyan">
            Back to console
          </Link>
          <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-mute">WebXR · G1 robot</span>
        </header>
        <GrokHumanoid variant="stage" mood="idle" expression="welcome" allowXr className="tp-xr-stage" />
        <div className="tp-xr-install">
          <InstallPwa compact />
        </div>
      </div>
    </MemberShield>
  );
}
