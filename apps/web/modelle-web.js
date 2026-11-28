/* ---------- Modell im Browser (#525, #662) ----------
   Ein Sprachmodell läuft auf diesem Gerät (WebGPU, Transformers.js). Nichts davon läuft ohne ausdrücklichen Klick: Laufzeit (Skript von cdn.jsdelivr.net) und Gewichte
   (huggingface.co) werden erst nach „Herunterladen“ geladen und bleiben im Cache dieses Browsers; Buchtext verlässt das Gerät nie. Die KI schlägt nur vor: Es wird nichts
   automatisch gespeichert, ein Vorschlag wird erst nach eigenem Klick übernommen (Kopieren). Die Liste steht in modelle.json (Format wie faehigkeiten.json). */
const MDL = {list:null, rt:null, loaded:null, pipe:null, busy:false, progress:{}, abort:null, msg:null, probe:{}, chat:[], back:null, srv:{models:[], err:""}};
const MDL_KEY = "gw.model", MDL_DONE = "gw.model.done.", MDL_RUN = "gw.model.run", MDL_CRASH = "gw.model.crash.", MDL_SRV = "gw.model.server", MDL_SRVM = "gw.model.server.model";   // fertig geladen (je Modell) / Download läuft (Marke gegen Unterbrechung, #758)
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
  return (d.memoryGB && d.memoryGB >= 8 && d.storageFreeGB >= 10 ? by("stark") : null) || by("standard") || by("notbehelf") || by("mini") || null;   // Handys melden höchstens 4 GB (Chrome rundet ab): dort bleibt das Mini-Modell (#774)
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
/* Rechner im selben Netz (#774, #525): Ollama, LM Studio u. a. mit OpenAI-kompatibler Schnittstelle. Das Modell läuft dort, nicht im Browser; der Text geht nur an die
   eingetragene Adresse. Die Adresse liegt im Speicher dieses Geräts (kein Geheimnis). Von einer https-Seite aus erlaubt der Browser nur https oder localhost. */
function mdlSrvNorm(u){
  let s = String(u || "").trim().replace(/\/+$/, ""); if (!s) return "";
  if (!/^https?:\/\//i.test(s)) s = "http://" + s;
  return /\/v1$/i.test(s) ? s : s + "/v1";
}
function mdlSrvLocal(u){   // Adresse im eigenen Netz? (localhost, 127.x, 10.x, 192.168.x, 172.16–31.x, *.local, ohne Punkt)
  try { const h = new URL(u).hostname; return h === "localhost" || /^127\./.test(h) || /^10\./.test(h) || /^192\.168\./.test(h) || /^172\.(1[6-9]|2\d|3[01])\./.test(h) || /\.local$/i.test(h) || !h.includes("."); } catch (e) { return false; }
}
async function mdlSrvModels(u){
  const base = mdlSrvNorm(u); if (!base) throw new Error("Keine Adresse eingetragen.");
  const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), 8000);
  try {
    const r = await fetch(base + "/models", {signal:ctl.signal}); if (!r.ok) throw new Error("Der Server antwortet mit " + r.status + ".");
    const j = await r.json(), ids = (j.data || j.models || []).map(x => x.id || x.name).filter(Boolean);
    if (!ids.length) throw new Error("Der Server meldet kein Modell. Zuerst dort ein Modell laden.");
    return ids;
  } catch (e) {
    if (e && e.name === "AbortError") throw new Error("Keine Antwort nach 8 Sekunden. Läuft der Server und ist er im selben Netz?");
    if (e && e.name === "TypeError") throw new Error("Der Server ist nicht erreichbar. Mögliche Gründe: falsche Adresse, Server aus, kein gemeinsames Netz, fehlende Freigabe (CORS) für " + (typeof location !== "undefined" ? location.origin : "diese App") + ", oder die App läuft über https und die Adresse über http (nur localhost oder https erlaubt).");
    throw e;
  } finally { clearTimeout(t); }
}
/* Ein Datenstrom-Block der Schnittstelle („data: {…}“-Zeilen) → Textstücke; übrig bleibt eine unfertige letzte Zeile */
function mdlSrvChunks(buf){
  const out = [], lines = buf.split("\n"), rest = lines.pop();
  for (const ln of lines){ const m = ln.match(/^data:\s*(.*)$/); if (!m || m[1] === "[DONE]" || !m[1].trim()) continue; try { const d = JSON.parse(m[1]), c = d.choices && d.choices[0], t = c && ((c.delta && c.delta.content) || c.text); if (t) out.push(t); } catch (e) {} }
  return {out, rest};
}
async function mdlSrvGenerate(messages, onText, maxTokens){
  const base = mdlSrvNorm(store.get(MDL_SRV)), model = store.get(MDL_SRVM), ctl = new AbortController();
  MDL.abort = {interrupt: () => ctl.abort()};
  let out = "";
  try {
    const r = await fetch(base + "/chat/completions", {method:"POST", headers:{"Content-Type":"application/json"}, signal:ctl.signal, body:JSON.stringify({model, messages, stream:true, temperature:0, max_tokens:maxTokens || 700})});
    if (!r.ok) throw new Error("Der Server antwortet mit " + r.status + ".");
    const rd = r.body.getReader(), dec = new TextDecoder(); let buf = "";
    for (;;){ const {done, value} = await rd.read(); if (done) break; buf += dec.decode(value, {stream:true}); const c = mdlSrvChunks(buf); buf = c.rest; for (const t of c.out){ out += t; if (onText) onText(out); } }
  } catch (e) { if (!(e && e.name === "AbortError")) throw e; }   // „Anhalten“ liefert den bisherigen Text
  MDL.abort = null; return out.trim();
}
async function mdlSrvConnect(u){
  MDL.srv.err = ""; MDL.busy = true; if (S.view === "model") modelView();
  try {
    const ids = await mdlSrvModels(u); MDL.srv.models = ids; store.set(MDL_SRV, mdlSrvNorm(u));
    const keep = store.get(MDL_SRVM); store.set(MDL_SRVM, ids.includes(keep) ? keep : ids[0]);
    MDL.msg = {kind:"ok", html:"Verbunden. Gewählt: <b>" + esc(store.get(MDL_SRVM)) + "</b>. Mit „Diesen Rechner nutzen“ übernimmst du ihn."};
  } catch (e) { MDL.srv.err = e && e.message || String(e); MDL.msg = {kind:"err", html:esc(MDL.srv.err)}; }
  MDL.busy = false; if (S.view === "model") modelView();
}
function mdlSrvUse(){
  const name = store.get(MDL_SRVM); if (!mdlSrvNorm(store.get(MDL_SRV)) || !name) return;
  MDL.pipe = {server:true, name}; MDL.loaded = "server"; MDL.msg = {kind:"ok", html:"Rechner im Netz wird genutzt: <b>" + esc(name) + "</b>. Dein Text geht nur an diese Adresse."}; modelView();
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
async function mdlDownload(m){
  if (MDL.busy) return; MDL.busy = true; MDL.cancel = false; MDL.msg = null; MDL.lastTick = Date.now();
  MDL.progress = {pct:0, file:"", loaded:0, total:m.sizeBytes, m:m.id}; store.set(MDL_RUN, m.id + "|download"); store.set(MDL_CRASH + m.id, "");
  try { navigator.storage && navigator.storage.persist && navigator.storage.persist(); } catch (e) {}   // Kontingent sichern (#774)
  if (S.view === "model") modelView();   // Balken und „Abbrechen“ sofort zeigen (#758)
  mdlWake(true);
  try {
    const rt = await mdlRuntime(), files = {};
    const model = await rt[m.class].from_pretrained(m.repo, {dtype:m.dtype, device:"webgpu", progress_callback: p => {
      if (MDL.cancel) throw new Error("abgebrochen");   // beendet den Download an der nächsten Meldung; fertige Dateien bleiben im Cache
      MDL.lastTick = Date.now();
      if (p.status === "progress" && p.file){ files[p.file] = {l:p.loaded, t:p.total}; const l = Object.values(files).reduce((a, f) => a + f.l, 0); MDL.progress = {pct:Math.min(99, Math.round(l / m.sizeBytes * 100)), file:p.file, loaded:l, total:m.sizeBytes, m:m.id}; if (l >= m.sizeBytes * 0.97 && store.get(MDL_RUN) !== m.id + "|start") store.set(MDL_RUN, m.id + "|start"); mdlTick(); }   // fast alles da: stürzt der Tab jetzt ab, war es das Starten (#774)
    }});
    if (MDL.cancel) throw new Error("abgebrochen");
    MDL.progress = {pct:100, file:"", loaded:m.sizeBytes, total:m.sizeBytes, m:m.id}; mdlTick();
    const proc = await rt.AutoProcessor.from_pretrained(m.repo);
    MDL.pipe = {model, proc, m}; MDL.loaded = m.id; store.set(MDL_KEY, m.id); store.set(MDL_DONE + m.id, "1"); store.set(MDL_CRASH + m.id, "");
    MDL.msg = {kind:"ok", html:`<b>${esc(m.name.de)}</b> ist geladen und liegt im Speicher dieses Browsers.`};
  } catch (e) {
    if (MDL.cancel) MDL.msg = {kind:"info", html:"Der Download wurde abgebrochen. Fertig geladene Dateien bleiben erhalten; „Download fortsetzen“ lädt nur den Rest."};
    else { MDL.msg = {kind:"err", html:esc("Das Modell konnte nicht geladen werden: " + (e && e.message || e)) + " Fertig geladene Dateien bleiben erhalten; „Download fortsetzen“ lädt nur den Rest."}; if (typeof errLog === "function") errLog(e, {schritt:"modell"}); }
  }
  MDL.busy = false; MDL.cancel = false; MDL.progress = {}; store.set(MDL_RUN, ""); mdlWake(false); if (S.view === "model") modelView();
}
function mdlProgLabel(p){ return !p.loaded ? "wird geladen …" : `${p.pct || 0} % · ${fmtBytes(p.loaded)} von ${fmtBytes(p.total)}`; }
function mdlTick(){ const el = $("mdlprog"); if (!el) return; const p = MDL.progress; el.value = p.pct || 0; const t = $("mdlproglabel"); if (t) t.textContent = mdlProgLabel(p); }
async function mdlDelete(m){
  try { const c = await caches.open("transformers-cache"); for (const r of await c.keys()) if (r.url.includes("/" + m.repo + "/")) await c.delete(r); } catch (e) {}
  if (MDL.loaded === m.id){ MDL.pipe = null; MDL.loaded = null; } store.set(MDL_KEY, ""); store.set(MDL_DONE + m.id, ""); store.set(MDL_CRASH + m.id, "");
  MDL.msg = {kind:"ok", html:"Das Modell wurde von diesem Gerät gelöscht."}; modelView();
}
async function mdlGenerate(messages, onText, maxTokens){
  if (!MDL.pipe) throw new Error("Es ist kein Modell geladen.");
  if (MDL.pipe.server) return mdlSrvGenerate(messages, onText, maxTokens);
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
async function modelView(){
  if (!MDL.back || S.view !== "model") MDL.back = {view:S.view || "connect", arg:S.view === "section" ? S.sec && S.sec.id : S.chap};
  S.view = "model"; crumbs();
  if (!MDL.busy && store.get(MDL_RUN)){
    const [rid, phase] = String(store.get(MDL_RUN)).split("|"); store.set(MDL_RUN, "");
    if (phase === "start"){ store.set(MDL_CRASH + rid, "1"); MDL.msg = {kind:"err", html:"Das Modell war fast geladen, doch beim <b>Starten</b> ist die Seite abgestürzt: Dem Gerät fehlt der Arbeitsspeicher. Es wird nicht noch einmal versucht. Wähle das Mini-Modell oder verbinde einen Rechner im Netz (unten)."}; }
    else MDL.msg = {kind:"warn", html:"Der letzte Download wurde unterbrochen (Seite neu geladen oder App gewechselt). Fertig geladene Dateien bleiben erhalten; „Download fortsetzen“ lädt nur den Rest."};
  }
  const [l, dev] = await Promise.all([mdlList(), setDevice()]), pick = mdlPick(l.models, dev), webgpu = dev.webgpu;
  const rows = [];
  for (const m of l.models){
    const fit = mdlFit(m, dev), state = await mdlState(m), cached = state === "complete", partial = state === "partial", loaded = MDL.loaded === m.id, big = m.sizeBytes > 1.5e9, crashed = !!store.get(MDL_CRASH + m.id);
    const act = MDL.busy ? '<span class="dim">Download läuft …</span>' : loaded ? `<button class="btn" data-mdl="probe" data-id="${m.id}">Probelauf</button> <button class="btn" data-mdl="delete" data-id="${m.id}">Löschen</button>`
      : fit.r === "nein" ? `<span class="dim" title="${esc(fit.why)}">geht auf diesem Gerät nicht</span>` : crashed ? `<span class="dim">startet auf diesem Gerät nicht</span> <button class="btn" data-mdl="retry" data-id="${m.id}">Trotzdem versuchen</button> <button class="btn" data-mdl="delete" data-id="${m.id}">Löschen</button>` : cached ? `<button class="btn pri" data-mdl="load" data-id="${m.id}">Laden</button> <button class="btn" data-mdl="delete" data-id="${m.id}">Löschen</button>`
      : partial ? `<button class="btn pri" data-mdl="load" data-id="${m.id}">Download fortsetzen</button> <button class="btn" data-mdl="delete" data-id="${m.id}">Löschen</button>`
      : `<button class="btn pri" data-mdl="download" data-id="${m.id}">${mdlSize(m)} herunterladen</button>`;
    const pr = MDL.probe[m.id];
    rows.push(`<tr><td><b>${esc(m.name.de)}</b>${pick && pick.id === m.id ? ' <span class="dim">(Vorschlag für dieses Gerät)</span>' : ""}<div class="dim">${esc(m.note.de)}<br>Lizenz ${esc(m.license)} · ${mdlSize(m)}${cached ? " · liegt auf diesem Gerät" : partial ? " · Download unvollständig" : ""}</div>${fit.r === "nein" ? `<div class="dim">${esc(fit.why)}</div>` : fit.r === "eingeschraenkt" ? `<div class="dim">${esc(fit.why)}</div>` : ""}${pr ? `<div class="dim">Probelauf: ${pr.tps.toFixed(1).replace(".", ",")} Token/s, „${esc(pr.text)}“</div>` : ""}</td><td style="white-space:nowrap">${act}</td></tr>`);
  }
  const p = MDL.progress, prog = MDL.busy ? `<div style="margin:8px 0"><progress id="mdlprog" max="100" value="${p.pct || 0}" style="width:100%"></progress><div class="dim" id="mdlproglabel">${mdlProgLabel(p)}</div><div class="dim">App offen und Bildschirm an lassen, bis der Download fertig ist.</div><button class="btn" data-mdl="cancel">Abbrechen</button></div>` : "";
  const sv = store.get(MDL_SRV) || "", svm = store.get(MDL_SRVM) || "", svBusy = MDL.busy ? "disabled" : "";
  const server = `<section class="card"><b>Rechner im selben Netz</b><p class="dim" style="margin:6px 0">Statt das Modell auf dem Handy zu laden, kann ein Rechner im selben WLAN es ausführen (Ollama, LM Studio u. a.). Die Rechenarbeit liegt dort; <b>der Text geht nur an die eingetragene Adresse</b>, nicht ins Internet.</p>
    <div class="row" style="gap:8px"><input id="mdlSrvUrl" value="${esc(sv)}" placeholder="http://192.168.0.20:11434" style="flex:1"> <button class="btn" data-mdl="srv-connect" ${svBusy}>Verbinden</button></div>
    ${sv && !mdlSrvLocal(sv) ? '<div class="note warn" style="margin-top:6px">Diese Adresse liegt nicht im eigenen Netz. Dein Text würde dorthin gesendet.</div>' : ""}
    ${MDL.srv.models.length ? `<div class="row" style="gap:8px;margin-top:6px"><select id="mdlSrvModel">${MDL.srv.models.map(x => `<option value="${esc(x)}" ${x === svm ? "selected" : ""}>${esc(x)}</option>`).join("")}</select> <button class="btn pri" data-mdl="srv-use" ${svBusy}>Diesen Rechner nutzen</button></div>` : ""}
    <div class="dim" style="margin-top:6px">Am Rechner nötig: Der Server muss im Netz erreichbar sein und diese App zulassen (Ollama: <code>OLLAMA_HOST=0.0.0.0</code> und <code>OLLAMA_ORIGINS=${esc(location.origin)}</code>). Aus einer https-App sind nur https-Adressen oder localhost erlaubt.</div></section>`;
  const chat = MDL.loaded ? mdlChatHtml() : '<p class="dim">Zum Chatten zuerst ein Modell laden.</p>';
  $("app").innerHTML = `<div class="one"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><b style="font-size:20px">Modell im Browser</b><button class="btn" data-act="mdl-back">Zurück</button></div>${msgBox()}${MDL.msg ? `<div class="note ${MDL.msg.kind}">${MDL.msg.html}</div>` : ""}
    <section class="card"><b>Wie das funktioniert</b><p class="dim" style="margin:6px 0">Das Modell läuft auf diesem Gerät. Dein Text wird <b>nicht ins Netz geschickt</b>. Heruntergeladen werden nur das Programm für das Modell (von ${esc((l.runtime && l.runtime.host) || "cdn.jsdelivr.net")}) und die Modelldatei (von huggingface.co), und zwar erst, wenn du auf „Herunterladen“ klickst. Das Modell schlägt nur vor; gespeichert wird nichts von allein.</p>
    ${webgpu ? "" : '<div class="note warn">Dieses Gerät meldet kein WebGPU. Ohne WebGPU läuft das Modell nicht oder sehr langsam; nutze dann den Chat mit GhostWriter.</div>'}${dev.shaderF16 ? "" : webgpu ? '<div class="note warn">WebGPU ohne „shader-f16“: die kleinen Modelle brauchen es.</div>' : ""}</section>
    <section class="card"><b>Modelle</b>${prog}<table class="kv">${rows.join("")}</table></section>${server}<section class="card"><b>Chat</b>${chat}</section></div>`;
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
  if (k === "retry" && m){ if (confirm("Das Modell hat auf diesem Gerät schon einmal beim Starten versagt. Noch einmal versuchen?")){ store.set(MDL_CRASH + m.id, ""); return mdlDownload(m); } return; }
  if (k === "srv-connect") return mdlSrvConnect(($("mdlSrvUrl") || {}).value);
  if (k === "srv-use"){ const sel = $("mdlSrvModel"); if (sel) store.set(MDL_SRVM, sel.value); return mdlSrvUse(); }
  if (k === "delete" && m){ if (confirm("Das Modell von diesem Gerät löschen?")) mdlDelete(m); return; }
  if (k === "probe" && m){ MDL.msg = {kind:"info", html:"Probelauf läuft …"}; MDL.busy = true; modelView(); try { const r = await mdlProbe(m); MDL.msg = {kind:"ok", html:`Probelauf: ${r.tps.toFixed(1).replace(".", ",")} Token pro Sekunde.`}; } catch (e) { MDL.msg = {kind:"err", html:esc("Der Probelauf ist fehlgeschlagen: " + (e && e.message || e))}; } MDL.busy = false; return modelView(); }
  if (k === "cancel"){ if (MDL.abort){ try { MDL.abort.interrupt(); } catch (e) {} return; } MDL.cancel = true; MDL.msg = {kind:"info", html:"Wird abgebrochen …"}; const t = $("mdlproglabel"); if (t) t.textContent = "wird abgebrochen …"; return; }
  if (k === "stop"){ try { MDL.abort && MDL.abort.interrupt(); } catch (e) {} return; }
  if (k === "copy"){ try { await navigator.clipboard.writeText(MDL.chat[Number(b.dataset.i)].text); b.textContent = "Kopiert"; } catch (e) { b.textContent = "Nicht möglich"; } }
});
document.addEventListener("submit", ev => {
  if (ev.target.id !== "fMdl") return; ev.preventDefault();
  const text = $("mdlText").value.trim(); if (!text || MDL.busy) return; mdlAsk($("mdlTask").value, text, $("mdlExtra").value.trim());
});
