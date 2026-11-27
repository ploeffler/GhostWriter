// Kosten ohne Index und Kosten nur fürs ganze Buch (#754). Aufruf: node apps/web/tests/kosten.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const sh = f => fs.readFileSync(path.join(__dirname, "..", "..", "shared", f), "utf8");
const yaml = fs.readFileSync(path.join(__dirname, "..", "vendor", "js-yaml.min.js"), "utf8");
const files = {
  "costs/project.yml": "scope: project\nentries:\n- {source: action_api, cost_amount: 0.3189, cost_status: estimated}\n- {source: action_api, cost_amount: 0.3189, cost_status: estimated}\n- {source: chat_estimate, cost_amount: 9, cost_status: estimated}\n",
  "chapters/01-a/costs/s1.yml": "entries:\n- {source: backend_api, cost_amount: 1.5, cost_status: actual}\n",
};
const ctx = {window:{}, S:{struct:[{id:"c1", path:"chapters/01-a", sections:[{id:"s1"}, {id:"s2"}]}], idx:{project:{}}}, Math, Number, Object, Array, Promise, JSON, String, Date, Map,
  getFile: async p => { if (files[p] == null) throw {code:"http_404"}; return {text:files[p]}; },
  pool: async (items, n, fn) => Promise.all(items.map(fn))};
vm.createContext(ctx); vm.runInContext(yaml, ctx); ctx.window.jsyaml = ctx.jsyaml || ctx.window.jsyaml || ctx.module;
vm.runInContext(sh("s07-laden.js").match(/\/\* Kosten ohne Index[\s\S]*?\nfunction buildStruct/)[0].replace(/function buildStruct$/, "") + "\n;this.__run = costsFromFiles;", ctx);
(async () => {
  await ctx.__run("ref");
  // Projekt: zwei Medienaufträge (Schätzung), Chat-Schätzung zählt nicht; Abschnitt s1 hat eigene Kosten, s2 keine
  assert.equal(ctx.S.idx.project.cost.text, "≈ 2,14 €");   // 0,3189 + 0,3189 + 1,5 = 2,1378
  assert.equal(ctx.S.struct[0].sections[0].cost.text, "1,50 €"); assert.equal(ctx.S.struct[0].sections[1].cost.text, "–");
  assert.equal(ctx.S.struct[0].cost.text, "1,50 €");
  // Hinweis: nur Buchkosten, keine bei Kapiteln → „– (nur Buch)“ und erklärender Tooltip; sonst unverändert
  const s5 = sh("s05-daten-vorlagen.js").match(/const projectOnlyCosts[\s\S]*?const costTip[^\n]*\n/)[0];
  const c2 = {S:{idx:{project:{cost:{amount:2.87, text:"≈ 2,87 €"}}}, struct:[{cost:{amount:null, text:"–"}, sections:[]}]}};
  vm.createContext(c2); vm.runInContext(s5 + "\n;this.api = {projectOnlyCosts, costShown, costTip};", c2);
  assert.equal(c2.api.projectOnlyCosts(), true);
  assert.equal(c2.api.costShown({text:"–"}, true), "– (nur Buch)"); assert.match(c2.api.costTip({text:"–"}, "Summe", true), /nur fürs ganze Buch erfasst/);
  assert.equal(c2.api.costShown({text:"1,50 €"}, true), "1,50 €"); assert.equal(c2.api.costTip({text:"1,50 €"}, "Summe", true), "Summe");
  c2.S.struct[0].cost.amount = 1; assert.equal(c2.api.projectOnlyCosts(), false);
  assert.equal(c2.api.costShown({text:"–"}, false), "–");
  console.log("kosten.test.cjs: ok");
})().catch(e => { console.error(e); process.exit(1); });
