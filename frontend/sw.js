// Minimal service worker: just enough to make Trankr installable as a PWA.
// It caches the app shell (HTML/icons) so the interface loads instantly;
// it does NOT cache API calls, so your data is always fetched fresh.
const CACHE = "trankr-shell-v1";
const SHELL_FILES = ["/", "/manifest.json", "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL_FILES))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Never intercept API calls — always go to network for live data.
  if (url.pathname.startsWith("/auth") || url.pathname.startsWith("/goals") ||
      url.pathname.startsWith("/tasks") || url.pathname.startsWith("/habits")) {
    return;
  }
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
