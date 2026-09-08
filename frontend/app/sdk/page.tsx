"use client";

import Link from "next/link";

export default function SdkPage() {
  return (
    <div className="min-h-screen bg-navy px-4 py-10 text-ink">
      <div className="mx-auto max-w-xl">
        <div className="flex items-center gap-3">
          <img
            src="/icons/icon-192.png"
            alt="TermPilot Grok Bot"
            width={72}
            height={72}
            className="rounded-[18px] border border-steel"
          />
          <div>
            <h1 className="text-2xl font-semibold">TermPilot SDK</h1>
            <p className="text-sm text-mute">Grok Bot · TermPilot. Read-only. No mail send. No calendar write.</p>
          </div>
        </div>
        <p className="mt-4 text-sm text-mute">
          Use this client offline or from your own scripts. It only calls health, tower and the model
          catalog. Assessed work is never completed.
        </p>
        <div className="mt-6 grid gap-3">
          <a
            className="rounded-2xl border border-cyan bg-panel px-4 py-3 text-sm text-cyan"
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
            href="/sdk/termpilot-icon.png"
            download="TermPilot-GrokBot.png"
          >
            Download app icon (desktop / home screen)
          </a>
          <Link className="text-sm text-mute underline" href="/">
            Back to TermPilot
          </Link>
        </div>
        <pre className="mt-6 overflow-auto rounded-2xl border border-steel bg-raised p-3 font-mono text-xs text-mute">{`const tp = new TermPilot("http://127.0.0.1:8000");
await tp.health();
await tp.tower();
await tp.catalog();`}</pre>
      </div>
    </div>
  );
}
