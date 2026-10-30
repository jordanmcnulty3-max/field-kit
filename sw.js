/* Field Kit offline cache. Bump VERSION whenever you upload changed files. */
const VERSION = 'fieldkit-v2';
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

  // App files: cache first so it opens instantly offline; refresh in the background when online.
  e.respondWith(caches.open(VERSION).then(async cache => {
    const hit = await cache.match(req, { ignoreSearch: true }) ||
      (req.mode === 'navigate' ? await cache.match('./index.html') : undefined);
    const net = fetch(req).then(res => { if (res.ok) cache.put(req, res.clone()); return res; }).catch(() => hit);
    return hit || net;
  }));
});
