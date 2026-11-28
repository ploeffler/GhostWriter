// Bücherregal der Web-App: Links zu Auflagen und Vorabfassungen je Buch. Aufruf: node apps/web/tests/regal.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname, "..", "regal-web.js"), "utf8");
const ctx = {S:{owner:"o", repo:"r", lib:{books:[]}}, GW_PORTS:{}, store:{get(){}, set(){}}, esc:String, deDate:iso => { const m = /(\d{4})-(\d{2})-(\d{2})/.exec(iso || ""); return m ? `${m[3]}.${m[2]}.${m[1]}` : ""; },
  runRelOfBook:(r, b) => (r.tag || "").startsWith(b.branch.replace("buch/", "") + "-"), document:{}, Set, Array, JSON, String, Promise, encodeURIComponent};
vm.runInNewContext(src + "\n;this.__x = {regalLinks};", ctx);
const book = {branch:"buch/malta", editions:[{number:1, date:"2026-11-20", tag:"malta-auflage-1"}, {number:2}]};
const rels = [{tag:"malta-vorab-3", name:"Malta Vorabfassung 3", pre:true, date:"2026-11-26T10:00:00Z", url:"https://x/vorab3"},
  {tag:"malta-auflage-1", name:"Auflage 1", pre:false, date:"2026-11-20T10:00:00Z", url:"https://x/a1"}, {tag:"anderes-vorab-1", name:"Anderes", pre:true, date:"2026-11-25T10:00:00Z", url:"https://x/o"}];
let l = ctx.__x.regalLinks(book, null);
assert.deepEqual(l.map(x => x.text), ["Auflage 1", "Auflage 2"]);
assert.equal(l[0].url, "https://github.com/o/r/releases/tag/malta-auflage-1"); assert.equal(l[0].date, "20.11.2026"); assert.equal(l[1].url, "");   // ohne Tag kein Link
l = ctx.__x.regalLinks(book, rels);
assert.deepEqual(l.map(x => x.text), ["Auflage 1", "Auflage 2", "Malta Vorabfassung 3 (Vorabfassung)"]);   // nur Pre-Releases dieses Buchs, Auflage nicht doppelt
assert.equal(l[2].url, "https://x/vorab3"); assert.equal(l[2].date, "26.11.2026");
assert.equal(ctx.__x.regalLinks({branch:"buch/leer"}, rels).length, 0);

const dataSrc = fs.readFileSync(path.join(__dirname, "..", "..", "shared", "s05-daten-vorlagen.js"), "utf8");
const dataCtx = {S:{owner:"o", repo:"r", lib:{books:[
  {branch:"buch/a", title:"A"}, {branch:"buch/b", title:"B"},
  {branch:"buch/solo", title:"Einzelbuch"}, {branch:"buch/a", title:"A doppelt"}
], series:[
  {id:"serie-1", title:"Serie 1", volumes:["buch/a", "buch/b"]},
  {id:"serie-2", title:"Serie 2", volumes:["buch/b"]}
]}}, plural:(n, one, many) => `${n} ${n === 1 ? one : many}`, deDate:() => "", Map, Set, Array, Math, JSON, String};
vm.runInNewContext(dataSrc + "\\n;this.__libraryData = libraryData;", dataCtx);
const library = dataCtx.__libraryData();
assert.deepEqual(Array.from(library.BOOKS, row => [row.BOOK_BRANCH, row.BOOK_SERIES]), [
  ["buch/a", "serie-1"], ["buch/b", "serie-1"], ["buch/solo", ""]
]);
assert.equal(library.BOOK_COUNT_TEXT, "3 Bücher · 2 Serien");

console.log("regal ok");
