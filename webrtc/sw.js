const VERSION = "tailkey-pwa-v1";
const ROOT = new URL("./", self.location.href);
const FILES = ["index.html", "style.css", "i18n.js", "prototype.css", "mobile.js", "tailcat_transport.js",
  "wasm_exec.js", "main.wasm.gz", "pwa.js", "manifest.webmanifest", "icon.svg", "icon-192.png", "icon-512.png"];
const ASSETS = new Set(FILES.map((name) => new URL(name, ROOT).href));

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(VERSION);
    // Cache only the fixed application files, never invitations or API responses.
    await cache.addAll(FILES.map((name) => new Request(new URL(name, ROOT), {cache:"reload"})));
  })());
});
self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (key.startsWith("tailkey-pwa-") && key !== VERSION) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});
self.addEventListener("fetch", (event) => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== ROOT.origin || url.search) return;
  const isShell = request.mode === "navigate" && (url.pathname === ROOT.pathname || url.href === new URL("index.html", ROOT).href);
  if (!isShell && !ASSETS.has(url.href)) return;
  event.respondWith((async () => {
    const cache = await caches.open(VERSION);
    return await cache.match(isShell ? new URL("index.html", ROOT).href : request) || fetch(request);
  })());
});
