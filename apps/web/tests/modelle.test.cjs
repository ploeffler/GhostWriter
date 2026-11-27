// Modell im Browser (#525, #662): Modellliste, Passung zum Gerät, Auswahl, Werkzeug-Parser. Aufruf: node apps/web/tests/modelle.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const dir = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(dir, "modelle-web.js"), "utf8"), ev = fs.readFileSync(path.join(dir, "einstellungen-web.js"), "utf8");
const list = JSON.parse(fs.readFileSync(path.join(dir, "modelle.json"), "utf8"));
const ctx = {fmtBytes: n => String(n), store:{d:{}, set(k, v){ this.d[k] = v; }, get(k){ return this.d[k] || ""; }}, GW_PORTS:{}, fetch: async () => ({json: async () => list}), $: () => null, esc: String, window:{}, console, S:{view:"model"}, navigator:{}, document:{addEventListener(){}, visibilityState:"visible"}, setTimeout, Date};
vm.createContext(ctx);
// setEval aus den Einstellungen (gleiche Auswertung wie die Matrix) herauslösen
const m = ev.match(/function setEval[\s\S]*?\n}\n/); assert.ok(m, "setEval gefunden");
vm.runInContext(m[0] + "\n" + src + "\nthis.api = {mdlFit, mdlPick, mdlParseTools, mdlMessages, MDL_TASKS, mdlList, mdlState, mdlDownload, MDL, mdlProgLabel};", ctx);
const api = ctx.api;

// Liste: jedes Modell vollständig, Deutsch und Englisch, nur freie Lizenzen
assert.equal(list.runtime.version, "4.3.2"); assert.match(list.runtime.url, /transformers@4\.3\.2\/dist\/transformers\.min\.js$/, "eigenständige Browser-Fassung (#739): die .web-Fassung importiert onnxruntime-web ohne Pfad");
for (const mo of list.models){
  for (const k of ["id", "repo", "dtype", "class", "tier", "sizeBytes", "license", "requires", "toolFormat"]) assert.ok(mo[k] != null, mo.id + ": " + k);
  for (const k of ["name", "note", "reason"]) assert.ok(mo[k].de && mo[k].en, mo.id + ": " + k + " DE/EN");
  assert.equal(mo.license, "Apache 2.0", mo.id);
}
const by = id => list.models.find(x => x.id === id);

// Passung
const good = {webgpu:true, shaderF16:true, memoryGB:8, storageFreeGB:20};
assert.equal(api.mdlFit(by("gemma4-e2b"), good).r, "ok");
assert.equal(api.mdlFit(by("gemma4-e2b"), {...good, webgpu:false}).r, "nein");
assert.equal(api.mdlFit(by("gemma4-e2b"), {...good, shaderF16:false}).r, "nein");
assert.equal(api.mdlFit(by("gemma4-e2b"), {...good, storageFreeGB:1}).r, "nein");
assert.match(api.mdlFit(by("gemma4-e2b"), {...good, webgpu:false}).why, /6 GB/);
assert.equal(api.mdlFit(by("gemma4-e2b"), {...good, memoryGB:null}).r, "eingeschraenkt");

// Auswahl: viel Rechner → stark; mittel → Standard; klein → Notbehelf; nichts → null
assert.equal(api.mdlPick(list.models, good).id, "gemma4-e4b");
assert.equal(api.mdlPick(list.models, {...good, memoryGB:6, storageFreeGB:5}).id, "gemma4-e2b");
assert.equal(api.mdlPick(list.models, {...good, memoryGB:4, storageFreeGB:3}).id, "qwen35-2b");
assert.equal(api.mdlPick(list.models, {...good, webgpu:false}), null);

// Werkzeugaufrufe je Format (Formate aus dem Test in #525)
const g = api.mdlParseTools('Ich suche.<|tool_call>call:suche{anfrage:<|"|>Wetter in Wien<|"|>,n:3}<tool_call|>', "gemma");
assert.deepEqual(JSON.parse(JSON.stringify(g)), [{name:"suche", args:{anfrage:"Wetter in Wien", n:3}}]);
const q = api.mdlParseTools("<tool_call>\n<function=suche>\n<parameter=anfrage>\nWetter\n</parameter>\n</function>\n</tool_call>", "qwen");
assert.deepEqual(JSON.parse(JSON.stringify(q)), [{name:"suche", args:{anfrage:"Wetter"}}]);
assert.equal(api.mdlParseTools("kein Aufruf", "gemma").length, 0);
assert.equal(api.mdlParseTools("<tool_call>kaputt", "qwen").length, 0);

// Nachrichten: Systemanweisung verbietet Erfinden; Hinweis wird vorangestellt
const msg = api.mdlMessages("lektorat", "Text.", "Hinweis");
assert.equal(msg[0].role, "system"); assert.match(msg[0].content, /Erfinde nichts/); assert.equal(msg[1].content, "Hinweis\n\nText.");


// Download (#758): Anzeige sofort, halbe Downloads, Abbrechen, 100 %, Wake Lock
(async () => {
  const m = by("gemma4-e2b"), views = [], keys = [];
  ctx.modelView = () => { views.push({busy:api.MDL.busy, pct:api.MDL.progress.pct}); };
  ctx.window.caches = ctx.caches = {open: async () => ({keys: async () => keys.map(url => ({url}))})};
  let locks = 0, released = 0; ctx.navigator.wakeLock = {request: async () => { locks++; return {release: async () => { released++; }, addEventListener(){}}; }};
  // Zustand: nichts / Dateien ohne Marke = unvollständig / mit Marke = vollständig
  assert.equal(await api.mdlState(m), "none");
  keys.push("https://huggingface.co/" + m.repo + "/resolve/main/config.json");
  assert.equal(await api.mdlState(m), "partial", "Dateien ohne Marke gelten nicht als vorhanden");
  ctx.store.set("gw.model.done." + m.id, "1");
  assert.equal(await api.mdlState(m), "complete");
  ctx.store.set("gw.model.done." + m.id, "");
  assert.equal(api.mdlProgLabel({}), "wird geladen …");
  // Lauf mit nachgemachter Laufzeit: Balken ist vor dem Laden da, am Ende 100 %, Marke gesetzt, Sperre freigegeben
  ctx.mdlRuntime = async () => ({ME: {from_pretrained: async (repo, o) => { o.progress_callback({status:"progress", file:"a", loaded:1e9, total:2.9e9}); return {}; }}, AutoProcessor: {from_pretrained: async () => ({})}});
  const mm = {...m, class:"ME"};
  await api.mdlDownload(mm);
  assert.equal(views[0].busy, true, "Ansicht wird gleich nach dem Start gezeichnet, nicht erst am Ende");
  assert.equal(ctx.store.get("gw.model.done." + m.id), "1"); assert.equal(ctx.store.get("gw.model.run"), ""); assert.equal(api.MDL.loaded, m.id);
  assert.equal(locks, 1); assert.equal(released, 1);
  // Abbrechen wirkt: der Download endet an der nächsten Fortschrittsmeldung, keine Marke, Meldung „abgebrochen“
  ctx.store.set("gw.model.done." + m.id, ""); api.MDL.loaded = null;
  ctx.mdlRuntime = async () => ({ME: {from_pretrained: async (repo, o) => { api.MDL.cancel = true; o.progress_callback({status:"progress", file:"a", loaded:1, total:2}); return {}; }}, AutoProcessor: {from_pretrained: async () => ({})}});
  await api.mdlDownload(mm);
  assert.equal(ctx.store.get("gw.model.done." + m.id), ""); assert.equal(api.MDL.loaded, null); assert.match(api.MDL.msg.html, /abgebrochen/); assert.equal(api.MDL.busy, false);
  // Fehler: Meldung nennt das Fortsetzen
  ctx.mdlRuntime = async () => ({ME: {from_pretrained: async () => { throw new Error("Netz weg"); }}});
  await api.mdlDownload(mm);
  assert.equal(api.MDL.msg.kind, "err"); assert.match(api.MDL.msg.html, /fortsetzen/); assert.equal(ctx.store.get("gw.model.done." + m.id), "");
  console.log("modelle.test.cjs: ok");
})().catch(e => { console.error(e); process.exit(1); });
