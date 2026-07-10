// Minimal Workbox-based service worker: caches the app shell and
// registers the Background Sync listener that api-client.ts triggers.
importScripts("https://storage.googleapis.com/workbox-cdn/releases/7.1.0/workbox-sw.js");

workbox.routing.registerRoute(
  ({ request }) => request.mode === "navigate",
  new workbox.strategies.NetworkFirst({ cacheName: "aeon-shell" })
);

self.addEventListener("sync", (event) => {
  if (event.tag === "aeon-sync-reports") {
    // Actual sync logic runs in the page via lib/offline — this listener
    // just wakes the page/service worker context on reconnect.
    event.waitUntil(self.clients.matchAll().then((clients) => {
      clients.forEach((client) => client.postMessage({ type: "SYNC_REPORTS" }));
    }));
  }
});
