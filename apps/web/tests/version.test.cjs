// Versionsanzeige im Kopf (#735). Aufruf: node apps/web/tests/version.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname, "..", "version-web.js"), "utf8");
const el = {textContent:"", title:"", classList:{on:false, toggle(c, v){ this.on = v; }}};
const ctx = {S:{owner:"", repo:""}, APP_VERSION:"1.6.0", $: id => id === "vers" ? el : null, setInterval(){}, document:{addEventListener(){}}, GW_PORTS:{git:{getFile: async () => ({text:"# x\nversion: 1.5.0\n"})}}};
vm.createContext(ctx); vm.runInContext(src + "\nthis.api = {verParse, verText, verLoad, VER};", ctx);
const A = ctx.api;
assert.equal(A.verParse("a: 1\nversion: 1.5.0\n"), "1.5.0"); assert.equal(A.verParse("version: \"2.0.1\""), "2.0.1"); assert.equal(A.verParse("nix"), null); assert.equal(A.verParse(""), null);
assert.equal(A.verText("1.6.0", null, "").text, "App 1.6.0");
assert.match(A.verText("1.6.0", null, "o/r").text, /Repository \?/);
const same = A.verText("1.5.1", "1.5.0", "o/r"); assert.equal(same.warn, false);
const diff = A.verText("1.6.0", "1.5.0", "o/r"); assert.equal(diff.warn, true); assert.match(diff.title, /weichen ab/);
(async () => {
  ctx.S.owner = "o"; ctx.S.repo = "r"; await A.verLoad();
  assert.equal(el.textContent, "App 1.6.0 · Repository 1.5.0"); assert.equal(el.classList.on, true);
  ctx.GW_PORTS.git.getFile = async () => { throw new Error("offline"); }; await A.verLoad();
  assert.match(el.textContent, /Repository \?/);
  ctx.S.owner = ""; await A.verLoad(); assert.equal(el.textContent, "App 1.6.0");
  console.log("version.test.cjs: ok");
})();
