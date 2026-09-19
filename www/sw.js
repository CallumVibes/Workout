/* Offline support. Cache-first for the app's own files. Bump CACHE to ship
   an update.

   spark.js is deliberately NOT precached: it is several megabytes, and most
   people never open the wallet. It is fetched the first time they do, and the
   handler below caches it from then on, so it still works offline afterwards. */
const CACHE = 'groundwork-v8';
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  // never cache relay or signer traffic
  if (url.protocol === 'wss:' || url.protocol === 'ws:') return;

  /* Anything not ours goes straight to the network, untouched. That means
     lightning address lookups and Spark's own servers: a cached invoice or a
     stale balance is worse than no answer at all, and none of it belongs in
     a cache the app controls. */
  if (url.origin !== location.origin) return;

  // the page itself: try the network so updates land, fall back to cache offline
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
        .catch(() => caches.match('./index.html'))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
      if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
      return r;
    }))
  );
});
