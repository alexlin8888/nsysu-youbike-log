// Beat the Bell: the page as an installed app. The page and its small data files come from the network when it
// answers within a few seconds, and from the last copy otherwise, so the app still opens on a weak campus signal or
// with no signal at all (the page then says how old its counts are). Replays, map tiles and the operator's counts
// are left to the network. site/build.py writes this file to docs/sw.js with the version of the page in CACHE.
var CACHE = "btb-aacb1c7261";
var SHELL = ["./", "vendor/leaflet.js", "manifest.webmanifest", "icon.svg", "icon-192.png", "places.json", "outlook.json", "state.json"];
var WAIT = 4000;   // milliseconds to wait for the network before the last copy is used

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf("btb-") === 0 && k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (e) {
  var req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin || /\/replay_[^/]*\.json$/.test(url.pathname) || /\/sw\.js$/.test(url.pathname)) return;
  // every visit opens the same page whatever its query (?from=, ?tab=), and state.json?t=... is one file
  var key = req.mode === "navigate" ? self.registration.scope : url.origin + url.pathname;
  // a copy served instead of the network says so, and the page tells the rider it is showing old counts
  var last = function () {
    return caches.open(CACHE).then(function (c) { return c.match(key); }).then(function (r) {
      if (!r) return r;
      var h = new Headers(r.headers); h.set("X-BTB-Cache", "1");
      return r.blob().then(function (b) { return new Response(b, { status: r.status, statusText: r.statusText, headers: h }); });
    });
  };
  e.respondWith(new Promise(function (resolve) {
    var done = false, finish = function (r) { if (!done && r) { done = true; resolve(r); } };
    var timer = setTimeout(function () { last().then(finish); }, WAIT);
    fetch(req).then(function (res) {
      clearTimeout(timer);
      if (res.ok) { var copy = res.clone(); caches.open(CACHE).then(function (c) { return c.put(key, copy); }).catch(function () {}); }
      finish(res);
    }).catch(function () {
      clearTimeout(timer);
      last().then(function (r) { finish(r || Response.error()); });
    });
  }));
});
