// Fehler melden ohne Chat und Fähigkeiten-Matrix der Web-App (#662): bereinigt, ohne Repository-, Buch- und Textnamen; Matrix gegen Messwerte. Aufruf: node apps/web/tests/fehler.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const read = f => fs.readFileSync(path.join(__dirname, "..", f), "utf8");

function load(extra){
  const mem = {}, listeners = {}, opened = [];
  const ctx = Object.assign({
    S: {owner:"geheimerowner", repo:"mein-privates-buch", view:"section", lib:{books:[{branch:"buch/barawitzkas-neffe", work_branch:"ghostwriter/buch/barawitzkas-neffe", title:"Barawitzkas Neffe", title_short:"Neffe"}], program:{upstream:"ploeffler/GhostWriter:main"}}},
    store: {get: k => mem[k] === undefined ? null : mem[k], set: (k, v) => { mem[k] = v; }}, esc: s => String(s), $: () => null,
    navigator: {userAgent:"Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"},
    window: {addEventListener: (t, f) => { listeners[t] = f; }, open: (u) => opened.push(u)}, document: {addEventListener: () => {}}, location: {origin:"https://x.github.io"},
    Date, JSON, Array, Set, Object, String, Math, Number, Promise, encodeURIComponent, setTimeout, clearTimeout, GW_PORTS: {}
  }, extra || {});
  vm.runInNewContext(read("fehler-web.js") + "\n;this.__x = {errSanitize, errEndpoint, errLog, errList, errIssueUrl, errClass, errBrowser, errUpstream, errHash, errButton};", ctx);
  return {ctx, x: ctx.__x, mem, opened, listeners};
}

(async () => {
  const t = load(), X = t.x;
  // Bereinigen: Namen, Pfade, Titel in Anführungszeichen, Token, Adressen, E-Mail
  const dirty = 'Fehler in geheimerowner/mein-privates-buch auf buch/barawitzkas-neffe: Datei chapters/02-der-blick/sections/05-die-maske.md fehlt, Abschnitt 2.5 „Die Maske, besonders bei Frauen“, Token github_pat_ABC123xyz, mail a.b@example.org, https://github.com/x/y?z=1 und Neffe';
  const clean = X.errSanitize(dirty);
  for (const bad of ["geheimerowner", "mein-privates-buch", "barawitzkas", "chapters", "05-die-maske", "Maske, besonders", "github_pat_", "a.b@example.org", "github.com/x/y", "Neffe"])
    assert(!clean.includes(bad), bad + " ist noch in: " + clean);
  assert.match(clean, /<token>/); assert.match(clean, /<pfad>/); assert.match(clean, /„…“/);
  assert(X.errSanitize("x".repeat(500)).length <= 240);
  // Aufruf ohne Repository, Pfade und Kennungen
  assert.equal(X.errEndpoint("PUT", "/repos/geheimerowner/mein-privates-buch/pulls/17/merge"), "PUT /repos/{o}/{r}/pulls/{n}/merge");
  assert.equal(X.errEndpoint("GET", "/repos/o/r/contents/chapters/01/a.md?ref=buch%2Fx"), "GET /repos/o/r".replace("/repos/o/r", "/repos/{o}/{r}") + "/contents/{pfad}");
  assert.equal(X.errEndpoint("PATCH", "/repos/o/r/git/refs/heads/ghostwriter/buch/x"), "PATCH /repos/{o}/{r}/git/refs/heads/{zweig}");
  assert.equal(X.errEndpoint("GET", "/repos/o/r/git/commits/0123456789abcdef0123456789abcdef01234567"), "GET /repos/{o}/{r}/git/commits/{sha}");
  // Klassen
  assert.equal(X.errClass({code:"offline"}), "netz"); assert.equal(X.errClass({code:"http_403"}), "rechte"); assert.equal(X.errClass({code:"server_unavailable"}), "github-server");
  assert.equal(X.errClass({message:"x"}), "app-fehler"); assert.equal(X.errClass({message:"x"}, "js-fehler"), "js-fehler");
  assert.equal(X.errBrowser(), "Chrome 131 · Android");
  // Protokoll: gleiche Fehler zusammengefasst (Zähler), Fingerabdruck stabil, höchstens 30
  const r1 = X.errLog({code:"http_422", status:422, endpoint:"PUT /repos/{o}/{r}/pulls/{n}/merge", message:"Merge nicht möglich in geheimerowner/mein-privates-buch"});
  const r2 = X.errLog({code:"http_422", status:422, endpoint:"PUT /repos/{o}/{r}/pulls/{n}/merge", message:"Merge nicht möglich in geheimerowner/mein-privates-buch"});
  assert.equal(r1.fp, r2.fp); assert.equal(r2.n, 2); assert.equal(X.errList().length, 1); assert.match(r1.fp, /^[0-9a-f]{12}$/);
  assert(!JSON.stringify(X.errList()).includes("geheimerowner"));
  for (let i = 0; i < 40; i++) X.errLog({message:"Fehler Nummer " + i + " anders" + "x".repeat(i)});
  assert(X.errList().length <= 30);
  // Meldung: Hauptrepository aus der Bibliothek, Format nach #660, nichts Persönliches
  const url = new URL(X.errIssueUrl(r2)), body = url.searchParams.get("body");
  assert.equal(url.origin + url.pathname, "https://github.com/ploeffler/GhostWriter/issues/new"); assert.equal(url.searchParams.get("labels"), "bug");
  assert.match(url.searchParams.get("title"), /^\[Web-App\] github-abgelehnt: /);
  for (const k of ["**Fehlerklasse:** github-abgelehnt", "**Programm:** GhostWriter Web-App", "**Schritt:** section", "**Aufruf:** `PUT /repos/{o}/{r}/pulls/{n}/merge` → 422", "**Browser:** Chrome 131 · Android", "**Fingerabdruck:** `" + r2.fp, "**Häufigkeit:** 2×"]) assert(body.includes(k), k);
  for (const bad of ["geheimerowner", "mein-privates-buch", "barawitzkas", "Neffe"]) assert(!body.includes(bad) && !url.href.includes(bad), bad);
  assert(!body.includes("Gerät (grob"), "Gerätewerte nur auf Wunsch");
  // Ohne Bibliothek (oder bei ungültigem Eintrag) gilt das Hauptrepository der Vorgabe
  t.ctx.S.lib = null; assert.equal(X.errUpstream(), "ploeffler/GhostWriter"); t.ctx.S.lib = {program:{upstream:"böse/../x"}}; assert.equal(X.errUpstream(), "ploeffler/GhostWriter");
  // Unbehandelte Fehler: Hinweis, Protokoll
  t.listeners.error({message:"Boom in chapters/01/a.md"}); assert(X.errList()[0].klasse === "js-fehler" && !X.errList()[0].meldung.includes("chapters"));

  // Matrix: Einstellungen laden (nur die reine Auswertung)
  const ctx2 = {S:{view:"x"}, store:{get:() => null, set(){}}, esc: String, $: () => null, window:{}, document:{addEventListener(){}}, GW_PORTS:{}, NET:{}, Date, Number, JSON, Array, Object, String, Math, errBrowser: () => "x · y", token: () => "", errList: () => [], location:{origin:""}, navigator:{}, crumbs(){}, busy(){}, msgBox: () => "", show(){}, errStore(){}, rest(){}, OB:{all: async () => []}, netProbe(){}, errText: String};
  vm.runInNewContext(read("einstellungen-web.js") + "\n;this.__x = {setEval};", ctx2);
  const E = ctx2.__x.setEval, matrix = JSON.parse(read("faehigkeiten.json")), fn = id => matrix.functions.find(f => f.id === id);
  const strong = {indexedDB:true, secure:true, serviceWorker:true, persistApi:true, microphone:true, mediaRecorder:true, webgpu:true, shaderF16:true, memoryGB:8, storageFreeGB:20, builtInTranslator:false, builtInPrompt:false};
  assert.equal(E(fn("modell-im-browser"), strong).r, "ok");
  assert.equal(E(fn("modell-im-browser"), Object.assign({}, strong, {webgpu:false})).r, "nein");
  assert.match(E(fn("modell-im-browser"), Object.assign({}, strong, {webgpu:false})).why, /WebGPU, mindestens 4 GB Arbeitsspeicher und 3 GB freien Speicher/);
  assert.equal(E(fn("modell-im-browser"), Object.assign({}, strong, {memoryGB:2})).r, "nein");
  assert.equal(E(fn("modell-im-browser"), Object.assign({}, strong, {memoryGB:null})).r, "eingeschraenkt");   // deviceMemory nicht überall verfügbar: unklar statt falsch
  assert.equal(E(fn("lokal-uebersetzen"), Object.assign({}, strong, {webgpu:false, builtInTranslator:true})).r, "ok");   // Alternative: Browser-Übersetzer
  assert.equal(E(fn("lokal-uebersetzen"), Object.assign({}, strong, {webgpu:false})).r, "nein");
  assert.equal(E(fn("offline-schreiben"), Object.assign({}, strong, {indexedDB:false})).r, "nein");
  assert.equal(E(fn("app-installieren"), Object.assign({}, strong, {secure:false})).r, "nein");
  for (const f of matrix.functions){ assert(f.name.de && f.name.en && f.reason.de && f.reason.en && f.fallback.de && f.fallback.en, f.id + ": Texte DE/EN"); }
  console.log("fehler ok");
})().catch(e => { console.error(e); process.exit(1); });
