'use strict';

(function () {
    var DB_NAME = 'floorball-offline';
    var STORE_NAME = 'action-queue';
    var _db = null;

    function openDB() {
        if (_db) return Promise.resolve(_db);
        return new Promise(function (resolve, reject) {
            var req = indexedDB.open(DB_NAME, 1);
            req.onupgradeneeded = function (e) {
                e.target.result.createObjectStore(STORE_NAME, {keyPath: 'id', autoIncrement: true});
            };
            req.onsuccess = function (e) { _db = e.target.result; resolve(_db); };
            req.onerror = function () { reject(req.error); };
        });
    }

    function enqueue(url) {
        return openDB().then(function (db) {
            return new Promise(function (resolve, reject) {
                var tx = db.transaction(STORE_NAME, 'readwrite');
                tx.objectStore(STORE_NAME).add({url: url, timestamp: Date.now()});
                tx.oncomplete = resolve;
                tx.onerror = function () { reject(tx.error); };
            });
        });
    }

    function remove(id) {
        return new Promise(function (resolve, reject) {
            var tx = _db.transaction(STORE_NAME, 'readwrite');
            tx.objectStore(STORE_NAME).delete(id);
            tx.oncomplete = resolve;
            tx.onerror = function () { reject(tx.error); };
        });
    }

    function getAll() {
        return openDB().then(function (db) {
            return new Promise(function (resolve, reject) {
                var items = [];
                var tx = db.transaction(STORE_NAME, 'readonly');
                var req = tx.objectStore(STORE_NAME).openCursor();
                req.onsuccess = function (e) {
                    var cursor = e.target.result;
                    if (cursor) { items.push(cursor.value); cursor.continue(); }
                    else { resolve(items); }
                };
                req.onerror = function () { reject(req.error); };
            });
        });
    }

    function syncQueue() {
        getAll().then(function (items) {
            if (!items.length) return;

            var chain = Promise.resolve();
            var synced = 0;

            items.forEach(function (item) {
                chain = chain.then(function () {
                    return fetch(item.url, {
                        headers: {'X-Requested-With': 'XMLHttpRequest'},
                        credentials: 'same-origin'
                    })
                    .then(function (res) { return res.json(); })
                    .then(function (data) {
                        if (!data.ok) throw new Error('server_error');
                        synced++;
                        return remove(item.id);
                    });
                });
            });

            chain.then(function () {
                if (synced > 0 && window.showToast) {
                    window.showToast(synced + ' offline action' + (synced > 1 ? 's' : '') + ' synced', 'success', 4000);
                }
                if (window.location.pathname.match(/^\/game\/\d+/)) {
                    fetch(window.location.href, {
                        headers: {'X-Requested-With': 'XMLHttpRequest'},
                        credentials: 'same-origin'
                    })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (data.stats && window.updateStatCells) window.updateStatCells(data.stats);
                        if (data.result && window.updateScore) window.updateScore(data.result);
                    })
                    .catch(function () {});
                }
            }).catch(function (err) {
                if (window.showToast) {
                    window.showToast('Sync failed \u2014 will retry on next reconnect', 'danger', 5000);
                }
                console.error('Offline sync error:', err);
            });
        });
    }

    window.offlineQueue = {enqueue: enqueue};

    window.addEventListener('online', syncQueue);
    window.addEventListener('DOMContentLoaded', function () {
        if (navigator.onLine) syncQueue();
    });
})();
