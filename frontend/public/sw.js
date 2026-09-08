const CACHE = "termpilot-shell-v3";
const SHELL = [
  "/",
  "/xr",
  "/sdk",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-512-maskable.png",
  "/icons/icon-1024.png",
  "/icons/apple-touch-icon.png",
  "/icons/termpilot-grokbot.png",
  "/splash/grokbot-humanoid.png",
  "/sdk/termpilot-icon.png",
  "/sdk/termpilot.js",
  "/sdk/termpilot.py",
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)).catch(() => undefined));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api") || url.pathname.startsWith("/export") || url.pathname.includes("mailbox")) return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request).then((hit) => hit || caches.match("/"))),
  );
});
