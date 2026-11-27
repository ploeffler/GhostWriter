// Modell im Browser (#525, #662): Modellliste, Passung zum Gerät, Auswahl, Werkzeug-Parser. Aufruf: node apps/web/tests/modelle.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const dir = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(dir, "modelle-web.js"), "utf8"), ev = fs.readFileSync(path.join(dir, "einstellungen-web.js"), "utf8");
const list = JSON.parse(fs.readFileSync(path.join(dir, "modelle.json"), "utf8"));
const ctx = {fmtBytes: n => String(n), store:{set(){}, get(){ return ""; }}, document:{addEventListener(){}}, GW_PORTS:{}, fetch: async () => ({json: async () => list}), $: () => null, esc: String, window:{}, console};
vm.createContext(ctx);
// setEval aus den Einstellungen (gleiche Auswertung wie die Matrix) herauslösen
const m = ev.match(/function setEval[\s\S]*?\n}\n/); assert.ok(m, "setEval gefunden");
vm.runInContext(m[0] + "\n" + src + "\nthis.api = {mdlFit, mdlPick, mdlParseTools, mdlMessages, MDL_TASKS, mdlList};", ctx);
const api = ctx.api;

// Liste: jedes Modell vollständig, Deutsch und Englisch, nur freie Lizenzen
assert.equal(list.runtime.version, "4.3.2"); assert.match(list.runtime.url, /transformers@4\.3\.2/);
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
console.log("modelle.test.cjs: ok");
