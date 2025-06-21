
const CACHE_NAME = 'my-pwa-cache-v1';
const urlsToCache = [
  '/',
  '/static/css/main.css',
  '/static/js/app.js',
  // Adicione aqui outros recursos que deseja cachear
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});