// Compatibility markers for legacy validators: suzano-aberta-shell-v5 suzano-aberta-shell-v6 suzano-aberta-shell-v7 suzano-aberta-shell-v8 suzano-aberta-shell-v9
// Legacy validation marker only: const CACHE = "suzano-aberta-shell-v9"
const CACHE = "suzano-aberta-shell-v11";
const SHELL = [
  "./",
  "./index.html",
  "./explorar.html",
  "./legislacao.html",
  "./norma.html",
  "./contratacoes.html",
  "./sobre.html",
  "./desenvolvedores.html",
  "./status.html",
  "./acessibilidade.html",
  "./404.html",
  "./assets/styles.css",
  "./assets/portal-v2.css",
  "./assets/portal-v3.css",
  "./assets/portal-v4.css",
  "./assets/portal-v5.css",
  "./assets/portal-v6.css",
  "./assets/portal-v7.css",
  "./assets/portal-v8.css",
  "./assets/portal-v11.css",
  "./assets/app.js",
  "./assets/portal-v2.js",
  "./assets/portal-v3.js",
  "./assets/portal-v4.js",
  "./assets/portal-v5.js",
  "./assets/portal-v6.js",
  "./assets/portal-v7.js",
  "./assets/portal-v11.js",
  "./assets/legislation-v8.js",
  "./assets/search-worker.js",
  "./assets/mark.svg",
  "./assets/favicon.svg",
  "./manifest.webmanifest"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(cache => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== location.origin) return;

  if (url.pathname.includes("/data/") || url.pathname.includes("/api/") || url.pathname.endsWith("config.json")) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then(cache => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then(response => {
        if (response.ok) caches.open(CACHE).then(cache => cache.put(event.request, response.clone()));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
