// „Frühere Prüfungen“: ein früherer Befund, den eine spätere Prüfung derselben Art im selben Bereich ersetzt, wird so gekennzeichnet (wie scripts/checks.py). Aufruf: node apps/web/tests/pruefprotokoll.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const read = f => fs.readFileSync(path.join(__dirname, "..", "..", "shared", f), "utf8");
const secs = ["s1", "s2", "s3"], ctx = {
  S:{checks:[]}, allSecs: () => secs.map(id => ({c:{id:"c1"}, s:{id}})), cached: () => ({dg:"x"}), ANA:{}, ANA_SHORT:{}, Date, JSON, Array, Set, Object, String, Number, Math, Promise
};
vm.runInNewContext(read("s01-kern.js").split("const S = ")[0].replace(/^const GH.*$/m, "") + "\nconst rankOf = (e, i) => whenOf(e) + \"|\" + String(i).padStart(6, \"0\");\n" + read("s04-pruefprotokoll.js") + "\n;this.__x = {historyFor, tagsFor, supersededBy};", ctx);
const X = ctx.__x, e = (id, kind, result, time, scope, note) => ({id, kind, result, date:"2026-11-20", time, scope, note, digests:{s1:"x", s2:"x", s3:"x"}});
// ganzes Kapitel: ✗ 17:10, danach ✓ 17:54 → das ✗ ist ersetzt
ctx.S.checks = [e("pr-1", "language", "failed", "17:10", ["c1"], "Nachprüfung offen"), e("pr-2", "language", "passed", "17:54", ["c1"])];
let h = X.historyFor(secs);
assert.equal(h.length, 1); assert.equal(h[0].CK_SUPERSEDED, "2026-11-20 17:54 ✓");
assert.equal(h[0].CK_NOTE, "ersetzt durch spätere Prüfung 2026-11-20 17:54 ✓ · Nachprüfung offen");
// nur ein Abschnitt nachgeprüft: für das Kapitel nicht ersetzt, für diesen Abschnitt schon
ctx.S.checks = [e("pr-1", "language", "failed", "17:10", ["c1"]), e("pr-2", "language", "passed", "17:54", ["s1"])];
assert.equal(X.historyFor(secs)[0].CK_SUPERSEDED, ""); assert.equal(X.historyFor(secs)[0].CK_NOTE, "");
assert.equal(X.historyFor(["s1"])[0].CK_SUPERSEDED, "2026-11-20 17:54 ✓");
// andere Prüfart ersetzt nichts
ctx.S.checks = [e("pr-1", "language", "failed", "17:10", ["c1"]), e("pr-2", "structure", "passed", "17:54", ["c1"]), e("pr-3", "language", "passed_with_notes", "18:00", ["c1"])];
h = X.historyFor(secs); assert.equal(h.length, 1); assert.equal(h[0].CK_SUPERSEDED, "2026-11-20 18:00 ✓·");
console.log("pruefprotokoll ok");
