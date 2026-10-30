/* Field Kit offline cache. Bump VERSION whenever you upload changed files. */
const VERSION = 'fieldkit-v5';
const TILES = 'fk-tiles';
const TILE_HOSTS = ['basemap.nationalmap.gov'];
const ASSETS = ['./', './index.html', './manifest.json', './leaflet.js', './leaflet.css',
  './icon-192.png', './icon-512.png', './icon-maskable-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION && k !== TILES).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Map tiles: serve saved tiles first, fall back to the network.
  if (TILE_HOSTS.includes(url.hostname)) {
    e.respondWith(caches.open(TILES).then(async c => {
      const hit = await c.match(req.url, { ignoreVary: true });
      if (hit) return hit;
      try { return await fetch(req); } catch { return new Response('', { status: 504, statusText: 'Offline' }); }
    }));
    return;
  }
  if (url.origin !== location.origin) return;

  // The page itself: try the network briefly so updates arrive on the next open, then fall back to the cache.
  if (req.mode === 'navigate') {
    e.respondWith(caches.open(VERSION).then(async cache => {
      try {
        const res = await fetch(req, { signal: AbortSignal.timeout(3000) });
        if (res.ok) { cache.put('./index.html', res.clone()); return res; }
        // GitHub Pages hiccup (404/5xx): keep the working app rather than showing an error page.
        return (await cache.match('./index.html')) || res;
      } catch {
        return (await cache.match('./index.html')) || (await cache.match('./')) || Response.error();
      }
    }));
    return;
  }

  // Other app files: cache first so it opens instantly offline; refresh in the background when online.
  e.respondWith(caches.open(VERSION).then(async cache => {
    const hit = await cache.match(req, { ignoreSearch: true }) ||
      (req.mode === 'navigate' ? await cache.match('./index.html') : undefined);
    const net = fetch(req).then(res => { if (res.ok) cache.put(req, res.clone()); return res; }).catch(() => hit);
    return hit || net;
  }));
});
