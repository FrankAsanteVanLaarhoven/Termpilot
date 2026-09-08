import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "TermPilot powered by Grok Bot",
  description: "No important deadline should become a surprise. Grok Bot runs every TermPilot student tool.",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, title: "TermPilot", statusBarStyle: "black-translucent" },
  robots: { index: false, follow: false, nocache: true, noarchive: true, nosnippet: true },
  referrer: "no-referrer",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#05070a",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />
        <link rel="icon" type="image/png" sizes="192x192" href="/icons/icon-192.png" />
        <link rel="icon" type="image/png" sizes="512x512" href="/icons/icon-512.png" />
        <link rel="icon" type="image/png" sizes="1024x1024" href="/icons/icon-1024.png" />
        <link rel="preload" href="/splash/grokbot-humanoid.png" as="image" />
        <link rel="preload" href="/robot/g1/g1.urdf" as="fetch" crossOrigin="anonymous" />
        <meta name="theme-color" content="#05070a" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-title" content="TermPilot" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <script
          dangerouslySetInnerHTML={{
            __html: `if("serviceWorker" in navigator){navigator.serviceWorker.register("/sw.js").catch(function(){})}`,
          }}
        />
      </head>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
