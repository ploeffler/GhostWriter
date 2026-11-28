// Offline-Bestand (#744, Teil 2): getFile legt Gelesenes ab und liest es nur bei Netzfehler zurück; Schreibwege bekommen nie einen alten Stand. Aufruf: node apps/web/tests/snap.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const rd = f => fs.readFileSync(path.join(__dirname, "..", f), "utf8"), sh = f => fs.readFileSync(path.join(__dirname, "..", "..", "shared", f), "utf8");

function make(){
  const logged = [], shown = [], calls = {};
  const git = {online:true, files:{}, async getFile(p, ref){ if (!git.online) throw {code:"offline", message:"Keine Verbindung"}; if (p in git.files === false) throw {code:"http_404"}; return {text:git.files[p], sha:"s-" + p, commit:"c1"}; },
    async listPRs(){ if (!git.online) throw {code:"offline"}; return []; }};
  const ctx = {S:{files:new Map(), owner:"o", repo:"r", msg:null, lib:null, book:null}, GW_PORTS:{git}, store:{set(){}}, busy(){}, esc:String, show:v => shown.push(v), crumbs(){}, workOf: b => "ghostwriter/" + b.branch,
    openPR: async b => (await git.listPRs()).length ? {} : null, prCommits: async () => {}, loadRole: async () => {}, loadSkills: async () => {}, document:{querySelector(){}}, errText: e => "ERR:" + (e && e.code), JSON, Promise, Map, Object, String, Array, Math, Date, console,
    window:{}, repoMissingText: async e => "MISSING", loadBookData: null, costsFromFiles: async () => {}};
  vm.createContext(ctx);
  vm.runInContext(sh("s02-dateien.js") + "\n" + rd("snap-web.js") + "\nthis.api = {getFile, SB};", ctx);
  return {ctx, git, shown, logged, api: ctx.api};
}
const nap = () => new Promise(r => setTimeout(r, 5));

(async () => {
  // 1 Füllen: erfolgreiches getFile legt Text, Prüfsumme und Commit unter repo|ref|pfad ab
  let t = make(); t.git.files["a.md"] = "Text A";
  let f = await t.api.getFile("a.md", "ghostwriter/x"); await nap();
  assert.equal(f.text, "Text A"); const rec = await t.api.SB.get("o/r|ghostwriter/x|a.md");
  assert.equal(rec.text, "Text A"); assert.equal(rec.sha, "s-a.md"); assert.equal(rec.commit, "c1"); assert.ok(!t.ctx.S.stale);
  // 2 Lesen offline: S.files leer (Neuladen), Netz weg → gespeicherter Stand, S.stale gesetzt
  t.ctx.S.files.clear(); t.git.online = false;
  f = await t.api.getFile("a.md", "ghostwriter/x"); assert.equal(f.text, "Text A"); assert.equal(f.sha, "s-a.md"); assert.ok(t.ctx.S.stale > 0);
  // auch mit fresh + allowStale (Lesewege wie loadBookData), nicht ohne allowStale (3 Schreibwege)
  t.ctx.S.files.clear(); f = await t.api.getFile("a.md", "ghostwriter/x", true, true); assert.equal(f.text, "Text A");
  t.ctx.S.files.clear(); await assert.rejects(t.api.getFile("a.md", "ghostwriter/x", true), e => e.code === "offline");   // Schreibweg: nie ein alter Stand als „frisch“
  // 4 nie gelesen: der Fehler bleibt
  await assert.rejects(t.api.getFile("b.md", "ghostwriter/x"), e => e.code === "offline");
  // 5 Fehler ohne Netzbezug werden nicht durch die Ablage ersetzt
  t.git.online = true; t.git.getFile = async () => { throw {code:"http_403"}; }; t.ctx.S.files.clear();
  await assert.rejects(t.api.getFile("a.md", "ghostwriter/x"), e => e.code === "http_403");
  t.git.getFile = async () => { throw {code:"http_404"}; };
  await assert.rejects(t.api.getFile("a.md", "ghostwriter/x"), e => e.code === "http_404");
  // anderer Branch / anderes Repository: kein Treffer
  t.git.getFile = async () => { throw {code:"offline"}; };
  await assert.rejects(t.api.getFile("a.md", "main")); t.ctx.S.repo = "anders"; await assert.rejects(t.api.getFile("a.md", "ghostwriter/x")); t.ctx.S.repo = "r";
  // Abmelden: clear leert die Ablage
  await t.ctx.GW_PORTS.snap.clear(); assert.equal(await t.api.SB.get("o/r|ghostwriter/x|a.md"), null);

  // 6 Start offline: library.json aus der Ablage zeigt das Bücherregal; ein nie geöffnetes Repository bekommt die verständliche Meldung
  t = make(); const lib = JSON.stringify({books:[{branch:"b1", title:"A"}, {branch:"b2", title:"B"}]}); t.git.files["library.json"] = lib;
  vm.runInContext(sh("s07-laden.js") + "\n;this.api2 = {loadRepo, openBook};", t.ctx);
  await t.ctx.api2.loadRepo("o/r"); await nap(); assert.deepEqual(t.shown, ["library"]);
  t.git.online = false; t.shown.length = 0; await t.ctx.api2.loadRepo("o/r");
  assert.deepEqual(t.shown, ["library"]); assert.equal(t.ctx.S.lib.books.length, 2); assert.ok(t.ctx.S.stale > 0);
  t.ctx.S.repo = ""; t.shown.length = 0; await t.ctx.api2.loadRepo("o/neu");
  assert.deepEqual(t.shown, ["connect"]); assert.match(t.ctx.S.msg.html, /noch nie geöffnet.*einmal mit Netz/);

  // 7 Buch offline öffnen: liest vom zuletzt gelesenen Arbeits-Branch (meta.readRef), nicht vom Buch-Branch
  t = make(); vm.runInContext(sh("s07-laden.js") + "\n;this.api2 = {loadRepo, openBook};", t.ctx);
  const refs = []; t.ctx.loadBookData = async ref => { refs.push(ref); t.ctx.S.stale = 0; };
  t.ctx.S.lib = {books:[{branch:"b1"}]}; t.ctx.S.owner = "o"; t.ctx.S.repo = "r";
  await t.ctx.api2.openBook("b1"); await nap(); assert.deepEqual(refs, ["b1"], "online ohne Änderungspaket: Buch-Branch");
  await t.ctx.GW_PORTS.snap.setMeta("o/r", {branch:"b1", readRef:"ghostwriter/b1"});
  t.git.online = false; t.ctx.GW_PORTS.outbox = {offline: () => true};
  await t.ctx.api2.openBook("b1"); assert.equal(refs[1], "ghostwriter/b1", "offline: zuletzt gelesener Arbeits-Branch");
  // ein nie geöffnetes Buch offline: verständliche Meldung statt „Keine Verbindung“
  t.ctx.loadBookData = async () => { throw {code:"offline"}; }; t.ctx.S.lib.books.push({branch:"b2"});
  await t.ctx.api2.openBook("b2"); assert.match(t.ctx.S.msg.html, /noch nicht auf diesem Gerät/);
  // 8 Rücksetzen: nach erfolgreichem Laden ist S.stale leer (loadBookData setzt es zurück, hier nachgebildet durch die echte Funktion unten)
  const lb = sh("s07-laden.js"); assert.match(lb, /S\.readRef = ref; S\.files\.clear\(\); S\.stale = 0;/);
  // Leistenhinweis „Stand vom …“ nur mit S.stale
  const nsrc = rd("net-web.js"), el = {hidden:true, className:"", textContent:""}, nctx = {S:{stale:0}, $: () => el, navigator:{onLine:false}, Date, GW_PORTS:{}, console, fetch(){}, AbortController, setTimeout, clearTimeout, obRender(){}};
  vm.runInNewContext(nsrc + "\n;this.__r = netRender; this.NET = NET;", nctx); nctx.NET.online = false; nctx.__r();
  assert.doesNotMatch(el.textContent, /Stand vom/); nctx.S.stale = Date.UTC(2026, 10, 27, 12, 17); nctx.__r(); assert.match(el.textContent, /Offline.*Angezeigt wird der Stand vom .* Uhr\./s);
  nctx.NET.online = true; nctx.NET.github = true; nctx.__r(); assert.equal(el.textContent, "", "online: kein Hinweis");

  // login(): ein Netzfehler wird nicht als „chat“ festgehalten
  const lsrc = sh("s10-freigaben.js").split("\n").find(l => l.startsWith("async function login()"));
  const lctx = {S:{login:""}, gwNetErr: e => e && e.code === "offline", GW_PORTS:{git:{me: async () => { throw {code:"offline"}; }}}}; vm.runInNewContext(lsrc + "\n;this.__l = login;", lctx);
  assert.equal(await lctx.__l(), "chat"); assert.equal(lctx.S.login, "", "Netzfehler nicht festhalten");
  lctx.GW_PORTS.git.me = async () => { throw {code:"http_401"}; }; assert.equal(await lctx.__l(), "chat"); assert.equal(lctx.S.login, "chat");
  console.log("snap.test.cjs: ok");
})().catch(e => { console.error(e); process.exit(1); });
