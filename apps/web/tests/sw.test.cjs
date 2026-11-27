// Service Worker der eigenen Web-App (#662, #35): nur die App-Hülle wird zwischengespeichert, fremde Adressen nie. Aufruf: node apps/web/tests/sw.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname, "..", "sw.js"), "utf8");

function load(online){
  const listeners = {}, stores = new Map(), put = [];
  const mk = name => stores.get(name) || stores.set(name, new Map()).get(name);
  const cache = name => ({
    addAll: async urls => { urls.forEach(u => mk(name).set(new URL(u, "https://app.example/web/").href, {url:u, body:"shell:" + u})); },
    match: async req => { const u = typeof req === "string" ? new URL(req, "https://app.example/web/").href : req.url; return mk(name).get(u.split("?")[0]) || mk(name).get(u) || null; },
    put: async (req, res) => { put.push(req.url); mk(name).set(req.url, res); }
  });
  const ctx = {
    self: {location: new URL("https://app.example/web/sw.js"), addEventListener: (t, f) => { listeners[t] = f; }, skipWaiting: async () => {}, clients: {claim: async () => {}}},
    caches: {open: async n => cache(n), keys: async () => [...stores.keys()], delete: async n => stores.delete(n)},
    fetch: async req => { if (!online) throw new TypeError("offline"); return {ok: true, type: "basic", body: "net:" + req.url, clone() { return this; }}; },
    Response: {error: () => ({error: true})}, URL, Promise, Array, Object
  };
  vm.runInNewContext(src, ctx);
  return {listeners, stores, put, ctx};
}
const ev = (url, method = "GET", mode = "cors") => { const e = {request: {url, method, mode}, out: undefined, waits: []}; e.respondWith = p => { e.out = Promise.resolve(p); }; e.waitUntil = p => { e.waits.push(p); }; return e; };

(async () => {
  let t = load(true);
  const ver = /const CACHE = "(gw-web-[0-9a-f]{12})"/.exec(src);
  assert(ver, "Fassung im Speichernamen");

  // Installieren: App-Hülle vollständig im Speicher
  const inst = ev("x"); inst.waitUntil = p => { inst.out = p; }; t.listeners.install(inst); await inst.out;
  const shell = t.stores.get(ver[1]);
  for (const f of ["index.html", "vendor/gw-lite.js", "vendor/icons.css", "vendor/js-yaml.min.js", "manifest.webmanifest", "icons/icon-192.png"])
    assert([...shell.values()].some(v => v.url === f), f + " fehlt in der App-Hülle");

  // Aktivieren: nur alte Speicher dieser App fallen weg, fremde bleiben
  t.stores.set("gw-web-alt", new Map()); t.stores.set("anderes", new Map());
  const act = ev("x"); act.waitUntil = p => { act.out = p; }; t.listeners.activate(act); await act.out;
  assert(!t.stores.has("gw-web-alt")); assert(t.stores.has("anderes")); assert(t.stores.has(ver[1]));

  // Fremde Adresse (GitHub mit Token) und Schreibzugriffe: nie anfassen
  let e = ev("https://api.github.com/repos/o/r/contents/a"); t.listeners.fetch(e); assert.equal(e.out, undefined);
  e = ev("https://app.example/web/index.html", "POST"); t.listeners.fetch(e); assert.equal(e.out, undefined);
  assert.equal(t.put.length, 0);

  // Aus dem Speicher, im Hintergrund aufgefrischt
  e = ev("https://app.example/web/vendor/gw-lite.js"); t.listeners.fetch(e); let r = await e.out;
  assert.equal(r.body, "shell:vendor/gw-lite.js"); await Promise.all(e.waits);

  // Unbekannte Datei: aus dem Netz und danach gemerkt
  e = ev("https://app.example/web/neu.txt"); t.listeners.fetch(e); r = await e.out; assert.equal(r.body, "net:https://app.example/web/neu.txt");
  assert(t.put.includes("https://app.example/web/neu.txt"));

  // Ohne Netz: Seite öffnet aus der App-Hülle, unbekannte Datei gibt einen Fehler
  t = load(false); const i2 = ev("x"); i2.waitUntil = p => { i2.out = p; }; t.listeners.install(i2); await i2.out;
  e = ev("https://app.example/web/?x=1", "GET", "navigate"); t.listeners.fetch(e); r = await e.out; assert.equal(r.body, "shell:./");
  e = ev("https://app.example/web/andere-seite", "GET", "navigate"); t.listeners.fetch(e); r = await e.out; assert.equal(r.body, "shell:index.html");
  e = ev("https://app.example/web/gibt-es-nicht.js"); t.listeners.fetch(e); r = await e.out; assert.equal(r.error, true);
  console.log("sw ok");
})().catch(e => { console.error(e); process.exit(1); });
