/* Rückgabe vom Gegenlesen (#573, #209): lesende Ansicht der Ablage `checkouts/<kennung>/rueckgabe-<datum>/rueckgabe.yml`. Einchecken
   (Upload, Zuordnung, Vergleich) und das Übernehmen von Aufbau-Änderungen laufen im Chat mit GhostWriter (scripts/checkin.py): die App
   kann keine Dateien binär hochladen und keine Programmskripte ausführen. */
async function checkoutsData(){
  const f = await getFile("checkouts.yml", S.readRef, true).catch(() => null); if (!f) return [];
  try { return (window.jsyaml.load(f.text) || {}).checkouts || []; } catch (e) { return []; }
}
async function checkinCard(){
  const cos = await checkoutsData(), rows = [];
  for (const c of cos) for (const r of c.rueckgaben || []) rows.push(`<li><div><b>${esc(c.id)}</b> <span class="w">· ${esc(r.art)} vom ${esc(deDate(r.datum))} · ${r.befunde || 0} Befunde</span></div><button class="btn" data-act="checkin" data-f="${esc(r.ordner)}">Rückgabe ansehen</button></li>`);
  return rows.length ? `<div class="card" style="margin-top:16px"><b>Rückgaben vom Gegenlesen</b><p class="dim" style="margin:2px 0 4px">Eingecheckte Rückgaben ansehen. Einchecken und Übernehmen von Aufbau-Änderungen geht im Chat mit GhostWriter.</p><ul style="margin:0;padding-left:18px">${rows.slice(-4).reverse().join("")}</ul></div>` : "";
}
async function checkinData(folder){
  if (!/^checkouts\/GW-[A-Z0-9]{4}\/rueckgabe-[\d-]+$/.test(folder)) throw {message:"Ungültige Angabe."};
  const report = window.jsyaml.load((await getFile(folder + "/rueckgabe.yml", S.readRef, true)).text) || {}, cos = await checkoutsData(), entry = cos.find(c => c.id === report.kennung) || {};
  const ended = (entry.status || "ausgecheckt") !== "ausgecheckt", numbers = new Map(chapters().flatMap((c, ci) => (c.sections || []).map((s, si) => [s.id, `${ci + 1}.${si + 1}`])));
  const kinds = {docx:"Word-Datei (DOCX)", pdf:"PDF", scan:"Scan oder Foto der Ausdrucke"};
  const aufbauText = a => { const n = numbers.get(a.abschnitt) || ""; return a.art === "neu" ? `neuer Abschnitt „${a.titel}“ in Kapitel ${a.kapitel || "?"}${a.hinter ? " nach " + (numbers.get(a.hinter) || "?") : " am Anfang"} (${a.absaetze} Absätze)` : a.art === "geloescht" ? `Abschnitt ${n} „${a.titel}“ fehlt in der Rückgabe (gelöscht?)` : a.art === "verschoben" ? `Abschnitt ${n} „${a.titel}“ verschoben: in Kapitel ${a.kapitel} ${a.hinter ? "nach " + (numbers.get(a.hinter) || "?") : "an den Anfang"}` : `Abschnitt ${n} umbenannt: „${a.alt}“ → „${a.neu}“`; };
  const aufbau = report.aufbau || [], notes = (report.nicht_uebernommen || []).map(x => "Nicht übernommen: " + x);
  ["vergleich", "zuordnung_abschnitte", "hinweis"].forEach(k => { if (report[k]) notes.push(String(report[k])); });
  let stats = `${report.befunde || 0} Befunde · ${report.kommentare || 0} Kommentare` + (aufbau.length ? ` · ${aufbau.length} Aufbau-Änderungen` : "");
  return Object.assign(base(), {RET_ID:report.kennung || "", RET_KIND_TEXT:(kinds[report.art] || report.art) + (report.programm && report.programm !== "unbekannt" ? " · " + report.programm : ""), RET_DATE_TEXT:deDate(report.datum), RET_STATS_TEXT:stats,
    RET_LATE_TEXT:report.spaet ? `Späte Rückgabe: Der Checkout ist ${report.checkout_status}; Zwischenänderungen erscheinen als Frage.` : "", RET_FOLDER:folder, RET_FINDINGS_FILE:"",   // Befunde durchsehen (hinweise.py collect) läuft im Chat
    RET_END_ARGS:ended ? "" : JSON.stringify({id:report.kennung}), RET_CAN_APPLY:ended ? "1" : "", RET_APPLY_HINT:ended || !aufbau.length ? "" : "Der Checkout läuft noch: erst beenden, dann lassen sich Aufbau-Änderungen übernehmen.",
    NOTES:notes.map(N_TEXT => ({N_TEXT})), PAGES:(report.seiten || []).map(p => ({P_TEXT:`Seite ${p.seite}: ` + (p.zuordnung === "qr" ? `Kapitel ${p.kapitel || "?"} (QR)` : "unbekannt")})),
    QUESTIONS:(report.offene_fragen || []).map(Q_TEXT => ({Q_TEXT})), AUFBAU:aufbau.map(a => ({A_ID:a.id, A_TEXT:aufbauText(a), A_STATE:a.status || "offen"}))});
}
async function reviewCard(){
  let files = []; try { files = await reviewFiles(); } catch (e) {}
  if (!files.length) return "";
  const rows = [];
  for (const f of files.slice(-3).reverse()){
    try { const {data} = await reviewLoad("editorial/" + f), all = reviewEntries(data), done = all.filter(([, e]) => (e.entscheidung || "offen") !== "offen").length;
      rows.push(`<li><div><b>${esc(f.replace(/^durchsicht-|\.yml$/g, ""))}</b> <span class="w">· ${done} von ${all.length} entschieden${all.length - done ? `, ${all.length - done} offen` : ""}</span></div><button class="btn" data-act="review" data-f="${esc("editorial/" + f)}">${all.length - done ? "Weitermachen" : "Ansehen"}</button></li>`); } catch (e) {}
  }
  return rows.length ? `<div class="card" style="margin-top:16px"><b>Hinweisdurchsicht</b><p class="dim" style="margin:2px 0 4px">Änderungsvorschläge aus der Prüfung, Eintrag für Eintrag entscheiden. Jede Antwort wird sofort als kleiner Nachtrag gespeichert; ins Manuskript kommt nichts von selbst.</p><ul class="chk">${rows.join("")}</ul></div>` : "";
}
function entryPatch(text, id, pairs){
  // nur die Zeilen dieses Eintrags (`- id: <id>`) ändern, der Rest der Datei bleibt Zeichen für Zeichen
  const L = text.split("\n"), i = L.findIndex(l => l === "- id: " + id); if (i < 0) throw {message:`Eintrag ${id} nicht gefunden.`};
  let j = i + 1; while (j < L.length && (L[j].startsWith("  ") || L[j] === "")) j++;
  const blk = L.slice(i, j), setKey = (key, val) => {
    const dumped = window.jsyaml.dump({[key]:val}, {lineWidth:100}).replace(/\n$/, "").split("\n").map(l => "  " + l);
    const k = blk.findIndex(l => l.startsWith("  " + key + ":"));
    if (k >= 0){ let e = k + 1; while (e < blk.length && /^    /.test(blk[e])) e++; blk.splice(k, e - k, ...dumped); } else { let end = blk.length; while (end > 1 && blk[end - 1] === "") end--; blk.splice(end, 0, ...dumped); }
  };
  Object.entries(pairs).forEach(([k, v]) => setKey(k, v));
  return [...L.slice(0, i), ...blk, ...L.slice(j)].join("\n");
}
function reviewSet(text, id, decision, neu, variant){
  const pairs = {entscheidung:decision}; if (neu != null) pairs.neu = neu; if (variant) pairs.variante = variant;
  const out = entryPatch(text, id, pairs);
  const a = window.jsyaml.load(text), b = window.jsyaml.load(out), ea = reviewEntries(a), eb = reviewEntries(b);
  const same = ea.length === eb.length && ea.every(([g, e], k) => eb[k][0] === g && (e.id === id ? true : JSON.stringify(e) === JSON.stringify(eb[k][1])));
  const t = eb.find(([, e]) => e.id === id);
  if (!same || !t || t[1].entscheidung !== decision || (neu != null && t[1].neu !== neu)) throw {message:"Die Durchsichtsdatei ließ sich nicht sicher ändern; bitte im Chat mit GhostWriter entscheiden."};
  return out;
}
function flash(kind, html){
  S.msg = {kind, html}; const old = document.querySelector("#app .note"), box = msgBox();
  if (old) old.outerHTML = box; else if ($("gw")) $("gw").insertAdjacentHTML("beforebegin", box);
}
async function reviewAsk(d){
  // „Frage stellen“ (#609, #630): entscheidet nichts; Claude antwortet mit dem Eintrag als Zusammenhang, die Karte bleibt offen
  try {
    const file = String(d.file || ""); if (!/^editorial\/durchsicht-[^/]+\.yml$/.test(file)) throw {message:"Ungültige Angabe."};
    const question = String(d.question || "").trim(); if (!question) throw {message:"Bitte eine Frage eingeben."};
    if (!S.sample) throw {message:"Claude ist in dieser App nicht verfügbar. Stelle die Frage im Chat mit GhostWriter."};
    const {data} = await reviewLoad(file), e = (reviewEntries(data).find(([, x]) => x.id === d.entry) || [])[1];
    if (!e) throw {message:`Eintrag ${d.entry} nicht gefunden.`};
    flash("info", `<span class="spin"></span> Claude antwortet …`);
    const ctx = [`Hinweis ${e.id} (${e.abschnitt || ""}, ${e.art || ""}): ${e.grund || ""}`, e.alt ? `Alter Wortlaut: ${e.alt}` : "", e.neu ? `Vorschlag: ${e.neu}` : "", (e.varianten || []).length ? "Varianten: " + e.varianten.map((v, i) => `${i + 1}) ${v}`).join(" · ") : "", e.kontext ? `Umfeld: ${e.kontext}` : "", e.frage ? `Frage an den Autor: ${e.frage}` : ""].filter(Boolean).join("\n");
    const r = await S.sample([{role:"user", content:`Du hilfst einem Autor bei einem Prüfhinweis zu seinem Buch. Antworte auf Deutsch, knapp, in Alltagssprache, ohne Datei- oder Werkzeugnamen. Entscheide nichts und behaupte nicht, etwas gespeichert zu haben.\n\n${ctx}\n\nFRAGE DES AUTORS:\n${question}`}], {cache:false});
    flash("ok", `<b>Antwort zu ${esc(d.entry)}:</b><div style="margin-top:6px">${md(r.text || "")}</div><div class="dim" style="margin-top:6px">Es wurde nichts entschieden und nichts gespeichert.</div>`);
  } catch (e) { flash("err", "<b>Keine Antwort.</b> " + esc(errText(e))); }
}
async function reviewDecide(d){
  // nacheinander abarbeiten, damit schnelle Klicks sich nicht überschreiben
  S.reviewChain = (S.reviewChain || Promise.resolve()).then(async () => {
    try {
      const file = String(d.file || ""), decision = d.decision;
      if (!/^editorial\/durchsicht-[^/]+\.yml$/.test(file) || !REVIEW_DECISIONS.includes(decision)) throw {message:"Ungültige Angabe."};
      if (decision === "geändert" && d.variant == null && !String(d.new || "").trim()) throw {message:"Bei „geändert“ gehört die eigene Fassung dazu."};
      const work = await prepareWork(); S.readRef = work;
      const {text, data} = await reviewLoad(file), e = (reviewEntries(data).find(([, x]) => x.id === d.entry) || [])[1];
      if (String(d.entry).startsWith(R_PREFIX)) return reviewGroup(file, text, data, String(d.entry).slice(R_PREFIX.length), decision);
      if (!e) throw {message:`Eintrag ${d.entry} nicht gefunden.`};
      if (e.umgesetzt) throw {message:`${d.entry} ist schon umgesetzt.`};
      let variant = 0, wording = decision === "geändert" ? String(d.new || "").trim() : (typeof d.new === "string" ? d.new : null);
      if (d.variant != null){   // #473: Variante N wählen = „geändert“ mit dem Wortlaut der Variante (wie hinweise.decide --variant)
        variant = Number(d.variant); const opts = e.varianten || [];
        if (!(variant >= 1 && variant <= opts.length)) throw {message:`${d.entry} hat ${opts.length} Varianten; Variante ${d.variant} gibt es nicht.`};
        wording = String(opts[variant - 1]);
      }
      if (decision === "geändert" && !variant){ const why = notReplacement(Object.assign({}, e, {neu:wording, ersatz_bestaetigt:false, streichen:false}));
        if (why) throw {message:`${why}. Die Antwort auf die Frage ist kein neuer Wortlaut; bitte den neuen Satz selbst eintragen oder im Chat mit GhostWriter entscheiden (#675).`}; }
      const out = reviewSet(text, d.entry, decision, wording, variant);
      const r = await commit([{path:file, content:out}], `Hinweisdurchsicht: ${d.entry} ${decision}`, {action:"notes_review.decide"});
      setReview(file, out);
      const all = reviewEntries(window.jsyaml.load(out)), open = all.filter(([, x]) => (x.entscheidung || "offen") === "offen").length;
      const msg = `<b>${esc(d.entry)}: ${esc(decision)}</b> – gespeichert. ${open ? `Noch ${open} offen.` : "Alle Einträge entschieden. Umsetzen prüfen zeigt, was ins Manuskript kommen kann."}`;
      if (open + 1 >= R_STAGE_MIN && !S.reviewAll){ S.msg = {kind:r.pr || r.nothing ? "ok" : "warn", html:msg}; return show("review", file); }   // Stufen: nächste Karte/Stufe zeigen
      flash(r.pr || r.nothing ? "ok" : "warn", msg);
    } catch (e) { flash("err", "<b>Nicht gespeichert.</b> " + esc(errText(e))); }
  });
  return S.reviewChain;
}
// #675 (wie hinweise.not_replacement): Antwort, Anweisung, Liste oder Frage in `neu` ist kein Ersatztext für `alt`
const R_INSTR = /(→|->|=>)|\b(?:entsprechend|bitte|überall|jeweils)\b[\s\S]*\b(?:ändern|anpassen|angleichen|ergänzen|umschreiben|streichen|einfügen|ersetzen|korrigieren)\b/i,
  R_LIST = /^\s*(?:[-*•]\s|\d+[.)]\s|\d{3,4}\s*[:–-])/, R_Q = /\?[\s"„“»«'’)\]]*$/;
function notReplacement(e){
  const neu = String(e.neu || ""), alt = String(e.alt || ""), words = t => t.split(/\s+/).filter(Boolean).length;
  if (!neu || e.streichen || e.ersatz_bestaetigt) return "";
  if (e.antwort && neu.trim() === String(e.antwort).trim()) return "„neu“ ist die Antwort auf die Frage";
  if (R_Q.test(neu) && !R_Q.test(alt)) return "„neu“ ist eine Frage";
  if (R_INSTR.test(neu) && !R_INSTR.test(alt)) return "„neu“ sieht nach einer Anweisung aus";
  const lines = neu.split("\n").filter(l => l.trim()), altLines = alt.split("\n").filter(l => l.trim()).length;
  if (lines.length > Math.max(1, altLines) && lines.some(l => R_LIST.test(l))) return "„neu“ ist eine Liste bzw. Zeitleiste";
  if (words(alt) >= 6 && words(neu) <= 2 && neu.length * 4 < alt.length) return "„neu“ ist viel kürzer als „alt“ (eher eine Antwort als ein Ersatz)";
  return "";
}
const rProposal = e => !!(e.alt && e.neu && e.neu !== e.alt && e.section_id !== "book" && rSev(e) !== "blockierend" && !(e.varianten || []).length && !notReplacement(e));
async function reviewGroup(file, text, data, key, decision, gering){
  // Gruppenentscheidung wie hinweise.decide_group / decide_gering: ja = Einträge mit Vorschlag annehmen, nein = alle lassen; ein Commit
  if (!["ja", "nein"].includes(decision)) throw {message:"Für eine Gruppe gilt nur ja (wie vorgeschlagen) oder nein (alle lassen)."};
  const all = reviewEntries(data).map(x => x[1]), keys = await rGroupKeys(all);
  const hits = all.filter(e => rOpen(e) && (gering ? rSev(e) === "gering" : keys.get(e) === key && !["blockierend", "gering"].includes(rSev(e))));
  const todo = hits.filter(e => gering || decision === "nein" || rProposal(e)), skipped = hits.length - todo.length;
  if (!hits.length) throw {message:`${gering ? "Geringes" : "Gruppe " + key} nicht gefunden oder schon entschieden.`};
  if (!todo.length) throw {message:"Kein Eintrag der Gruppe hat einen eindeutigen Vorschlag; bitte einzeln ansehen."};
  let out = text; for (const e of todo) out = entryPatch(out, e.id, {entscheidung:gering ? "nein" : decision});
  const back = reviewEntries(window.jsyaml.load(out)), ids = new Set(todo.map(e => e.id));
  if (back.length !== all.length || back.some(([, e]) => ids.has(e.id) ? e.entscheidung !== (gering ? "nein" : decision) : false)) throw {message:"Die Durchsichtsdatei ließ sich nicht sicher ändern; bitte im Chat mit GhostWriter entscheiden."};
  const r = await commit([{path:file, content:out}], `Hinweisdurchsicht: ${gering ? "Geringes gelassen" : "Gruppe " + key + " " + decision} (${todo.length})`, {action:"notes_review.decide"});
  setReview(file, out);
  S.msg = {kind:r.pr || r.nothing ? "ok" : "warn", html:`<b>${gering ? "Geringes" : "Gruppe"}: ${todo.length} Einträge ${decision === "ja" && !gering ? "angenommen" : "gelassen"}</b>${skipped ? `, ${skipped} ohne eindeutigen Vorschlag übersprungen` : ""}.`};
  return show("review", file);
}
const W_LEAD = /^(?:\s|…|\.\.\.)+/, W_TRAIL = /(?:\s|…|\.\.\.)+$/;
function wording(text, alt, neu){
  // (alt, neu), wie sie im Text zu ersetzen sind, oder null (wie hinweise.wording, #522): erst unverändert, sonst ohne
  // einfassende Auslassungspunkte und Leerzeichen aus dem Befund; bei neu fallen nur dieselben Ränder weg
  if (text.split(alt).length - 1 === 1) return [alt, neu];
  const lead = W_LEAD.exec(alt), trail = W_TRAIL.exec(alt), a = alt.slice(lead ? lead[0].length : 0, trail ? trail.index : alt.length);
  if (!a || text.split(a).length - 1 !== 1) return null;
  let n = neu; if (lead) n = n.replace(W_LEAD, ""); if (trail) n = n.replace(W_TRAIL, "");
  return [a, n];
}
function wordingNotFound(e, ms, secs){
  // Grund, warum der Wortlaut im genannten Abschnitt nicht eindeutig steht: mehrfach, woanders oder gar nicht (#522)
  const hits = ms.split(e.alt).length - 1;
  if (hits > 1) return ["⛔", `alter Wortlaut kommt ${hits}-mal in ${e.abschnitt} vor: die Stelle von Hand wählen`];
  const places = secs.filter(v => v.s.id !== e.section_id).filter(v => { const f = cached(v.s.path); return f && wording(msOf(f.text), e.alt, e.neu) !== null; }).map(v => `${chapters().indexOf(v.c) + 1}.${v.c.sections.indexOf(v.s) + 1}`);
  if (places.length === 1) return ["⚠️", `Wortlaut steht in ${places[0]} statt ${e.abschnitt}: Abschnitt im Befund prüfen, von Hand umsetzen`];
  if (places.length) return ["⚠️", `Wortlaut steht in mehreren anderen Abschnitten (${places.join(", ")}): von Hand umsetzen`];
  return ["⛔", "Wortlaut nicht gefunden: Text oder Befund prüfen"];
}
function reviewPlanItems(data, secs){
  // wie hinweise.plan: [{mark, why, e, x}] für alle entschiedenen, noch nicht umgesetzten Einträge
  const out = [];
  for (const [, e] of reviewEntries(data)){
    if (e.umgesetzt || !["ja", "geändert"].includes(e.entscheidung)) continue;
    const x = secs.find(v => v.s.id === e.section_id), f = x && cached(x.s.path), ms = f ? msOf(f.text) : "";
    let mark, why;
    if (e.section_id === "book"){ mark = "⚠️"; why = "buchweit: von Hand in den betroffenen Abschnitten umsetzen"; }
    else if (!x){ mark = "⛔"; why = "Abschnitt gibt es nicht mehr"; }
    else if (!e.alt || !e.neu){ mark = "⚠️"; why = e.antwort ? "Antwort des Autors ohne neuen Wortlaut: von Hand umsetzen" : "ohne alten Wortlaut oder Vorschlag: von Hand umsetzen"; }
    else if (x.c.status === "approved"){ mark = "⛔"; why = `Kapitel ${String(e.abschnitt).split(".")[0]} ist abgeschlossen: erst wieder öffnen`; }
    else if (front(f.text).status === "approved"){ mark = "⛔"; why = `Abschnitt ${e.abschnitt} ist abgeschlossen: erst wieder öffnen`; }
    else if (wording(ms, e.alt, e.neu) === null){ [mark, why] = wordingNotFound(e, ms, secs); }
    else if (notReplacement(e)){ mark = "⚠️"; why = `${notReplacement(e)}: von Hand umsetzen oder den neuen Wortlaut eintragen`; }   // #675
    else { mark = "✅"; why = "umsetzbar"; }
    out.push({mark, why, e, x});
  }
  return out;
}
const planLines = items => items.map(({mark, why, e}) => `<div>${mark} <code>${esc(e.id)}</code> · ${esc(e.abschnitt)} · ${esc(why)}</div>`).join("");
async function reviewPlan(d){
  try {
    busy("Wird geprüft …");
    const file = String(d.file || ""), {data} = await reviewLoad(file), secs = allSecs();
    await loadSecFiles(secs, "Wird geprüft");
    const items = reviewPlanItems(data, secs), ok = data.gesperrt ? 0 : items.filter(i => i.mark === "✅").length;
    S.msg = {kind:"info", html:`<b>Umsetzen prüfen</b> (ändert noch nichts)${data.gesperrt ? `<div>⛔ Durchsicht gesperrt: ${esc(data.gesperrt)} – es wird nichts umgesetzt.</div>` : ""}${items.length ? planLines(items) : "<div>Keine entschiedenen Einträge zum Umsetzen.</div>"}${ok ? `<div style="margin-top:8px"><button class="btn pri" data-act="reviewapply" data-f="${esc(file)}">${ok === 1 ? "Den umsetzbaren Eintrag" : `Die ${ok} umsetzbaren Einträge`} ins Manuskript umsetzen</button></div><div class="dim" style="margin-top:6px">Nur ✅-Einträge werden umgesetzt, in einem Commit auf dem Arbeits-Branch (Manuskripte, Durchsicht, Befundstatus). Ins Buch kommt es erst über „Änderungen übernehmen“.</div>` : ""}`};
  } catch (e) { S.msg = failMsg(e); }
  show("review", d.file);
}
const SENTENCE = /[^.!?…\n]+(?:[.!?…]+[»«“”"')\]]*|\n|$)/g;
function contextOf(text, neu){
  // betroffener Satz mit bis zu zwei Sätzen davor und danach (wie hinweise.context)
  const start = text.indexOf(neu); if (start < 0 || text.indexOf(neu, start + 1) >= 0) return neu;
  const end = start + neu.length, spans = [...text.matchAll(SENTENCE)].filter(m => m[0].trim()).map(m => [m.index, m.index + m[0].length]);
  let first = spans.findIndex(([, b]) => b > start); if (first < 0) first = 0;
  let last = spans.findIndex(([, b]) => b >= end); if (last < 0) last = spans.length - 1;
  return text.slice(spans[Math.max(0, first - 2)][0], spans[Math.min(spans.length - 1, last + 2)][1]).replace(/\s+/g, " ").trim();
}
async function reviewApply(d){
  busy("Wird umgesetzt …");
  try {
    const file = String(d.file || ""); if (!/^editorial\/durchsicht-[^/]+\.yml$/.test(file)) throw {message:"Ungültige Angabe."};
    const work = await prepareWork(); await loadBookData(work); S.readRef = work;
    const {text:dtext, data} = await reviewLoad(file), secs = allSecs();
    if (data.gesperrt) throw {message:`Durchsicht gesperrt: ${data.gesperrt}. Nichts umgesetzt.`};   // #675
    await loadSecFiles(secs, "Wird geprüft");
    const items = reviewPlanItems(data, secs), files = {}, orig = {[file]:dtext}, applied = [], skipped = [], ctx = [], notes = [];
    const MARK = "\n## Manuskript\n";
    for (const it of items){
      if (it.mark !== "✅" || notReplacement(it.e)){ skipped.push(it.mark === "✅" ? Object.assign({}, it, {mark:"⚠️", why:notReplacement(it.e)}) : it); continue; }   // #675: zweite Sicherung
      const e = it.e, path = e.datei || it.x.s.path;
      if (!(path in files)){ const t = (await getFile(path, work, true)).text; files[path] = t; orig[path] = t; }
      const t = files[path], k = t.indexOf(MARK);
      if (k < 0){ skipped.push({mark:"⛔", why:"Manuskript nicht gefunden", e}); continue; }
      const head = t.slice(0, k + MARK.length), body = t.slice(head.length), w = wording(body, e.alt, e.neu);
      if (w === null){ skipped.push({mark:"⛔", why:"Wortlaut nicht mehr eindeutig (nach einer früheren Umsetzung)", e}); continue; }
      const nb = body.replace(w[0], () => w[1]); files[path] = head + nb; applied.push(e); ctx.push([e, contextOf(nb, w[1])]);
    }
    if (!applied.length){ S.msg = {kind:"info", html:`<b>Nichts umgesetzt.</b>${planLines(skipped) || "<div>Keine umsetzbaren Einträge.</div>"}`}; return show("review", file); }
    // Durchsicht: umgesetzt: true
    let nd = dtext; applied.forEach(e => { nd = entryPatch(nd, e.id, {umgesetzt:true}); });
    const a0 = reviewEntries(window.jsyaml.load(dtext)), a1 = reviewEntries(window.jsyaml.load(nd)), done = new Set(applied.map(e => e.id));
    if (a0.length !== a1.length || !a1.every(([, e], i) => done.has(e.id) ? e.umgesetzt === true : JSON.stringify(e) === JSON.stringify(a0[i][1]))) throw {message:"Die Durchsichtsdatei ließ sich nicht sicher ändern; bitte im Chat mit GhostWriter umsetzen."};
    files[file] = nd;
    // Befundstatus zurückschreiben: umgesetzt → erledigt, nein → entschieden (nur Befunde mit Status „offen“)
    const targets = {};
    for (const [, e] of a1){ const st = e.umgesetzt ? "erledigt" : e.entscheidung === "nein" ? "entschieden" : null; if (st && e.befund){ const [bf, fid] = String(e.befund).split("#"); (targets[bf] = targets[bf] || {})[fid] = st; } }
    for (const [bf, ids] of Object.entries(targets)){
      try {
        const t = (await getFile(bf, work, true)).text, bd = window.jsyaml.load(t) || {}, hit = (bd.befunde || []).filter(b => b.id in ids && b.status === "offen");
        if (!hit.length) continue;
        let out = t; hit.forEach(b => { out = entryPatch(out, b.id, {status:ids[b.id]}); });
        const nb = (window.jsyaml.load(out) || {}).befunde || [], hs = new Set(hit.map(b => b.id));
        if (nb.length !== (bd.befunde || []).length || !nb.every((b, i) => hs.has(b.id) ? b.status === ids[b.id] : JSON.stringify(b) === JSON.stringify(bd.befunde[i]))){ notes.push(bf); continue; }
        files[bf] = out; orig[bf] = t;
      } catch (e) { /* Befunddatei fehlt oder ist anders aufgebaut: nichts zurückschreiben */ }
    }
    const r = await commit(changed(files, orig), `Hinweisdurchsicht: ${applied.length} ${applied.length === 1 ? "Eintrag" : "Einträge"} ins Manuskript umgesetzt`, {action:"notes_review.apply"});
    setReview(file, nd);
    S.msg = savedMsg(`${applied.length} ${applied.length === 1 ? "Eintrag" : "Einträge"} umgesetzt, ${skipped.length} nicht umgesetzt.`, r);
    S.msg.html += `<div style="margin-top:6px"><b>Im Zusammenhang neu lesen:</b></div>${ctx.map(([e, c]) => `<div><code>${esc(e.id)}</code> · ${esc(e.abschnitt)}: ${esc(c)}</div>`).join("")}`
      + (skipped.length ? `<div style="margin-top:6px"><b>Nicht umgesetzt:</b></div>${planLines(skipped)}` : "")
      + (notes.length ? `<div class="dim" style="margin-top:6px">Befundstatus nicht zurückgeschrieben (Datei anders aufgebaut): ${esc(notes.join(", "))}</div>` : "")
      + `<div class="dim" style="margin-top:6px">Nachprüfung (Schlusskorrektur, Qualitätsprüfung) und erneutes Abschließen der Kapitel sind eigene Schritte und gehen weiter im Chat.</div>`;
  } catch (e) { S.msg = failMsg(e); }
  show("review", d.file);
}

