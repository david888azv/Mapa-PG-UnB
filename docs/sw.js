// MAPA-PG Multi — Service Worker
// Estratégia: shell em cache imediato; dados de área em cache sob demanda
// (network-first com fallback para cache, para que atualizações sejam
// refletidas quando online; offline o app continua funcional para áreas
// já visitadas).
const VERSION = 'mapa-pg-v5.2.0';
const SHELL = [
  './',
  './index.html',
  './faixas-if.html',
  './chart.umd.min.js',
  './manifest.json',
  './registry_ies.json',
  './help-doc.html',
  './mudancas-v5.0.0.html',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;          // ignora cross-origin (CDN)
  // Network-first com fallback ao cache (mantém atualizações quando online)
  e.respondWith(
    fetch(e.request)
      .then(resp => {
        if (resp && resp.ok && resp.type === 'basic') {
          const clone = resp.clone();
          caches.open(VERSION).then(c => c.put(e.request, clone));
        }
        return resp;
      })
      .catch(() => caches.match(e.request))
  );
});
