/* ---------- Sprachnotizen (#644, #662) ----------
   Aufnahme im Browser (MediaRecorder), lokal gespeichert (IndexedDB), nie hochgeladen: Audio kommt nie ins Repository und nie in einen Actions-Lauf; Spracherkennung läuft nie
   als Action (Beschluss Peter, 25.11.2026). Eine App-Aufnahme ist die einzige Kopie: Sie bleibt hier, bis sie im Chat abgeschrieben ist und du entscheidest, ob du sie aufs Gerät
   lädst oder verwirfst. Der Hinweis „N Sprachnotizen warten auf Abschrift“ steht in der Leiste oben. Zum Diktieren in Textfelder reicht das Mikrofon der Handy-Tastatur (läuft auf dem Gerät).
   Eine Notiz: {id, created, duration (ms), mime, size, blob, ctx:{repo, book, label}, state:"wartet"|"abgeschrieben"}. */
const VOICE_MAX = 30 * 60 * 1000;          // höchstens 30 Minuten je Aufnahme (Opus ≈ 4 MB), danach stoppt die Aufnahme von selbst
const VOICE = {rec:null, stream:null, chunks:[], t0:0, ticker:0, ctx:null, mime:"", busy:false};
function voiceStore(){
  if (typeof indexedDB === "undefined"){
    const m = new Map(); let n = 0;
    return {mem:true, all:async () => [...m.values()].sort((a, b) => a.id - b.id), put:async e => { if (!e.id) e.id = ++n; m.set(e.id, e); return e.id; }, del:async id => { m.delete(id); }};
  }
  const db = new Promise((ok, no) => { const r = indexedDB.open("gw-web-voice", 1); r.onupgradeneeded = () => r.result.createObjectStore("voice", {keyPath:"id", autoIncrement:true}); r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });
  const run = (mode, fn) => db.then(d => new Promise((ok, no) => { const t = d.transaction("voice", mode), q = fn(t.objectStore("voice")); t.oncomplete = () => ok(q && q.result); t.onerror = () => no(t.error); t.onabort = () => no(t.error); }));
  return {mem:false, all:() => run("readonly", s => s.getAll()).then(a => (a || []).sort((x, y) => x.id - y.id)), put:e => run("readwrite", s => s.put(e)), del:id => run("readwrite", s => s.delete(id))};
}
const VS = voiceStore();
const voiceCan = () => typeof MediaRecorder !== "undefined" && !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
function voiceMime(){
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) return "";
  return ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"].find(t => MediaRecorder.isTypeSupported(t)) || "";
}
function voiceContext(){   // wo wurde aufgenommen: Vorschlag für die spätere Zuordnung (Anekdote, Abschnittsnotiz, Material, Recherchefrage)
  const repo = S.owner ? S.owner + "/" + S.repo : "", book = S.book ? (S.book.title_short || S.book.title || S.book.branch) : "";
  let label = "ohne Zuordnung";
  if (S.book && S.sec && S.secNo) label = `Abschnitt ${S.secNo}`; else if (S.book && S.chap != null && S.chap >= 0) label = `Kapitel ${S.chap + 1}`; else if (S.book) label = "ganzes Buch";
  return {repo, book, label};
}
const voiceExt = mime => /mp4/.test(mime) ? "m4a" : /ogg/.test(mime) ? "ogg" : "webm";
const voicePad = n => String(n).padStart(2, "0");
function voiceName(n){
  const d = new Date(n.created), stamp = `${d.getFullYear()}-${voicePad(d.getMonth() + 1)}-${voicePad(d.getDate())}-${voicePad(d.getHours())}${voicePad(d.getMinutes())}`;
  const where = String((n.ctx && n.ctx.label) || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return `sprachnotiz-${stamp}${where && where !== "ohne-zuordnung" ? "-" + where : ""}.${voiceExt(n.mime)}`;
}
const voiceDur = ms => { const s = Math.round(ms / 1000); return `${Math.floor(s / 60)}:${voicePad(s % 60)}`; };
async function voiceCount(){ try { return (await VS.all()).filter(n => n.state !== "abgeschrieben").length; } catch (e) { return 0; } }
async function voiceStart(){
  if (VOICE.rec || VOICE.busy) return;
  if (!voiceCan()){ S.msg = {kind:"err", html:"In diesem Browser ist keine Aufnahme möglich (Mikrofon oder Aufnahme fehlt)."}; return voiceView(); }
  VOICE.busy = true;
  try {
    VOICE.stream = await navigator.mediaDevices.getUserMedia({audio:true});
    VOICE.mime = voiceMime(); VOICE.chunks = []; VOICE.ctx = voiceContext();
    VOICE.rec = new MediaRecorder(VOICE.stream, VOICE.mime ? {mimeType:VOICE.mime, audioBitsPerSecond:32000} : {audioBitsPerSecond:32000});
    VOICE.rec.ondataavailable = e => { if (e.data && e.data.size) VOICE.chunks.push(e.data); };
    VOICE.rec.start(1000); VOICE.t0 = Date.now();
    VOICE.ticker = setInterval(() => { voiceTick(); if (Date.now() - VOICE.t0 >= VOICE_MAX) voiceStop(); }, 500);
  } catch (e) {
    const denied = e && (e.name === "NotAllowedError" || e.name === "SecurityError"), none = e && e.name === "NotFoundError";
    S.msg = {kind:"err", html:esc(denied ? "Das Mikrofon ist nicht freigegeben. Erlaube es in den Einstellungen des Browsers für diese Seite." : none ? "Es wurde kein Mikrofon gefunden." : "Die Aufnahme konnte nicht gestartet werden.")};
    voiceRelease();
  }
  VOICE.busy = false; if (S.view === "voice") voiceView();
}
function voiceRelease(){ try { (VOICE.stream ? VOICE.stream.getTracks() : []).forEach(t => t.stop()); } catch (e) {} VOICE.stream = null; VOICE.rec = null; clearInterval(VOICE.ticker); VOICE.ticker = 0; }
function voiceTick(){ const el = $("voicetime"); if (el) el.textContent = voiceDur(Date.now() - VOICE.t0); }
async function voiceStop(){
  const rec = VOICE.rec; if (!rec) return;
  const done = new Promise(ok => { rec.onstop = ok; });
  try { rec.stop(); } catch (e) {}
  await done;
  const dur = Date.now() - VOICE.t0, mime = rec.mimeType || VOICE.mime || "audio/webm", blob = new Blob(VOICE.chunks, {type:mime}), ctx = VOICE.ctx;
  voiceRelease(); VOICE.chunks = [];
  if (!blob.size){ S.msg = {kind:"warn", html:"Die Aufnahme war leer und wurde nicht gespeichert."}; return voiceView(); }
  try {
    await VS.put({created:VOICE.t0, duration:dur, mime, size:blob.size, blob, ctx, state:"wartet"});
    try { if (navigator.storage && navigator.storage.persist) navigator.storage.persist(); } catch (e) {}
    S.msg = {kind:"ok", html:`<b>Aufnahme gespeichert</b> (${voiceDur(dur)}, nur auf diesem Gerät). Zum Abschreiben: Datei laden und im Chat mit GhostWriter hochladen.`};
  } catch (e) { S.msg = {kind:"err", html:esc("Die Aufnahme konnte nicht gespeichert werden (Speicher voll?). Lade sie sofort herunter, bevor du weitermachst: " + (e && e.message || e))}; VOICE.rescue = {blob, name:voiceName({created:VOICE.t0, mime, ctx})}; }
  if (typeof obRender === "function") await obRender();
  if (S.view === "voice") voiceView();
}
async function voiceView(){
  if (!VOICE.back || S.view !== "voice") VOICE.back = {view:S.view || "connect", arg:S.view === "section" ? S.sec && S.sec.id : S.chap};
  S.view = "voice"; crumbs();
  const notes = (await VS.all().catch(() => [])).slice().reverse(), ctx = voiceContext(), recording = !!VOICE.rec, can = voiceCan();
  let free = ""; try { const e = await navigator.storage.estimate(); const f = (e.quota - (e.usage || 0)); free = f < 100 * 1048576 ? ` <b>Wenig Speicher frei (${fmtBytes(f)}).</b>` : ""; } catch (e) {}
  const rec = recording ? `<div style="display:flex;align-items:center;gap:12px"><span style="color:#c0392b;font-size:22px">●</span><b id="voicetime" style="font-size:22px">${voiceDur(Date.now() - VOICE.t0)}</b><button class="btn pri" data-voice="stop">Aufnahme beenden und speichern</button></div><div class="dim" style="margin-top:6px">Aufgenommen wird für: ${esc(VOICE.ctx.label)}${VOICE.ctx.book ? " (" + esc(VOICE.ctx.book) + ")" : ""}. Höchstens ${VOICE_MAX / 60000} Minuten.</div>`
    : `<button class="btn pri" data-voice="start" ${can ? "" : "disabled title='braucht Mikrofon und Aufnahme im Browser'"}>● Aufnahme starten</button> <span class="dim">für: ${esc(ctx.label)}${ctx.book ? " (" + esc(ctx.book) + ")" : ""}</span>${can ? "" : '<div class="dim">Dieser Browser kann nicht aufnehmen (braucht Mikrofon und Aufnahme).</div>'}${free}`;
  const rescue = VOICE.rescue ? `<div class="note err"><b>Nicht gespeichert.</b> <button class="link" data-voice="rescue">Aufnahme jetzt herunterladen</button></div>` : "";
  const list = notes.length ? `<table class="kv">${notes.map(n => `<tr><td>${esc(fmtTime(n.created))}<div class="dim">${voiceDur(n.duration)} · ${fmtBytes(n.size)} · ${esc((n.ctx && n.ctx.label) || "")}${n.ctx && n.ctx.book ? " · " + esc(n.ctx.book) : ""}</div></td>
    <td>${n.state === "abgeschrieben" ? '<span class="dim">im Chat abgeschrieben</span>' : '<b>wartet auf Abschrift</b>'}<div><audio controls preload="none" data-voice-audio="${n.id}" style="max-width:260px;height:32px"></audio></div></td>
    <td style="white-space:nowrap"><button class="btn" data-voice="download" data-id="${n.id}">Herunterladen</button> ${n.state === "abgeschrieben" ? "" : `<button class="btn" data-voice="done" data-id="${n.id}">Im Chat abgeschrieben</button> `}<button class="btn" data-voice="discard" data-id="${n.id}">Verwerfen</button></td></tr>`).join("")}</table>` : '<p class="dim">Noch keine Sprachnotizen.</p>';
  $("app").innerHTML = `<div class="one"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><b style="font-size:20px">Sprachnotizen</b><button class="btn" data-act="voice-back">Zurück</button></div>${msgBox()}${rescue}
    <section class="card"><b>Aufnehmen</b><p class="dim" style="margin:6px 0">Die Aufnahme bleibt <b>nur auf diesem Gerät</b>. Sie wird nicht hochgeladen und nicht ins Buch gelegt; im Buch landet erst die Abschrift, die du im Chat mit GhostWriter erstellst. Zum Diktieren in ein Textfeld genügt das Mikrofon deiner Handy-Tastatur.</p>${rec}</section>
    <section class="card"><b>Aufnahmen auf diesem Gerät</b><p class="dim" style="margin:6px 0">Zum Abschreiben: <b>Herunterladen</b>, die Datei im Chat mit GhostWriter hochladen („Sprachnotiz“), danach hier <b>Im Chat abgeschrieben</b> wählen. Die Aufnahme bleibt dann weiter hier, bis du sie herunterlädst oder verwirfst; es gibt keine zweite Kopie.</p>${list}</section></div>`;
  notes.forEach(n => { const a = document.querySelector(`[data-voice-audio="${n.id}"]`); if (a) a.src = URL.createObjectURL(n.blob); });
  window.scrollTo(0, 0);
}
function voiceSave(blob, name){ const u = URL.createObjectURL(blob), a = document.createElement("a"); a.href = u; a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 10000); }
GW_PORTS.views = Object.assign(GW_PORTS.views || {}, {voice:voiceView});
document.addEventListener("click", async ev => {
  const m = ev.target.closest && ev.target.closest("#micbtn"); if (m){ ev.preventDefault(); return voiceView(); }
  const a = ev.target.closest && ev.target.closest("[data-act]");
  if (a && a.dataset.act === "voice-back"){ ev.preventDefault(); if (VOICE.rec && !confirm("Die Aufnahme läuft noch. Beenden und speichern?")) return; if (VOICE.rec) await voiceStop(); const k = VOICE.back || {view:"connect"}; VOICE.back = null; return show(k.view, k.arg); }
  if (a && a.dataset.act === "voice-open"){ ev.preventDefault(); return voiceView(); }
  const b = ev.target.closest && ev.target.closest("[data-voice]"); if (!b) return;
  ev.preventDefault(); const k = b.dataset.voice, id = Number(b.dataset.id), all = await VS.all().catch(() => []), n = all.find(x => x.id === id);
  if (k === "start") return voiceStart();
  if (k === "stop") return voiceStop();
  if (k === "rescue" && VOICE.rescue){ voiceSave(VOICE.rescue.blob, VOICE.rescue.name); return; }
  if (!n) return;
  if (k === "download") return voiceSave(n.blob, voiceName(n));
  if (k === "done"){ n.state = "abgeschrieben"; await VS.put(n); S.msg = {kind:"ok", html:"Als abgeschrieben vermerkt. Die Aufnahme bleibt auf diesem Gerät, bis du sie herunterlädst oder verwirfst."}; if (typeof obRender === "function") await obRender(); return voiceView(); }
  if (k === "discard"){
    const warn = n.state === "abgeschrieben" ? "Diese Aufnahme verwerfen? Es gibt keine zweite Kopie." : "Diese Aufnahme ist noch NICHT abgeschrieben und es gibt keine zweite Kopie. Wirklich verwerfen?";
    if (!confirm(warn)) return; await VS.del(n.id); S.msg = null; if (typeof obRender === "function") await obRender(); return voiceView();
  }
});
window.addEventListener("beforeunload", ev => { if (VOICE.rec){ ev.preventDefault(); ev.returnValue = ""; } });
