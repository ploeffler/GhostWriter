// Serienansicht (#742) und Speichern ohne erkanntes Netz (#744). Aufruf: node apps/web/tests/serie.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const read = f => fs.readFileSync(path.join(__dirname, "..", "..", f), "utf8");
(async () => {
  // ---- Serienansicht
  const Y = {"series/ser-a/series.yml":"id: ser-a\ntitle: Die Reihe\nkind: continuous\nvolumes: [buch/eins, buch/zwei, buch/weg]\n", "series/ser-a/glossary.yml":"terms:\n  - {term: Nebel, text: Ein Ort}\n", "series/ser-a/characters/char-x.md":"---\nid: char-x\nname: Xaver\nrole: Held\n---\n"};
  const jsyaml = {load: t => { const o = {}; const m = /volumes: \[(.*?)\]/.exec(t); if (/^id:/m.test(t)){ o.id = /^id: (.*)$/m.exec(t)[1]; o.title = /^title: (.*)$/m.exec(t)[1]; o.kind = "continuous"; o.volumes = m[1].split(", "); } else if (/terms:/.test(t)) o.terms = [{term:"Nebel", text:"Ein Ort"}]; else o.name = "x"; return o; }};
  const html = {app:{innerHTML:""}}, calls = [];
  const ctx = {S:{owner:"o", repo:"r", lib:{books:[{branch:"buch/eins", title:"Eins", status:"ready", sections_total:10, sections_approved:5}, {branch:"buch/zwei", title:"Zwei", status:"setup"}], series:[]}}, window:{jsyaml, scrollTo(){}}, document:{addEventListener(){}}, $: id => html[id], esc: String, plural: (n, a, b) => n + " " + (n === 1 ? a : b), pool: async (l, n, f) => Promise.all(l.map(f)), crumbs(){}, busy(){}, errText: e => e.message,
    getFile: async p => { if (!(p in Y)) throw {message:"nf"}; return {text:Y[p]}; }, listDefault: async d => d === "series/ser-a/characters" ? [{name:"char-x.md", path:d + "/char-x.md"}] : [], front: () => ({id:"char-x", name:"Xaver", role:"Held"}),
    bookRow: b => ({BOOK_TITLE:b.title, BOOK_TITLE_SHORT:b.title, BOOK_STATE:b.status === "ready" ? "ready" : "setup", BOOK_STATE_TEXT:b.status === "ready" ? "eingerichtet" : "im Aufbau", BOOK_PROGRESS:50, BOOK_PROGRESS_TEXT:"5 von 10 Abschnitten", BOOK_EDITION_TEXT:"noch keine Auflage"}),
    msgBox: () => "", show: v => calls.push(v), openBook: b => calls.push("open:" + b), GW_PORTS:{}, console};
  vm.createContext(ctx); vm.runInContext(read("web/serie-web.js") + "\nthis.api = {seriesData, seriesHtml, seriesView};", ctx);
  const d = await ctx.api.seriesData("ser-a");
  assert.equal(d.VOLUMES.length, 3); assert.equal(d.VOLUMES[0].V_TITLE, "Eins"); assert.equal(d.VOLUMES[2].V_STATE_TEXT, "nicht gefunden");
  assert.equal(d.SERIES_CHARACTERS[0].SC_NAME, "Xaver"); assert.equal(d.SERIES_TERMS[0].ST_TERM, "Nebel"); assert.equal(d.VOLUME_COUNT_TEXT, "3 Bände");
  const h = ctx.api.seriesHtml(d);
  assert.match(h, /Band öffnen/); assert.equal((h.match(/data-ser-open=/g) || []).length, 2, "kein Knopf für einen fehlenden Band"); assert.match(h, /nur angezeigt/);
  await assert.rejects(ctx.api.seriesData("ser-gibts-nicht"), e => /nicht lesbar/.test(e.message));
  await ctx.api.seriesView("ser-gibts-nicht"); assert.deepEqual(calls, ["library"]); assert.equal(ctx.S.msg.kind, "err");
  assert.equal(typeof ctx.GW_PORTS.actions["view.series"], "function"); ctx.GW_PORTS.actions["view.series"]({series_id:"ser-a"}); assert.equal(calls.at(-1), "series");

  // ---- Speichern: Netzfehler vor dem lokalen Sichern führt zur Outbox (#744)
  const out = [];
  const c2 = {S:{book:{branch:"buch/b", work_branch:"gw/b", title:"B"}, secFile:{text:"---\nid: s\n---\n## Manuskript\n\nalt\n", sha:"s1"}, secNo:"1.1", files:new Map(), readRef:"gw/b", owner:"o", repo:"r"}, busy(){}, esc: String, show: (v, a) => out.push("show:" + v), errText: e => e.message, console,
    allSecs: () => [{s:{id:"sec-1", path:"chapters/01/sections/01.md", title:"T"}}], workOf: b => b.work_branch, front: () => ({}), msOf: () => "alt", setBlock: (md, k, v) => k === "Manuskript" ? md.replace("alt", v) : md, setFact: m => m,
    prepareWork: async () => { throw {code:"offline", message:"Keine Verbindung zu GitHub."}; }, getFile: async () => { throw {code:"offline"}; }, applyOverlay(){}, openPR: async () => null, prCommits: async () => {}, loadBookData: async () => {},
    GW_PORTS:{git:{}, outbox:{offline: () => false, pending: async () => 0, add: async o => { out.push("add:" + o.files[0].path); return 1; }}}};
  vm.createContext(c2); vm.runInContext(read("shared/s09-schreiben.js") + "\nthis.api = {saveSection};", c2);
  await c2.api.saveSection({section_id:"sec-1", manuscript:"neu", goal:"", summary:""});
  assert.deepEqual(out, ["add:chapters/01/sections/01.md", "show:section"]);
  assert.equal(c2.S.msg.kind, "warn"); assert.match(c2.S.msg.html, /Nur auf diesem Gerät gespeichert/);
  // anderer Fehler (kein Netzfehler): nicht lokal sichern, Fehler zeigen
  out.length = 0; c2.prepareWork = async () => { throw {code:"forbidden", message:"Kein Zugriff."}; };
  await c2.api.saveSection({section_id:"sec-1", manuscript:"neu", goal:"", summary:""});
  assert.deepEqual(out, ["show:section"]); assert.equal(c2.S.msg.kind, "err");
  // Gegenprobe (#744): ein 403 oder 422 von GitHub gilt nicht als Netzfehler und wandert nicht in die Outbox
  for (const code of ["http_403", "http_422"]){ out.length = 0; c2.prepareWork = async () => { throw {code, message:"x"}; }; await c2.api.saveSection({section_id:"sec-1", manuscript:"neu", goal:"", summary:""}); assert.deepEqual(out, ["show:section"], code); assert.equal(c2.S.msg.kind, "err"); }
  console.log("serie.test.cjs: ok");
})().catch(e => { console.error(e); process.exit(1); });
