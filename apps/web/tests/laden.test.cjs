// Verbinden mit einem Repository ohne Bücherregal (#729, #731): verständliche Meldung statt „Not Found“, kein Eintrag im Fehlerprotokoll. Aufruf: node apps/web/tests/laden.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname, "..", "..", "shared", "s07-laden.js"), "utf8");

function run(git){
  const logged = [], shown = [];
  const ctx = {S:{files:new Map(), msg:null}, store:{set(){}}, busy(){}, esc:s => String(s), show:v => shown.push(v), openBook(){}, getFile:(p) => git.getFile(p),
    errText:e => { logged.push(e); return "ERR:" + (e && e.code); }, GW_PORTS:{git}, JSON, Promise, Map, Object, String, Array};
  vm.runInNewContext(src + "\n;this.__loadRepo = loadRepo;", ctx);
  return ctx.__loadRepo("ploeffler/GhostWriter").then(() => ({ctx, logged, shown}));
}
const nf = {code:"http_404", status:404, message:"Not Found"};

(async () => {
  // Repository erreichbar, aber ohne library.json und ghostwriter-index.json: Hinweis, kein Fehlerprotokoll
  let r = await run({getFile: async () => { throw nf; }, listDir: async () => []});
  assert.match(r.ctx.S.msg.html, /weder ein Bücherregal.*noch ein Buch/s); assert.deepEqual(r.logged, []); assert.deepEqual(r.shown, ["connect"]);
  // Repository nicht sichtbar: Wurzel liefert ebenfalls 404 – Hinweis auf Zugriff, kein Fehlerprotokoll
  r = await run({getFile: async () => { throw nf; }, listDir: async () => { throw nf; }});
  assert.match(r.ctx.S.msg.html, /nicht gefunden – oder der Token hat dafür keinen Zugriff/); assert.deepEqual(r.logged, []);
  // andere Fehler gehen unverändert durch errText (und damit ins Protokoll)
  r = await run({getFile: async () => { throw {code:"http_401", status:401, message:"Bad credentials"}; }, listDir: async () => []});
  assert.equal(r.ctx.S.msg.html, "ERR:http_401");
  r = await run({getFile: async () => { throw nf; }, listDir: async () => { throw {code:"offline", message:"x"}; }});
  assert.equal(r.ctx.S.msg.html, "ERR:offline");
  console.log("laden.test.cjs: ok");
})().catch(e => { console.error(e); process.exit(1); });
