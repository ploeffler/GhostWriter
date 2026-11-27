// Rollen je Buch in der App (#762): gleiche Fälle wie die Python-Fassung. Aufruf: node apps/web/tests/rollen.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname, "..", "..", "shared", "s19-rollen.js"), "utf8");
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "..", "tests", "data", "rollen_faelle.json"), "utf8")).cases;
const ctx = {S:{}, esc:String, Array, String, Object, Promise, JSON}; vm.createContext(ctx);
vm.runInContext(src + "\nthis.api = {teamRole, roleWhy, roleNote, needWrite, loadRole};", ctx);
const api = ctx.api, plain = o => JSON.parse(JSON.stringify(o));
for (const c of cases){
  const r = api.teamRole(c.team ? {team:c.team} : {}, c.login, c.push);
  for (const [k, v] of Object.entries(c.expect)) assert.deepEqual(plain(r[k]), v, c.name + ": " + k);
}
// Knöpfe je Rolle
const role = n => { const c = cases.find(x => x.name.startsWith(n)); ctx.S.role = api.teamRole(c.team ? {team:c.team} : {}, c.login, c.push); return ctx.S.role; };
role("Leser"); assert.match(api.roleWhy("section.update"), /Leserechte/); assert.match(api.roleWhy("approval.confirm"), /Leserechte/); assert.equal(api.roleWhy("view.project"), ""); assert.equal(api.roleWhy("view.section"), "");
assert.throws(() => api.needWrite(), e => /nicht gespeichert/.test(e.message)); assert.match(api.roleNote(), /Leser.*nur lesen/s);
role("Bearbeiter ohne approve"); assert.equal(api.roleWhy("section.update"), ""); assert.match(api.roleWhy("approval.confirm"), /Freigabeberechtigte: anna/); assert.match(api.roleWhy("edition.create"), /Freigabeberechtigte/);
assert.doesNotThrow(() => api.needWrite()); assert.match(api.roleNote(), /schreiben, nicht abschließen/);
role("Bearbeiter mit approve"); assert.equal(api.roleWhy("approval.confirm"), ""); assert.equal(api.roleNote().includes("Freigabeberechtigte"), false);
role("Bearbeiter ohne GitHub"); assert.match(api.roleWhy("section.update"), /kein Schreibrecht/);
role("ohne team: Schreibrecht"); assert.equal(api.roleWhy("approval.confirm"), ""); assert.equal(api.roleNote(), "");   // ohne Team nichts anzeigen
ctx.S.role = null; assert.equal(api.roleWhy("section.update"), "");
console.log("rollen.test.cjs: ok");
