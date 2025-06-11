// service-worker.js

const CACHE_NAME = 'static-v1';
const URLS_TO_CACHE = [
  '/',                // adjust to your root or index.html
  '/haberler.html',
  // add your CSS/JS/assets here
];

// 1. Install: pre-cache your shell
self.addEventListener('install', event => {
  self.skipWaiting(); // <-- activate immediately
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(URLS_TO_CACHE))
  );
});

// 2. Activate: claim clients so this SW takes over all pages
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    )
    .then(() => self.clients.claim()) // <-- take control immediately
  );
});

// 3. Fetch: network-first for your HTML, cache-first for everything else
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Network-first for your HTML shell
  if (url.pathname.endsWith('haberler.html') || url.pathname === '/') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // optionally update cache
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Cache-first for other requests (CSS/JS/images/etc)
  event.respondWith(
    caches.match(event.request).then(cached => 
      cached ||
      fetch(event.request).then(response => {
        // optionally cache new resources on the fly
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        return response;
      })
    )
  );
});
