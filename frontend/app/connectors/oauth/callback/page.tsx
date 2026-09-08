"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function OAuthCallbackPage() {
  const [status, setStatus] = useState("Finishing university sign-in…");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code") ?? "";
    const state = params.get("state") ?? "src_email";
    if (!code) {
      setStatus("No OAuth code was returned. You can close this tab and connect again.");
      return;
    }
    void api
      .oauthComplete(state, code)
      .then(() => {
        setStatus("Connected. You can close this tab and ask Grok Bot to open your mailbox.");
      })
      .catch(() => {
        setStatus("Sign-in finished, but live mail still needs provider secrets on the server.");
      });
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-navy p-8 text-ink">
      <p className="max-w-md text-center text-sm">{status}</p>
    </main>
  );
}
