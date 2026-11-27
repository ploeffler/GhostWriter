// Sprachnotizen der Web-App (#644, #662): lokal aufnehmen und verwalten, nie hochladen. Aufruf: node apps/web/tests/voice.test.cjs
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname, "..", "voice-web.js"), "utf8");

function load(opts){
  opts = opts || {};
  const html = {app:{innerHTML:""}, voicetime:{textContent:""}}, listeners = {}, fetches = [], saved = [];
  class MR { constructor(stream, o){ this.o = o || {}; this.mimeType = opts.mime || "audio/webm;codecs=opus"; MR.last = this; } start(){ this.started = true; } stop(){ if (opts.data !== false && this.ondataavailable) this.ondataavailable({data:new Blob([new Uint8Array(opts.size || 2048)])}); setTimeout(() => this.onstop && this.onstop(), 0); } static isTypeSupported(t){ return /webm/.test(t); } }
  const tracks = [{stop(){ tracks.stopped = (tracks.stopped || 0) + 1; }}];
  const ctx = {
    S:{owner:"o", repo:"r", book:{branch:"b", title:"Das Buch", title_short:"Buch"}, chap:1, sec:{path:"x"}, secNo:"2.5", view:"voice", msg:null}, $: id => html[id] || null, esc: String, crumbs(){}, msgBox: () => "", show(){}, fmtTime: () => "t", fmtBytes: n => n + " B",
    MediaRecorder: MR, Blob, URL: {createObjectURL: () => "blob:x", revokeObjectURL(){}}, setTimeout, clearTimeout, setInterval, clearInterval, Date, JSON, Array, Object, String, Number, Math, Promise, Uint8Array,
    navigator: {mediaDevices: opts.noMic ? undefined : {getUserMedia: async () => { if (opts.deny) { const e = new Error("x"); e.name = "NotAllowedError"; throw e; } return {getTracks: () => tracks}; }}, storage:{estimate: async () => ({quota:1e9, usage:1e6}), persist: async () => true}},
    document: {addEventListener: (t, f) => { listeners[t] = f; }, querySelector: () => null, createElement: () => ({click(){ saved.push("click"); }, remove(){}}), body:{appendChild(){}}}, window: {addEventListener: (t, f) => { listeners[t] = listeners[t] || f; }, scrollTo(){}},
    GW_PORTS:{}, confirm: () => true, obRender: async () => {}
  };
  vm.runInNewContext(src + "\n;this.__x = {VS, VOICE, voiceName, voiceContext, voiceCount, voiceStart, voiceStop, voiceView, voiceDur, voiceCan, voiceExt, VOICE_MAX};", ctx);
  return {ctx, x: ctx.__x, html, MR, tracks, listeners};
}
(async () => {
  let t = load(); const X = t.x;
  // Kontext: wo wurde aufgenommen
  assert.deepEqual(JSON.parse(JSON.stringify(X.voiceContext())), {repo:"o/r", book:"Buch", label:"Abschnitt 2.5"});
  t.ctx.S.sec = null; assert.equal(X.voiceContext().label, "Kapitel 2"); t.ctx.S.chap = null; assert.equal(X.voiceContext().label, "ganzes Buch"); t.ctx.S.book = null; assert.equal(X.voiceContext().label, "ohne Zuordnung");
  t.ctx.S.book = {branch:"b", title:"Das Buch"}; t.ctx.S.chap = 1; t.ctx.S.sec = {path:"x"};
  // Dateiname und Dauer
  assert.equal(X.voiceName({created:new Date(2026, 10, 27, 9, 5).getTime(), mime:"audio/webm;codecs=opus", ctx:{label:"Abschnitt 2.5"}}), "sprachnotiz-2026-11-27-0905-abschnitt-2-5.webm");
  assert.equal(X.voiceName({created:new Date(2026, 10, 27, 9, 5).getTime(), mime:"audio/mp4", ctx:{label:"ohne Zuordnung"}}), "sprachnotiz-2026-11-27-0905.m4a");
  assert.equal(X.voiceDur(125000), "2:05");
  // Aufnahme starten und beenden: lokal gespeichert, Mikrofon wird freigegeben, kein Netzzugriff
  assert.equal(X.voiceCan(), true);
  await X.voiceStart(); assert(t.MR.last.started); assert.equal(t.MR.last.o.audioBitsPerSecond, 32000);
  await X.voiceStop();
  const all = await X.VS.all(); assert.equal(all.length, 1); assert.equal(all[0].state, "wartet"); assert.equal(all[0].ctx.label, "Abschnitt 2.5"); assert(all[0].size > 0); assert.equal(all[0].mime, "audio/webm;codecs=opus");
  assert.equal(t.tracks.stopped, 1, "Mikrofon freigegeben"); assert.equal(X.VOICE.rec, null);
  assert.equal(await X.voiceCount(), 1); all[0].state = "abgeschrieben"; await X.VS.put(all[0]); assert.equal(await X.voiceCount(), 0);
  await X.voiceView();
  assert.match(t.html.app.innerHTML, /im Chat abgeschrieben/); assert.match(t.html.app.innerHTML, /Herunterladen/); assert.match(t.html.app.innerHTML, /Verwerfen/);
  assert.doesNotMatch(src, /fetch\(|XMLHttpRequest|sendBeacon|api\.github|\/dispatches/, "Audio geht nie ins Netz");
  // Leere Aufnahme wird nicht gespeichert
  t = load({data:false}); await t.x.voiceStart(); await t.x.voiceStop(); assert.equal((await t.x.VS.all()).length, 0); assert.match(t.ctx.S.msg.html, /leer/);
  // Mikrofon verweigert / fehlt
  t = load({deny:true}); await t.x.voiceStart(); assert.match(t.ctx.S.msg.html, /nicht freigegeben/); assert.equal(t.x.VOICE.rec, null);
  t = load({noMic:true}); assert.equal(t.x.voiceCan(), false); await t.x.voiceStart(); assert.match(t.ctx.S.msg.html, /keine Aufnahme möglich/);
  // Unbekannter Typ: Rückfall ohne mimeType
  t = load({mime:"audio/mp4"}); await t.x.voiceStart(); await t.x.voiceStop(); assert.equal((await t.x.VS.all())[0].mime, "audio/mp4");
  // Höchstdauer ist festgelegt
  assert.equal(t.x.VOICE_MAX, 30 * 60 * 1000);
  console.log("voice ok");
})().catch(e => { console.error(e); process.exit(1); });
