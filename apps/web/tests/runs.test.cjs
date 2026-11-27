// Actions starten und Läufe ansehen (#662): richtige Workflow-Dateien, Eingaben und Prüfungen vor dem Start. Aufruf: node apps/web/tests/runs.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname, "..", "runs-web.js"), "utf8");
const calls = [], rests = [];
const ctx = {
  S: {owner:"o", repo:"r", book:{branch:"buch/x"}, view:"runs"}, esc: String, $: () => null, crumbs(){}, busy(){}, msgBox: () => "", show(){}, errText: e => "Fehler: " + e.message, fmtTime: () => "t", fmtBytes: n => n + " B",
  document: {addEventListener(){}, createElement: () => ({dataset:{}, style:{}})}, window: {scrollTo(){}}, FormData: class { constructor(f){ this.f = f; } forEach(fn){ Object.entries(this.f.values).forEach(([k, v]) => [].concat(v).forEach(x => fn(x, k))); } },
  GW_PORTS: {git: {dispatch: async (file, ref, inputs) => { calls.push({file, ref, inputs}); }, listRuns: async () => [], listReleases: async () => []}},
  workOf: b => "ghostwriter/" + b.branch,
  setTimeout, clearTimeout, Date, JSON, Array, Object, String, Number, Math, Promise
};
vm.runInNewContext(src + "\n;this.__x = {runDispatch, RUN_STATE, runErr, RUN, GW_PORTS, cleanWhy, runsFetch, runsScope, runRelOfBook, runBookOf};", ctx);
const X = ctx.__x, form = (values, checked) => ({values, querySelectorAll: () => (checked || []).map(v => ({value:v})), closest(){}});
(async () => {
  // Probedruck: Formate und Kapitel, Vorgabe pdf; Ref ist der Buch-Branch
  assert.equal(await X.runDispatch("proof", form({chapters:" 1-4 "}, ["pdf", "epub"])), "");
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0])), {file:"proof.yml", ref:"buch/x", inputs:{formats:"pdf,epub", chapters:"1-4"}});
  await X.runDispatch("proof", form({}, [])); assert.equal(calls[1].inputs.formats, "pdf");
  // Vorabfassung: ohne Auswahl leer (= Einstellungen des Buchs)
  await X.runDispatch("preview", form({}, [])); assert.deepEqual(JSON.parse(JSON.stringify(calls[2])), {file:"preview.yml", ref:"buch/x", inputs:{formats:"", chapters:""}});
  // Manuskript: Lesefassung braucht Kapitel oder Abschnitt
  const n = calls.length;
  assert.match(await X.runDispatch("manuscript", form({format:"md", chapter:""})), /Kapitel oder einen Abschnitt/); assert.equal(calls.length, n);
  assert.equal(await X.runDispatch("manuscript", form({format:"md", chapter:"5.1"})), ""); assert.equal(calls[n].inputs.chapter, "5.1");
  // Auschecken: Gegenleser Pflicht, Bereich Pflicht, Frist als Datum; Booleans als Text
  assert.match(await X.runDispatch("checkout", form({chapters:"3-5"})), /Gegenleser/);
  assert.match(await X.runDispatch("checkout", form({reader:"anna"})), /Kapitel angeben|ganzes Buch/);
  assert.match(await X.runDispatch("checkout", form({reader:"anna", chapters:"3", until:"morgen"})), /JJJJ-MM-TT/);
  assert.equal(calls.length, n + 1);
  assert.equal(await X.runDispatch("checkout", form({reader:"anna", book:"on", dry_run:"on", until:"2026-12-01"})), "");
  assert.deepEqual(JSON.parse(JSON.stringify(calls[n + 1])), {file:"checkout.yml", ref:"buch/x", inputs:{chapters:"", book:"true", reader:"anna", until:"2026-12-01", dry_run:"true"}});
  // Eingaben werden geprüft, bevor etwas an GitHub geht (keine Sonderzeichen in Kapitelangaben)
  const m = calls.length;
  assert.match(await X.runDispatch("proof", form({chapters:"1; rm -rf"}, ["pdf"])), /nur als Zahlen/); assert.match(await X.runDispatch("manuscript", form({format:"pdf", chapter:"a"})), /nur als Zahlen/);
  assert.equal(calls.length, m);
  // Läufe: Stand
  assert.deepEqual(JSON.parse(JSON.stringify(X.RUN_STATE({status:"in_progress"}))), ["läuft", "⏳"]);
  assert.deepEqual(JSON.parse(JSON.stringify(X.RUN_STATE({status:"completed", conclusion:"success"}))), ["fertig", "✓"]);
  assert.deepEqual(JSON.parse(JSON.stringify(X.RUN_STATE({status:"completed", conclusion:"failure"}))), ["fehlgeschlagen", "✗"]);
  assert.deepEqual(JSON.parse(JSON.stringify(X.RUN_STATE({status:"completed", conclusion:"cancelled"}))), ["abgebrochen", "⏹"]);
  // Fehlertexte beim Starten
  assert.match(X.runErr({code:"http_404"}), /fehlt die Action/); assert.match(X.runErr({code:"http_403"}), /Actions/); assert.match(X.runErr({code:"http_422", message:"Unexpected inputs"}), /nicht angenommen/);
  // Aktionen der Ansichten gehen in diese Ansicht
  for (const a of ["edition.create.open", "edition.proof", "edition.preview", "manuscript.export", "checkout.start"]) assert.equal(typeof X.GW_PORTS.actions[a], "function", a);
  assert.equal(typeof X.GW_PORTS.views.runs, "function");
  // Umfang (v1.6): im Buch nur dessen Läufe (Buch- und Arbeits-Branch), in der Bibliothek alle mit Buchname
  const asked = [], mk = (id, branch, created) => ({id, name:"n" + id, branch, created, status:"completed", conclusion:"success", url:"u"});
  const all = [mk(1, "buch/x", "2026-11-27T10:00:00Z"), mk(2, "ghostwriter/buch/x", "2026-11-27T11:00:00Z"), mk(3, "buch/y", "2026-11-27T12:00:00Z"), mk(4, "main", "2026-11-27T13:00:00Z")];
  ctx.GW_PORTS.git.listRuns = async (f, q) => { asked.push(q.branch || ""); return all.filter(r => !q.branch || r.branch === q.branch); };
  ctx.S.lib = {books:[{branch:"buch/x", title:"Buch X", title_short:"X"}, {branch:"buch/y", title:"Buch Y"}]}; ctx.S.book = ctx.S.lib.books[0]; X.RUN.scope = "";
  assert.equal(X.runsScope(), "book");
  assert.deepEqual((await X.runsFetch()).map(r => r.id), [2, 1]); assert.deepEqual(asked, ["buch/x", "ghostwriter/buch/x"]);
  X.RUN.scope = "lib"; assert.equal(X.runsScope(), "lib"); asked.length = 0;
  assert.deepEqual((await X.runsFetch()).map(r => r.id), [1, 2, 3, 4]); assert.deepEqual(asked, [""]);
  assert.equal(X.runBookOf(all[1]).title_short, "X"); assert.equal(X.runBookOf(all[3]), undefined);
  ctx.S.book = null; X.RUN.scope = ""; assert.equal(X.runsScope(), "lib");   // Bücherregal: immer alle
  ctx.S.book = ctx.S.lib.books[0];
  assert.equal(X.runRelOfBook({tag:"x-auflage-1", name:"Auflage 1"}), true); assert.equal(X.runRelOfBook({tag:"y-auflage-1", name:"Buch Y"}), false);
  ctx.S.book = {branch:"main"}; assert.equal(X.runRelOfBook({tag:"irgendwas", name:""}), true);   // Einzelbuch: alle
  // „Branches aufräumen“ auf der Seite Daten: nur mit Rechten
  assert.equal(X.cleanWhy(true, "ok", true), "");
  assert.match(X.cleanWhy(true, "ok", false), /Nicht angemeldet/); assert.match(X.cleanWhy(false, "ok", true), /Schreibrecht/);
  assert.match(X.cleanWhy(true, "forbidden", true), /„Actions“/); assert.match(X.cleanWhy(true, "missing", true), /fehlt die Action/);
  assert.equal(X.cleanWhy(true, "unknown", true), "");                       // unklar: der Start meldet ein fehlendes Recht verständlich
  assert.equal(typeof X.GW_PORTS.afterRender, "function");
  console.log("runs ok");
})().catch(e => { console.error(e); process.exit(1); });
