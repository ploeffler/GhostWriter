/* ---------- Modell im Browser (#525, #662) ----------
   Ein Sprachmodell läuft auf diesem Gerät (WebGPU, Transformers.js). Nichts davon läuft ohne ausdrücklichen Klick: Laufzeit (Skript von cdn.jsdelivr.net) und Gewichte
   (huggingface.co) werden erst nach „Herunterladen“ geladen und bleiben im Cache dieses Browsers; Buchtext verlässt das Gerät nie. Die KI schlägt nur vor: Es wird nichts
   automatisch gespeichert, ein Vorschlag wird erst nach eigenem Klick übernommen (Kopieren). Die Liste steht in modelle.json (Format wie faehigkeiten.json). */
const MDL = {list:null, rt:null, loaded:null, pipe:null, busy:false, progress:{}, abort:null, msg:null, probe:{}, chat:[], back:null};
const MDL_KEY = "gw.model", MDL_DONE = "gw.model.done.", MDL_RUN = "gw.model.run", MDL_PHASE = "gw.model.phase", MDL_CRASH = "gw.model.crashes.";   // fertig geladen (je Modell) / Download läuft (Marke gegen Unterbrechung, #758) / Phase und Absturzzähler (#774)
const MDL_TASKS = {
  lektorat: {de:"Lektorat", sys:"Du bist ein sorgfältiger Lektor. Verbessere Rechtschreibung, Grammatik und Ausdruck des Textes. Erhalte Inhalt, Handlung, Ton und Erzählstimme. Erfinde nichts dazu. Antworte nur mit dem überarbeiteten Text."},
  zusammenfassen: {de:"Zusammenfassen", sys:"Fasse den Text in wenigen Sätzen zusammen. Erfinde nichts dazu. Antworte nur mit der Zusammenfassung."},
  uebersetzen: {de:"Übersetzen", sys:"Übersetze den Text sinngemäß in die gewünschte Sprache, mit natürlichem Ausdruck. Erfinde nichts dazu. Antworte nur mit der Übersetzung."},
  frei: {de:"Freie Frage", sys:"Du hilfst beim Schreiben eines Buches. Antworte knapp und auf Deutsch. Erfinde keine Angaben über Personen oder Orte."}
};
async function mdlList(){ if (!MDL.list){ MDL.list = await fetch("modelle.json").then(r => r.json()).catch(() => ({models:[], runtime:{}})); } return MDL.list; }
/* Passt ein Modell auf das Gerät? Gleiche Auswertung wie die Matrix in den Einstellungen (setEval). */
function mdlFit(m, d){ return setEval({requires:m.requires, reason:m.reason}, d); }
function mdlPick(models, d){   // bestes passendes: erst stark (wenn passend), sonst Standard, sonst Notbehelf
  const ok = models.filter(m => mdlFit(m, d).r !== "nein"), by = t => ok.find(m => m.tier === t);
  return (d.memoryGB && d.memoryGB >= 8 && d.storageFreeGB >= 10 ? by("stark") : null) || by("standard") || by("notbehelf") || null;
}
const mdlSize = m => fmtBytes(m.sizeBytes);
/* Antworten in Werkzeugform je Modellformat lesen (nur ergänzend; der feste Ablauf braucht sie nicht).
   gemma: <|tool_call>call:name{key:<|"|>wert<|"|>,n:3}<tool_call|>   qwen: <tool_call><function=name><parameter=key>wert</parameter></function></tool_call> */
function mdlParseTools(text, fmt){
  const out = [], s = String(text || "");
  if (fmt === "gemma"){
    for (const m of s.matchAll(/<\|tool_call>\s*call:([\w.-]+)\{([\s\S]*?)\}\s*<tool_call\|>/g)){
      const args = {};
      for (const kv of m[2].matchAll(/([\w.-]+):(?:<\|"\|>([\s\S]*?)<\|"\|>|([^,}]+))/g)){ const v = kv[2] != null ? kv[2] : kv[3].trim(); args[kv[1]] = /^-?\d+(\.\d+)?$/.test(v) && kv[2] == null ? Number(v) : v; }
      out.push({name:m[1], args});
    }
  } else if (fmt === "qwen"){
    for (const m of s.matchAll(/<tool_call>\s*<function=([\w.-]+)>([\s\S]*?)<\/function>\s*<\/tool_call>/g)){
      const args = {}; for (const p of m[2].matchAll(/<parameter=([\w.-]+)>\s*([\s\S]*?)\s*<\/parameter>/g)) args[p[1]] = p[2];
      out.push({name:m[1], args});
    }
  }
  return out;
}
function mdlMessages(task, text, extra){   // Nachrichtenliste für das Modell
  const t = MDL_TASKS[task] || MDL_TASKS.frei;
  return [{role:"system", content:t.sys}, {role:"user", content:(extra ? extra + "\n\n" : "") + text}];
}
async function mdlRuntime(){
  if (MDL.rt) return MDL.rt;
  const l = await mdlList(), url = l.runtime && l.runtime.url; if (!url) throw new Error("Keine Laufzeit in modelle.json.");
  MDL.rt = await import(url);
  return MDL.rt;
}
/* Zustand eines Modells auf diesem Gerät (#758): „complete“ nur, wenn der Download einmal ganz durchgelaufen ist (Marke MDL_DONE), „partial“, wenn Dateien im Cache liegen,
   aber die Marke fehlt (abgebrochen oder unterbrochen), sonst „none“. Fertige Dateien bleiben beim Fortsetzen im Cache und werden nicht neu geladen. */
async function mdlHasFiles(m){ try { if (!window.caches) return false; const c = await caches.open("transformers-cache"), keys = await c.keys(); return keys.some(r => r.url.includes("/" + m.repo + "/")); } catch (e) { return false; } }
async function mdlState(m){ const has = await mdlHasFiles(m); if (!has) return "none"; return store.get(MDL_DONE + m.id) ? "complete" : "partial"; }
async function mdlCached(m){ return (await mdlState(m)) === "complete"; }
let mdlLock = null;
async function mdlWake(on){   // Bildschirm anlassen, solange der Download läuft (wo der Browser es kann)
  try {
    if (!on){ if (mdlLock){ const l = mdlLock; mdlLock = null; await l.release(); } return; }
    if (navigator.wakeLock && !mdlLock){ mdlLock = await navigator.wakeLock.request("screen"); mdlLock.addEventListener && mdlLock.addEventListener("release", () => { mdlLock = null; }); }
  } catch (e) { mdlLock = null; }
}
const mdlPhase = v => { try { store.set(MDL_PHASE, v); } catch (e) {} };
const mdlFileUrl = (m, path) => "https://huggingface.co/" + m.repo + "/resolve/main/" + path;
/* Freier Platz vorab (#774): zu wenig Platz meldet sich vor dem Download, nicht erst als Absturz. Fragt außerdem dauerhaften Speicher an. */
async function mdlPreflight(m){
  try { if (navigator.storage && navigator.storage.persist) await navigator.storage.persist(); } catch (e) {}
  try {
    if (navigator.storage && navigator.storage.estimate){
      const e = await navigator.storage.estimate(), frei = (e.quota || 0) - (e.usage || 0);
      if (e.quota && frei < m.sizeBytes * 1.3) return `Zu wenig freier Speicher: ${fmtBytes(frei)} frei, ${mdlSize(m)} nötig.`;
    }
  } catch (e) {}
  return "";
}
/* Dateien einzeln gestreamt in den Cache der Laufzeit schreiben (#774, Stufe 2): Die Antwort wird durchgereicht und nie als Ganzes in den JavaScript-Speicher gelesen.
   Schlüssel ist die Anfrage-URL wie bei Transformers.js (so zählt auch mdlHasFiles). Fehlt eine Datei hier, lädt from_pretrained sie danach wie bisher selbst. */
async function mdlPrefetch(m, onBytes){
  if (!m.files || !m.files.length || !window.caches || typeof fetch !== "function") return;
  const cache = await caches.open("transformers-cache"), total = m.files.reduce((a, f) => a + f.size, 0);
  let done = 0; const ctl = new AbortController(); MDL.fetchAbort = ctl;
  for (const f of m.files){
    if (MDL.cancel) throw new Error("abgebrochen");
    const url = mdlFileUrl(m, f.path);
    if (await cache.match(url)){ done += f.size; onBytes(done, total, f.path); continue; }
    mdlPhase("datei:" + f.path);
    const res = await fetch(url, {signal:ctl.signal});
    if (!res.ok || !res.body) throw new Error("Datei nicht ladbar: " + f.path + " (" + res.status + ")");
    let got = 0; const base = done;
    const counter = new TransformStream({transform(chunk, c){ if (MDL.cancel){ ctl.abort(); c.error(new Error("abgebrochen")); return; } got += chunk.byteLength; MDL.lastTick = Date.now(); onBytes(base + got, total, f.path); c.enqueue(chunk); }});
    const headers = {"content-type": res.headers.get("content-type") || "application/octet-stream"}; const len = res.headers.get("content-length"); if (len) headers["content-length"] = len;
    await cache.put(url, new Response(res.body.pipeThrough(counter), {headers}));   // ein Abbruch mitten in der Datei hinterlässt keinen Eintrag
    done = base + f.size;
  }
  MDL.fetchAbort = null;
}
async function mdlDownload(m){
  if (MDL.busy) return; MDL.busy = true; MDL.cancel = false; MDL.msg = null; MDL.lastTick = Date.now();
  const fehl = await mdlPreflight(m);
  if (fehl){ MDL.msg = {kind:"err", html:esc(fehl)}; MDL.busy = false; if (S.view === "model") modelView(); return; }
  MDL.progress = {pct:0, file:"", loaded:0, total:m.sizeBytes, m:m.id}; store.set(MDL_RUN, m.id); mdlPhase("start");
  if (S.view === "model") modelView();   // Balken und „Abbrechen“ sofort zeigen (#758)
  mdlWake(true);
  try {
    const rt = await mdlRuntime(), files = {};
    await mdlPrefetch(m, (l, t, file) => { MDL.progress = {pct:Math.min(99, Math.round(l / t * 100)), file, loaded:l, total:t, m:m.id}; mdlTick(); });
    if (MDL.cancel) throw new Error("abgebrochen");
    mdlPhase("sitzung"); MDL.starting = true; if (S.view === "model") modelView();
    const model = await rt[m.class].from_pretrained(m.repo, {dtype:m.dtype, device:"webgpu", progress_callback: p => {
      if (MDL.cancel) throw new Error("abgebrochen");   // beendet den Download an der nächsten Meldung; fertige Dateien bleiben im Cache
      MDL.lastTick = Date.now();
      if (p.status === "progress" && p.file){ files[p.file] = {l:p.loaded, t:p.total}; const l = Object.values(files).reduce((a, f) => a + f.l, 0); MDL.progress = {pct:Math.min(99, Math.round(l / m.sizeBytes * 100)), file:p.file, loaded:l, total:m.sizeBytes, m:m.id}; mdlTick(); }
    }});
    if (MDL.cancel) throw new Error("abgebrochen");
    MDL.progress = {pct:100, file:"", loaded:m.sizeBytes, total:m.sizeBytes, m:m.id}; mdlTick();
    mdlPhase("prozessor");
    const proc = await rt.AutoProcessor.from_pretrained(m.repo);
    MDL.pipe = {model, proc, m}; MDL.loaded = m.id; store.set(MDL_KEY, m.id); store.set(MDL_DONE + m.id, "1"); store.set(MDL_CRASH + m.id, "");
    MDL.msg = {kind:"ok", html:`<b>${esc(m.name.de)}</b> ist geladen und liegt im Speicher dieses Browsers.`};
  } catch (e) {
    if (MDL.cancel) MDL.msg = {kind:"info", html:"Der Download wurde abgebrochen. Fertig geladene Dateien bleiben erhalten; „Download fortsetzen“ lädt nur den Rest."};
    else { MDL.msg = {kind:"err", html:esc("Das Modell konnte nicht geladen werden: " + (e && e.message || e)) + " Fertig geladene Dateien bleiben erhalten; „Download fortsetzen“ lädt nur den Rest."}; if (typeof errLog === "function") errLog(e, {schritt:"modell"}); }
  }
  MDL.busy = false; MDL.cancel = false; MDL.starting = false; MDL.fetchAbort = null; MDL.progress = {}; store.set(MDL_RUN, ""); mdlPhase(""); mdlWake(false); if (S.view === "model") modelView();
}
function mdlProgLabel(p){ return MDL.starting ? "Modell wird gestartet …" : !p.loaded ? "wird geladen …" : `${p.pct || 0} % · ${fmtBytes(p.loaded)} von ${fmtBytes(p.total)}`; }
function mdlTick(){ const el = $("mdlprog"); if (!el) return; const p = MDL.progress; el.value = p.pct || 0; const t = $("mdlproglabel"); if (t) t.textContent = mdlProgLabel(p); }
async function mdlDelete(m){
  try { const c = await caches.open("transformers-cache"); for (const r of await c.keys()) if (r.url.includes("/" + m.repo + "/")) await c.delete(r); } catch (e) {}
  if (MDL.loaded === m.id){ MDL.pipe = null; MDL.loaded = null; } store.set(MDL_KEY, ""); store.set(MDL_DONE + m.id, "");
  MDL.msg = {kind:"ok", html:"Das Modell wurde von diesem Gerät gelöscht."}; modelView();
}
async function mdlGenerate(messages, onText, maxTokens){
  if (!MDL.pipe) throw new Error("Es ist kein Modell geladen.");
  const rt = await mdlRuntime(), {model, proc} = MDL.pipe, tok = proc.tokenizer || proc;
  const prompt = proc.apply_chat_template ? proc.apply_chat_template(messages, {add_generation_prompt:true}) : tok.apply_chat_template(messages, {add_generation_prompt:true, tokenize:false});
  const inputs = await proc(prompt, null, null, {add_special_tokens:false}).catch(() => tok(prompt, {add_special_tokens:false}));
  let out = ""; MDL.abort = new rt.InterruptableStoppingCriteria();
  const streamer = new rt.TextStreamer(tok, {skip_prompt:true, skip_special_tokens:true, callback_function: t => { out += t; if (onText) onText(out); }});
  await model.generate({...inputs, max_new_tokens:maxTokens || 700, do_sample:false, streamer, stopping_criteria:MDL.abort});
  MDL.abort = null; return out.trim();
}
async function mdlProbe(m){   // Probelauf: kurzer Auftrag, Zeitmessung; das Ergebnis bleibt auf dem Gerät
  const t0 = performance.now(); let n = 0;
  const txt = await mdlGenerate(mdlMessages("uebersetzen", "Der Hund lief durch den Garten.", "Übersetze ins Englische."), () => { n++; }, 24);
  const s = (performance.now() - t0) / 1000; MDL.probe[m.id] = {sec:s, tokens:n, text:txt, tps:n / s};
  return MDL.probe[m.id];
}
function mdlCrashMsg(ph, n){   // Absturz erkennen und benennen (#774): wiederholt an derselben Stelle heißt „Gerät schafft es nicht“
  const wo = ph === "sitzung" ? "beim Starten des Modells" : ph && ph.startsWith("datei:") ? "bei der Datei " + ph.slice(6) : "";
  if (n >= 2 && ph && ph !== "start") return {kind:"warn", html:`Der Download ist ${n} Mal an derselben Stelle abgestürzt${wo ? " (" + esc(wo) + ")" : ""}. Wahrscheinlich reicht der Arbeitsspeicher dieses Geräts nicht. Weitere Versuche helfen vermutlich nicht; nutze den Chat mit GhostWriter oder einen Rechner. „Diagnose kopieren“ hilft bei der Fehlersuche.`, repeat:true};
  return {kind:"warn", html:`Der letzte Download wurde unterbrochen${wo ? " (" + esc(wo) + ")" : ""}, etwa durch Neuladen, App-Wechsel oder Speichermangel. Fertig geladene Dateien bleiben erhalten; „Download fortsetzen“ lädt nur den Rest.`};
}
/* Diagnose zum Kopieren (#774): nur Gerätewerte und Modellzustand, keine Buchinhalte. */
async function mdlDiagnose(){
  const dev = await setDevice(), l = await mdlList(), est = navigator.storage && navigator.storage.estimate ? await navigator.storage.estimate().catch(() => ({})) : {}, pm = (typeof performance !== "undefined" && performance.memory) || {};
  const rows = [["Modelle", l.models.map(m => m.id + ": " + (store.get(MDL_CRASH + m.id) || 0) + " Abstürze, Stelle " + (store.get(MDL_CRASH + "phase." + m.id) || "–")).join("; ")],
    ["Speicher frei/Kontingent", `${fmtBytes((est.quota || 0) - (est.usage || 0))} / ${fmtBytes(est.quota || 0)}`], ["Arbeitsspeicher (deviceMemory)", String(navigator.deviceMemory || "unbekannt")], ["Kerne", String(navigator.hardwareConcurrency || "unbekannt")],
    ["WebGPU maxBufferSize", String(dev.maxBuffer || "–")], ["WebGPU maxStorageBufferBindingSize", String(dev.maxStorageBuffer || "–")], ["JS-Heap belegt", pm.usedJSHeapSize ? fmtBytes(pm.usedJSHeapSize) : "–"],
    ["Dauerhaft angefordert", String(dev.persisted)], ["Mobilgerät", String(!!dev.mobile)], ["Browser", typeof errBrowser === "function" ? errBrowser() : "–"]];
  return "GhostWriter Modell-Diagnose\n" + rows.map(r => r[0] + ": " + r[1]).join("\n");
}
async function modelView(){
  if (!MDL.back || S.view !== "model") MDL.back = {view:S.view || "connect", arg:S.view === "section" ? S.sec && S.sec.id : S.chap};
  S.view = "model"; crumbs();
  if (!MDL.busy && store.get(MDL_RUN)){
    const id = store.get(MDL_RUN), ph = store.get(MDL_PHASE); store.set(MDL_RUN, ""); mdlPhase("");
    const n = Number(store.get(MDL_CRASH + id) || 0) + 1; store.set(MDL_CRASH + id, String(n)); store.set(MDL_CRASH + "phase." + id, ph);
    MDL.msg = mdlCrashMsg(ph, n);
  }
  const [l, dev] = await Promise.all([mdlList(), setDevice()]), pick = mdlPick(l.models, dev), webgpu = dev.webgpu;
  const rows = [];
  for (const m of l.models){
    const fit = mdlFit(m, dev), state = await mdlState(m), cached = state === "complete", partial = state === "partial", loaded = MDL.loaded === m.id, big = m.sizeBytes > 1.5e9;
    const act = MDL.busy ? '<span class="dim">Download läuft …</span>' : loaded ? `<button class="btn" data-mdl="probe" data-id="${m.id}">Probelauf</button> <button class="btn" data-mdl="delete" data-id="${m.id}">Löschen</button>`
      : fit.r === "nein" ? `<span class="dim" title="${esc(fit.why)}">geht auf diesem Gerät nicht</span>` : cached ? `<button class="btn pri" data-mdl="load" data-id="${m.id}">Laden</button> <button class="btn" data-mdl="delete" data-id="${m.id}">Löschen</button>`
      : partial ? `<button class="btn pri" data-mdl="load" data-id="${m.id}">Download fortsetzen</button> <button class="btn" data-mdl="delete" data-id="${m.id}">Löschen</button>`
      : `<button class="btn pri" data-mdl="download" data-id="${m.id}">${mdlSize(m)} herunterladen</button>`;
    const pr = MDL.probe[m.id];
    rows.push(`<tr><td><b>${esc(m.name.de)}</b>${pick && pick.id === m.id ? ' <span class="dim">(Vorschlag für dieses Gerät)</span>' : ""}<div class="dim">${esc(m.note.de)}<br>Lizenz ${esc(m.license)} · ${mdlSize(m)}${cached ? " · liegt auf diesem Gerät" : partial ? " · Download unvollständig" : ""}</div>${fit.r === "nein" ? `<div class="dim">${esc(fit.why)}</div>` : fit.r === "eingeschraenkt" ? `<div class="dim">${esc(fit.why)}</div>` : ""}${pr ? `<div class="dim">Probelauf: ${pr.tps.toFixed(1).replace(".", ",")} Token/s, „${esc(pr.text)}“</div>` : ""}</td><td style="white-space:nowrap">${act}</td></tr>`);
  }
  const p = MDL.progress, prog = MDL.busy ? `<div style="margin:8px 0"><progress id="mdlprog" max="100" value="${p.pct || 0}" style="width:100%"></progress><div class="dim" id="mdlproglabel">${mdlProgLabel(p)}</div><div class="dim">App offen und Bildschirm an lassen, bis der Download fertig ist.</div><button class="btn" data-mdl="cancel">Abbrechen</button></div>` : "";
  const chat = MDL.loaded ? mdlChatHtml() : '<p class="dim">Zum Chatten zuerst ein Modell laden.</p>';
  $("app").innerHTML = `<div class="one"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><b style="font-size:20px">Modell im Browser</b><button class="btn" data-act="mdl-back">Zurück</button></div>${msgBox()}${MDL.msg ? `<div class="note ${MDL.msg.kind}">${MDL.msg.html}</div>` : ""}
    <section class="card"><b>Wie das funktioniert</b><p class="dim" style="margin:6px 0">Das Modell läuft auf diesem Gerät. Dein Text wird <b>nicht ins Netz geschickt</b>. Heruntergeladen werden nur das Programm für das Modell (von ${esc((l.runtime && l.runtime.host) || "cdn.jsdelivr.net")}) und die Modelldatei (von huggingface.co), und zwar erst, wenn du auf „Herunterladen“ klickst. Das Modell schlägt nur vor; gespeichert wird nichts von allein.</p>
    ${webgpu ? "" : '<div class="note warn">Dieses Gerät meldet kein WebGPU. Ohne WebGPU läuft das Modell nicht oder sehr langsam; nutze dann den Chat mit GhostWriter.</div>'}${dev.shaderF16 ? "" : webgpu ? '<div class="note warn">WebGPU ohne „shader-f16“: die kleinen Modelle brauchen es.</div>' : ""}</section>
    <section class="card"><b>Modelle</b>${dev.mobile ? '<div class="note warn">Auf Handys stürzt der Download großer Modelle oft ab (zu wenig Arbeitsspeicher pro Tab). Besser am Rechner oder im Chat mit GhostWriter.</div>' : ""}${prog}<table class="kv">${rows.join("")}</table></section><section class="card"><b>Chat</b>${chat}</section><section class="card"><button class="btn" data-mdl="diag">Diagnose kopieren</button> <span class="dim">Gerätewerte und Modellzustand, keine Buchinhalte.</span></section></div>`;
  window.scrollTo(0, 0);
}
function mdlChatHtml(){
  const hist = MDL.chat.map(c => `<div style="margin:8px 0"><div class="dim">${c.role === "user" ? "Du (" + esc(MDL_TASKS[c.task] ? MDL_TASKS[c.task].de : "Frage") + ")" : "Vorschlag des Modells – bitte prüfen"}</div><div ${c.live ? "data-live" : ""} style="white-space:pre-wrap;${c.role === "user" ? "" : "background:var(--card2,#f4f1e8);padding:8px;border-radius:6px"}">${esc(c.text)}</div>${c.role === "ai" && !c.live ? `<button class="btn" data-mdl="copy" data-i="${MDL.chat.indexOf(c)}">Vorschlag kopieren</button>` : ""}</div>`).join("");
  return `${hist}<form id="fMdl"><select id="mdlTask">${Object.entries(MDL_TASKS).map(([k, v]) => `<option value="${k}">${v.de}</option>`).join("")}</select> <input id="mdlExtra" placeholder="Hinweis, z. B. Zielsprache" style="width:40%"><textarea id="mdlText" rows="5" style="width:100%;margin-top:6px" placeholder="Text einfügen …"></textarea>
    <div class="row" style="gap:8px;margin-top:6px"><button class="btn pri" type="submit" ${MDL.busy ? "disabled" : ""}>Vorschlag erzeugen</button> ${MDL.abort ? '<button class="btn" type="button" data-mdl="stop">Anhalten</button>' : ""}</div><div class="dim">Das Modell kann Fehler machen und Angaben erfinden. Nichts wird automatisch ins Buch übernommen.</div></form>`;
}
async function mdlAsk(task, text, extra){
  MDL.chat.push({role:"user", task, text}); const ai = {role:"ai", text:"…", live:true}; MDL.chat.push(ai); MDL.busy = true; modelView();
  try { ai.text = await mdlGenerate(mdlMessages(task, text, extra), t => { ai.text = t; const el = document.querySelector("[data-live]"); if (el) el.textContent = t; }); }
  catch (e) { ai.text = "Das Modell konnte nicht antworten: " + (e && e.message || e); }
  ai.live = false; MDL.busy = false; modelView();
}
document.addEventListener("visibilitychange", () => {   // zurück in der App: Bildschirmsperre neu anfordern, hängenden Download melden (#758)
  if (document.visibilityState !== "visible" || !MDL.busy || MDL.cancel) return;
  mdlWake(true);
  if (Date.now() - (MDL.lastTick || 0) > 20000){ MDL.msg = {kind:"warn", html:"Der Download scheint ins Stocken geraten zu sein (die App war im Hintergrund). Mit „Abbrechen“ beenden und danach „Download fortsetzen“ wählen; fertige Dateien bleiben erhalten."}; if (S.view === "model") modelView(); }
});
GW_PORTS.views = Object.assign(GW_PORTS.views || {}, {model:modelView});
document.addEventListener("click", async ev => {
  const g = ev.target.closest && ev.target.closest("#modelbtn"); if (g){ ev.preventDefault(); return modelView(); }
  const a = ev.target.closest && ev.target.closest("[data-act]");
  if (a && a.dataset.act === "mdl-back"){ ev.preventDefault(); const k = MDL.back || {view:"connect"}; MDL.back = null; return show(k.view, k.arg); }
  const b = ev.target.closest && ev.target.closest("[data-mdl]"); if (!b) return; ev.preventDefault();
  const k = b.dataset.mdl, l = await mdlList(), m = l.models.find(x => x.id === b.dataset.id);
  if (k === "download" && m){
    if (m.sizeBytes > 1.5e9 && !confirm(`${mdlSize(m)} herunterladen? Das ist viel Datenvolumen; im WLAN ist es besser. Der Download kommt von huggingface.co, die Modelldatei bleibt im Speicher dieses Browsers.`)) return;
    return mdlDownload(m);
  }
  if (k === "load" && m) return mdlDownload(m);
  if (k === "delete" && m){ if (confirm("Das Modell von diesem Gerät löschen?")) mdlDelete(m); return; }
  if (k === "probe" && m){ MDL.msg = {kind:"info", html:"Probelauf läuft …"}; MDL.busy = true; modelView(); try { const r = await mdlProbe(m); MDL.msg = {kind:"ok", html:`Probelauf: ${r.tps.toFixed(1).replace(".", ",")} Token pro Sekunde.`}; } catch (e) { MDL.msg = {kind:"err", html:esc("Der Probelauf ist fehlgeschlagen: " + (e && e.message || e))}; } MDL.busy = false; return modelView(); }
  if (k === "cancel"){ if (MDL.abort){ try { MDL.abort.interrupt(); } catch (e) {} return; } MDL.cancel = true; MDL.msg = {kind:"info", html:"Wird abgebrochen …"}; const t = $("mdlproglabel"); if (t) t.textContent = "wird abgebrochen …"; return; }
  if (k === "diag"){ try { await navigator.clipboard.writeText(await mdlDiagnose()); b.textContent = "Kopiert"; } catch (e) { b.textContent = "Nicht möglich"; } return; }
  if (k === "stop"){ try { MDL.abort && MDL.abort.interrupt(); } catch (e) {} return; }
  if (k === "copy"){ try { await navigator.clipboard.writeText(MDL.chat[Number(b.dataset.i)].text); b.textContent = "Kopiert"; } catch (e) { b.textContent = "Nicht möglich"; } }
});
document.addEventListener("submit", ev => {
  if (ev.target.id !== "fMdl") return; ev.preventDefault();
  const text = $("mdlText").value.trim(); if (!text || MDL.busy) return; mdlAsk($("mdlTask").value, text, $("mdlExtra").value.trim());
});
