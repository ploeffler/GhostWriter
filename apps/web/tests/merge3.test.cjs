// Dreiwege-Vergleich je Absatz (#662): Zusammenführen ohne Überschneidung, Konflikt nur bei gleichem Bereich. Aufruf: node apps/web/tests/merge3.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const ctx = {String, Array, Map, Int32Array, Error, Math};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "..", "merge3.js"), "utf8") + "\n;this.__x = {merge3, m3Join, m3Conflicts};", ctx);
const {merge3, m3Join, m3Conflicts} = ctx.__x, P = (...a) => a.join("\n\n"), plain = v => JSON.parse(JSON.stringify(v));

const base = P("Kopf", "Absatz A", "Absatz B", "Absatz C", "Schluss");
// verschiedene Absätze geändert: beides übernehmen
let m = merge3(base, P("Kopf", "Absatz A neu", "Absatz B", "Absatz C", "Schluss"), P("Kopf", "Absatz A", "Absatz B", "Absatz C neu", "Schluss"));
assert.equal(m3Conflicts(m), 0); assert.equal(m3Join(m, []), P("Kopf", "Absatz A neu", "Absatz B", "Absatz C neu", "Schluss"));
// nur eine Seite geändert
assert.equal(m3Join(merge3(base, base, P("Kopf", "Absatz A", "Absatz B x", "Absatz C", "Schluss")), []), P("Kopf", "Absatz A", "Absatz B x", "Absatz C", "Schluss"));
assert.equal(m3Join(merge3(base, P("Kopf", "Absatz A", "Absatz B", "Absatz C", "Schluss", "Neu am Ende"), base), []), P("Kopf", "Absatz A", "Absatz B", "Absatz C", "Schluss", "Neu am Ende"));
// beide dasselbe: einmal
const same = P("Kopf", "Absatz A!", "Absatz B", "Absatz C", "Schluss");
assert.equal(m3Conflicts(merge3(base, same, same)), 0); assert.equal(m3Join(merge3(base, same, same), []), same);
// Einfügen an verschiedenen Stellen, Löschen auf einer Seite
m = merge3(base, P("Kopf", "Vorn neu", "Absatz A", "Absatz B", "Absatz C", "Schluss"), P("Kopf", "Absatz A", "Absatz B", "Schluss"));
assert.equal(m3Conflicts(m), 0); assert.equal(m3Join(m, []), P("Kopf", "Vorn neu", "Absatz A", "Absatz B", "Schluss"));
// gleicher Absatz verschieden: Konflikt mit allen drei Fassungen
m = merge3(base, P("Kopf", "Absatz A", "B lokal", "Absatz C", "Schluss"), P("Kopf", "Absatz A", "B remote", "Absatz C", "Schluss"));
assert.equal(m3Conflicts(m), 1); const c = plain(m.find(x => typeof x !== "string").conflict);
assert.deepEqual(c, {base:["Absatz B"], local:["B lokal"], remote:["B remote"]});
assert.equal(m3Join(m, ["local"]), P("Kopf", "Absatz A", "B lokal", "Absatz C", "Schluss"));
assert.equal(m3Join(m, ["remote"]), P("Kopf", "Absatz A", "B remote", "Absatz C", "Schluss"));
assert.equal(m3Join(m, ["both"]), P("Kopf", "Absatz A", "[KONFLIKT PRÜFEN: Fassung von diesem Gerät]", "B lokal", "[KONFLIKT PRÜFEN: Fassung von GitHub]", "B remote", "Absatz C", "Schluss"));
assert.equal(m3Join(m, ["Von Hand zusammengefügt"]), P("Kopf", "Absatz A", "Von Hand zusammengefügt", "Absatz C", "Schluss"));
assert.throws(() => m3Join(m, []), /nicht entschieden/);
// ein Absatz auf einer Seite gelöscht, auf der anderen geändert: Konflikt
m = merge3(base, P("Kopf", "Absatz A", "Absatz C", "Schluss"), P("Kopf", "Absatz A", "B geändert", "Absatz C", "Schluss"));
assert.equal(m3Conflicts(m), 1);
// Änderungen in benachbarten Absätzen gelten als eine Stelle (wie bei Zeilen in git): Konflikt
assert.equal(m3Conflicts(merge3(base, P("Kopf", "A neu", "Absatz B", "Absatz C", "Schluss"), P("Kopf", "Absatz A", "B neu", "Absatz C", "Schluss"))), 1);
// zwei getrennte Konflikte
m = merge3(base, P("Kopf", "A1", "Absatz B", "C1", "Schluss"), P("Kopf", "A2", "Absatz B", "C2", "Schluss"));
assert.equal(m3Conflicts(m), 2); assert.equal(m3Join(m, ["local", "remote"]), P("Kopf", "A1", "Absatz B", "C2", "Schluss"));
// Text bleibt unverändert, wenn nichts geändert ist (auch mit mehreren Leerzeilen und Zeilenende)
const odd = "---\nstatus: writing\n---\n\n## Manuskript\n\nText\n\n\nNoch ein Absatz\n";
assert.equal(m3Join(merge3(odd, odd, odd), []), odd);
console.log("merge3 ok");
