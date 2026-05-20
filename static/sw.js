'use strict';

var SHELL_CACHE = 'app-shell-v1';
var GAME_CACHE = 'game-page-v1';

var SHELL_ASSETS = [
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    '/static/site.webmanifest',
    '/static/android-chrome-192x192.png',
    '/static/favicon-32x32.png'
];

self.addEventListener('install', function (e) {
    e.waitUntil(
        caches.open(SHELL_CACHE)
            .then(function (cache) { return cache.addAll(SHELL_ASSETS); })
            .then(function () { return self.skipWaiting(); })
    );
});

self.addEventListener('activate', function (e) {
    e.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(
                keys
                    .filter(function (k) { return k !== SHELL_CACHE && k !== GAME_CACHE; })
                    .map(function (k) { return caches.delete(k); })
            );
        }).then(function () { return self.clients.claim(); })
    );
});

self.addEventListener('fetch', function (e) {
    var url = new URL(e.request.url);

    // Action + undo endpoints: pass through, never cache
    if (url.pathname.startsWith('/action') || url.pathname.startsWith('/undo')) {
        return;
    }

    // Static assets: cache-first
    if (url.pathname.startsWith('/static/') ||
        SHELL_ASSETS.indexOf(e.request.url) !== -1) {
        e.respondWith(
            caches.match(e.request).then(function (hit) {
                return hit || fetch(e.request);
            })
        );
        return;
    }

    // Game detail pages: network-first, cache on success for offline fallback
    if (url.pathname.match(/^\/game\/\d+/)) {
        e.respondWith(
            fetch(e.request)
                .then(function (res) {
                    var clone = res.clone();
                    caches.open(GAME_CACHE).then(function (c) { c.put(e.request, clone); });
                    return res;
                })
                .catch(function () { return caches.match(e.request); })
        );
        return;
    }

    // Everything else: network-first, no caching
    e.respondWith(
        fetch(e.request).catch(function () { return caches.match(e.request); })
    );
});
