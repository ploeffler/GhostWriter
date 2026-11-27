/* Service Worker der eigenen Web-App (#662, #35): die App-Hülle (Seite, Laufzeit, Symbole) läuft auch ohne Netz.
   Alles von anderen Adressen (api.github.com mit dem Token!) geht unberührt ans Netz und wird nie zwischengespeichert.
   Die Fassung (f639e0190dc5) ändert sich mit jedem Bau; ein neuer Stand ersetzt den alten beim nächsten Laden. */
const CACHE = "gw-web-f639e0190dc5";
const SHELL = ["./", "index.html", "manifest.webmanifest", "faehigkeiten.json", "modelle.json", "vendor/gw-lite.js", "vendor/icons.css", "vendor/js-yaml.min.js",
  "icons/icon-192.png", "icons/icon-512.png", "icons/icon-maskable-512.png", "icons/icon-180.png", "icons/icon.svg"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith("gw-web-") && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;       // fremde Adressen und Schreibzugriffe: nie anfassen
  e.respondWith(caches.open(CACHE).then(async c => {
    const hit = await c.match(req, {ignoreSearch:true});
    const net = fetch(req).then(res => { if (res && res.ok && res.type === "basic") c.put(req, res.clone()); return res; }).catch(() => null);
    if (hit){ e.waitUntil(net); return hit; }                                    // aus dem Speicher, im Hintergrund auffrischen
    const res = await net;
    return res || (req.mode === "navigate" ? c.match("index.html") : Response.error());
  }));
});
