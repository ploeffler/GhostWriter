/* Hintergrund-Warteschlange (#478): Aufträge request-NNN.yml (Ordner research je Abschnitt, matter/research, jobs) wie scripts/jobs.py und
   queue_view.py. „Abbrechen“ löscht nichts (die App kann keine Dateien löschen): Der Auftrag wird als abgebrochen markiert und läuft nicht mehr. */
const JOB_TYPES = {research:"Recherche", analysis:"Analyse", colorize:"Colorieren", import:"Import"};
async function queueFiles(){
  const ref = S.readRef, out = [], dirs = [];
  for (const c of chapters()){ for (const e of await listDir(`${c.path}/research`, ref)) if (e.type === "dir") dirs.push(`${c.path}/research/${e.name}`); }
  for (const e of await listDir("matter/research", ref)) if (e.type === "dir") dirs.push(`matter/research/${e.name}`);
  dirs.push("jobs");
  const lists = await pool(dirs, 6, async d => ({d, list:await listDir(d, ref)}));
  for (const l of lists.filter(Boolean)) for (const e of l.list) if (/^request-\d+\.yml$/.test(e.name)) out.push(`${l.d}/${e.name}`);
  return {files:out, dirs};
}
function jobOrder(){
  const m = new Map(); chapters().forEach((c, ci) => (c.sections || []).forEach((s, si) => m.set(s.id, `1|${String(ci).padStart(4, "0")}|${String(si).padStart(4, "0")}`)));
  return id => m.get(id) || "8|0000|0000";
}
async function queueJobs(){
  const {files, dirs} = await queueFiles(), order = jobOrder();
  const jobs = (await pool(files, 8, async path => {
    let data = {}; try { data = window.jsyaml.load((await getFile(path, S.readRef, true)).text) || {}; } catch (e) { return {path, data:{}, state:"failed", type:"research", sid:"", error:"Auftrag nicht lesbar", key:"1|9"}; }
    const sid = String(data.section_id || (/research\/([^/]+)\/request-/.exec(path) || [])[1] || "");
    return {path, data, state:jobState(data), type:data.type || "research", sid, key:(data.priority === true ? "0" : "1") + "|" + order(sid) + "|" + String(data.requested_at || "") + "|" + path};
  })).filter(Boolean).sort((a, b) => a.key < b.key ? -1 : a.key > b.key ? 1 : 0);
  // after: Ziel auflösen, Ringe ignorieren (wie jobs.resolve_after); ein erledigtes (verschwundenes) Ziel blockiert nicht
  const byRel = new Map(jobs.map(j => [j.path, j])), pending = j => j.state === "open" || j.state === "waiting_budget";
  for (const j of jobs){
    j.after = null; const a = String(j.data.after || "").trim(); if (!a) continue;
    const t = byRel.get(a) || byRel.get(j.path.replace(/[^/]+$/, "") + (a.endsWith(".yml") ? a : a + ".yml"));
    if (!t || t === j) j.note = "Ziel von „after“ nicht mehr vorhanden: " + a; else j.after = t;
  }
  for (const j of jobs){ const seen = new Set(); let k = j; while (k && !seen.has(k)){ seen.add(k); k = k.after; } if (k === j){ [...seen].forEach(m => { m.note = "Ring bei „after“ ignoriert"; }); [...seen].forEach(m => { m.after = null; }); } }
  jobs.forEach(j => { j.blockedBy = j.after && pending(j.after) ? j.after.path : ""; });
  const ordered = [], seen = new Set(), emit = j => { if (seen.has(j)) return; seen.add(j); if (j.after) emit(j.after); ordered.push(j); };
  jobs.forEach(emit);
  return {jobs:ordered, dirs};
}
function secLabel(sid){ const x = allSecs().find(v => v.s.id === sid); return x ? `${chapters().indexOf(x.c) + 1}.${x.c.sections.indexOf(x.s) + 1} ${x.s.title}` : sid; }
function jobTitle(j){
  const kind = JOB_TYPES[j.type] || j.type, extra = j.data[j.type] && typeof j.data[j.type] === "object" ? j.data[j.type] : {};
  const where = j.type === "research" ? secLabel(j.sid) : String(extra.kind || extra.folder || extra.step || "");
  return where ? `${kind} · ${where}` : kind;
}
function jobDetail(j){ if (j.type === "research") return String(j.data.question || ""); const x = j.data[j.type] || {}; return Object.entries(x).filter(([k, v]) => ["kind", "scope", "folder", "file", "step"].includes(k) && v).map(([k, v]) => `${k}: ${v}`).join(", "); }
const utcText = iso => { const m = /(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(String(iso || "")); return m ? `${m[3]}.${m[2]}.${m[1]}, ${m[4]}:${m[5]} UTC` : ""; };
async function queueDone(dirs){
  // fertige, noch nicht übernommene Recherchen: Laufdatei mit `request:` im Kopf, die der Buch-Branch noch nicht hat
  if (!S.pr || S.readRef === S.book.branch) return [];
  const out = [];
  for (const d of dirs.filter(x => x !== "jobs")){
    const [mine, theirs] = await Promise.all([listDir(d, S.readRef), listDir(d, S.book.branch)]), have = new Set(theirs.map(e => e.name));
    for (const e of mine.filter(e => /^run-\d+\.md$/.test(e.name) && !have.has(e.name))){
      try { const t = (await getFile(`${d}/${e.name}`, S.readRef, true)).text; if (/^request:\s*request-\d+/m.test(t.slice(0, 700))) out.push({d, name:e.name}); } catch (err) {}
    }
  }
  return out;
}
async function queueData(){
  const {jobs, dirs} = await queueJobs(), done = await queueDone(dirs);
  const row = j => ({J_TITLE:jobTitle(j), J_DETAIL:j.state === "failed" ? String(j.data.error || j.error || "Auftrag nicht lesbar") : jobDetail(j), J_WHEN_TEXT:"", J_PRIORITY_TEXT:"", J_BLOCKED_TEXT:"", J_NOTE:j.note || "", J_PRIO_DISABLED:"", J_ARGS:JSON.stringify({request:j.path})});
  const pending = [], failed = [];
  for (const j of jobs){
    const r = row(j);
    if (j.state === "failed"){ r.J_WHEN_TEXT = j.data.failed_at ? "fehlgeschlagen " + utcText(j.data.failed_at) : ""; failed.push(r); continue; }
    r.J_STATE_TEXT = j.state === "waiting_budget" ? "wartet auf Bestätigung (KI-Budget knapp)" : j.blockedBy ? "wartet auf einen anderen Auftrag" : "wartet";
    if (j.blockedBy) r.J_BLOCKED_TEXT = "Erst nach " + j.blockedBy;
    r.J_WHEN_TEXT = j.data.requested_at ? "eingereicht " + utcText(j.data.requested_at) : "";
    if (j.data.priority === true){ r.J_PRIORITY_TEXT = "vorgezogen"; r.J_PRIO_DISABLED = "disabled"; }
    pending.push(r);
  }
  const doneRows = done.map(x => ({J_TITLE:"Recherche · " + secLabel((/research\/([^/]+)$/.exec(x.d) || [])[1] || ""), J_DETAIL:"Ergebnis liegt im Änderungspaket"}));
  const total = pending.length + failed.length + doneRows.length;
  const d = Object.assign(base(), {QUEUE_BOOK:shortTitle(), QUEUE_COUNT_TEXT:total ? plural(total, "Auftrag", "Aufträge") : "keine Aufträge", QUEUE_EMPTY:total ? "" : "1", PENDING:pending, FAILED:failed, DONE:doneRows});
  return d;
}
async function queueChange(kind, d){
  busy(kind === "prioritize" ? "Auftrag wird vorgezogen …" : kind === "retry" ? "Auftrag wird wieder geöffnet …" : "Auftrag wird abgebrochen …");
  try {
    const path = String(d.request || ""); if (!/^(chapters\/[^/]+\/research\/[^/]+|matter\/research\/[^/]+|jobs)\/request-\d+\.yml$/.test(path)) throw {message:"Ungültige Angabe."};
    const work = await prepareWork(); await loadBookData(work);
    const t = (await getFile(path, work, true).catch(() => { throw {message:"Der Auftrag ist nicht mehr da (vielleicht schon erledigt)."}; })).text, data = window.jsyaml.load(t) || {};
    if (kind !== "retry" && jobState(data) === "failed") throw {message:"Dieser Auftrag läuft nicht mehr; vorziehen oder abbrechen geht nur bei wartenden Aufträgen."};
    if (kind === "retry" && jobState(data) !== "failed") throw {message:"Erneut versuchen geht nur bei fehlgeschlagenen Aufträgen."};
    let out = t.replace(/\n*$/, "\n");
    if (kind === "retry"){   // #554/#596: error und failed_at entfernen, derselbe Auftrag ist wieder offen
      out = out.replace(/^error:.*(?:\n[ \t]+.*)*\n?/m, "").replace(/^failed_at:.*\n?/m, "");
      const back = window.jsyaml.load(out) || {};
      if (back.error || back.failed_at || JSON.stringify(Object.assign({}, back, {error:0, failed_at:0})) !== JSON.stringify(Object.assign({}, data, {error:0, failed_at:0}))) throw {message:"Die Auftragsdatei ließ sich nicht sicher ändern; nichts wurde gespeichert."};
      const r = await commit([{path, content:out}], `Warteschlange: ${path} erneut versucht`, {action:"queue.retry"});
      S.msg = savedMsg("Auftrag wieder geöffnet; er läuft beim nächsten Durchgang erneut (derselbe Auftrag, kein zweiter).", r);
      return show("queue");
    }
    if (kind === "prioritize") out = /^priority:.*$/m.test(out) ? out.replace(/^priority:.*$/m, "priority: true") : out + "priority: true\n";
    else out = out.replace(/^waiting:.*\n/m, "") + `error: Vom Benutzer in der App abgebrochen\nfailed_at: '${new Date().toISOString().replace(/\.\d+Z$/, "+00:00")}'\n`;
    const back = window.jsyaml.load(out) || {};
    if (kind === "prioritize" ? back.priority !== true : !back.error || JSON.stringify(Object.assign({}, back, {error:0, failed_at:0, waiting:0})) !== JSON.stringify(Object.assign({}, data, {error:0, failed_at:0, waiting:0}))) throw {message:"Die Auftragsdatei ließ sich nicht sicher ändern."};
    const r = await commit([{path, content:out}], kind === "prioritize" ? `Warteschlange: ${path} vorgezogen` : `Warteschlange: ${path} abgebrochen`, {action:"queue." + kind});
    S.msg = savedMsg(kind === "prioritize" ? "Auftrag vorgezogen." : "Auftrag abgebrochen.", r);
    if (kind === "cancel") S.msg.html += ` <span class="dim">Die App kann keine Dateien löschen: Der Auftrag steht jetzt als fehlgeschlagen und läuft nicht mehr. Ein schon laufender Auftrag lässt sich so nicht stoppen.</span>`;
  } catch (e) { S.msg = failMsg(e); }
  show("queue");
}

/* Veraltet-Markierung (#510, #592): Status, Freigabe und Fingerabdruck bleiben, der Text ändert sich nicht */
async function staleChange(kind, d){
  busy(kind === "mark" ? "Markierung wird gesetzt …" : "Markierung wird entfernt …");
  try {
    const x = allSecs().find(v => v.s.id === d.section_id); if (!x) throw {message:"Abschnitt nicht gefunden."};
    const reason = String(d.reason || "").split(/\s+/).filter(Boolean).join(" ");
    if (kind === "mark" && !reason) throw {message:"Bitte einen Grund angeben."};
    const work = await prepareWork(); await loadBookData(work);
    const t = (await getFile(x.s.path, work, true)).text, now = staleOf(t);
    if (kind === "clear" && !now) throw {message:"Der Abschnitt ist nicht als veraltet markiert."};
    const out = staleSet(t, kind === "mark" ? {since:new Date().toISOString().slice(0, 10), reason, source:String(d.source || "")} : null);
    if (msOf(out) !== msOf(t) || (kind === "mark" ? !staleOf(out) : staleOf(out))) throw {message:"Die Abschnittsdatei ließ sich nicht sicher ändern; nichts wurde gespeichert."};
    const r = await commit([{path:x.s.path, content:out}], kind === "mark" ? `${x.s.title}: als veraltet markiert` : `${x.s.title}: Veraltet-Markierung entfernt`, {action:"section." + kind + "_stale"});
    S.msg = savedMsg(kind === "mark" ? "Als veraltet markiert. Status und Freigabe bleiben." : "Markierung entfernt.", r);
  } catch (e) { S.msg = failMsg(e); }
  show("section", d.section_id);
}
async function staleList(){
  await loadSecFiles(allSecs(), "Veraltete Abschnitte werden gesucht");
  const rows = [];
  chapters().forEach((c, ci) => (c.sections || []).forEach((s, si) => { const st = staleOf((cached(s.path) || {}).text); if (st) rows.push(`<li><b>${ci + 1}.${si + 1} ${esc(s.title)}</b>: ${esc(staleHint(st))}</li>`); }));
  S.msg = {kind:"info", html:rows.length ? `<b>Veraltete Abschnitte (${rows.length}):</b><ul>${rows.join("")}</ul>` : "Kein Abschnitt ist als veraltet markiert."};
  return show(S.view === "section" ? "section" : S.view === "chapter" ? "chapter" : "project", S.view === "section" ? S.sec && S.sec.id : S.chap);
}

/* Hinweisdurchsicht (#367): editorial/durchsicht-*.yml – Eintrag für Eintrag entscheiden, jede Antwort als kleiner Nachtrag */
const REVIEW_DECISIONS = ["ja", "nein", "geändert"], CH_STATUS = {planned:"geplant", in_progress:"in Arbeit", ready_for_assembly:"bereit zum Zusammenführen", assembly:"im Zusammenführen", review:"in Prüfung", ready_for_approval:"bereit zum Abschluss", approved:"abgeschlossen"};
const reviewKey = n => { const m = /^durchsicht-(.+?)(?:-(\d+))?\.yml$/.exec(n); return m ? [m[1], +(m[2] || 1)] : [n.replace(/\.yml$/, ""), 0]; };   // wie hinweise.dialog_order
const reviewCmp = (a, b) => { const x = reviewKey(a), y = reviewKey(b); return x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : x[1] - y[1]; };
async function reviewFiles(){ return (await listDir("editorial", S.readRef)).filter(e => /^durchsicht-.+\.yml$/.test(e.name)).map(e => e.name).sort(reviewCmp); }
const reviewEntries = data => [...(data.ohne_autor || []).map(e => ["ohne_autor", e]), ...(data.autorenentscheidung || []).map(e => ["autorenentscheidung", e])];
const reviewState = e => e.umgesetzt ? "umgesetzt" : (e.entscheidung || "offen");
async function reviewLoad(file){
  // direkt nach einer eigenen Änderung gilt der eigene Stand (GitHub liefert sonst kurz noch den alten), danach der frische
  const at = (S.reviewAt || {})[file], mine = S.reviewText && S.reviewText[file];
  const text = (at && mine != null && Date.now() - at < 90000) ? mine : (await getFile(file, S.readRef, true)).text;
  return {text, data:window.jsyaml.load(text) || {}};
}
const setReview = (file, text) => { (S.reviewText = S.reviewText || {})[file] = text; (S.reviewAt = S.reviewAt || {})[file] = Date.now(); };
const reviewWhere = e => e.chapter_id ? "Kapitel " + String(e.abschnitt).split(".")[0] : e.abschnitt;
/* Stufen der Durchsicht (#570, #473) wie hinweise.stages/current: ab 12 offenen Einträgen nur die aktuelle Stufe */
const R_RANK = {blockierend:0, wesentlich:1, mittel:2, gering:3}, R_GROUP_MIN = 3, R_ROUND = 5, R_STAGE_MIN = 12, R_PREFIX = "gruppe:";
const rOpen = e => (e.entscheidung || "offen") === "offen" && !e.umgesetzt, rSev = e => e.schweregrad || "mittel";
async function rGroupKeys(list){   // Gruppenschlüssel: Art + Prüfsumme des bereinigten Musters (hier: eigene, stabile Kurzprüfsumme)
  const out = new Map();
  for (const e of list){
    let n = String(e.muster || e.grund || "").replace(/[\d"„“»«'‚‘’]+/g, "").toLowerCase().replace(/\s+/g, " ").trim();
    const b = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(n));
    out.set(e, `${e.art || ""}-${[...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("").slice(0, 6)}`);
  }
  return out;
}
async function reviewStages(data){
  const every = reviewEntries(data).map(x => x[1]), keys = await rGroupKeys(every), known = (data.themen || []).map(t => t.id), themed = e => known.includes(e.thema) && rSev(e) !== "blockierend";
  const counts = {}; for (const e of every) if (!["blockierend", "gering"].includes(rSev(e)) && !known.includes(e.thema)) counts[keys.get(e)] = (counts[keys.get(e)] || 0) + 1;
  const grouped = new Set(Object.keys(counts).filter(k => counts[k] >= R_GROUP_MIN)), middle = e => !["blockierend", "gering"].includes(rSev(e)) && !themed(e);
  const opened = every.filter(rOpen), groups = {};
  for (const e of opened) if (middle(e) && grouped.has(keys.get(e))) (groups[keys.get(e)] = groups[keys.get(e)] || []).push(e);
  const singles = opened.filter(e => middle(e) && !grouped.has(keys.get(e))).sort((a, b) => R_RANK[rSev(a)] - R_RANK[rSev(b)]);
  const done = every.filter(e => middle(e) && !grouped.has(keys.get(e)) && !rOpen(e)).length, rounds = [];
  for (let i = 0; i < singles.length; i += R_ROUND) rounds.push(singles.slice(i, i + R_ROUND));
  const titles = Object.fromEntries((data.themen || []).map(t => [t.id, t.titel])), themes = known.map(id => [id, titles[id], opened.filter(e => themed(e) && e.thema === id)]);
  const themeTotal = known.filter(id => every.some(e => themed(e) && e.thema === id)).length, openThemes = themes.filter(t => t[2].length);
  return {blocking:opened.filter(e => rSev(e) === "blockierend"), themes:openThemes, themeNo:themeTotal - openThemes.length + 1, themeTotal, groups, keys, rounds,
    gering:opened.filter(e => rSev(e) === "gering" && !themed(e)), open:opened.length, roundNo:Math.floor(done / R_ROUND) + 1, roundTotal:singles.length ? Math.ceil((done + singles.length) / R_ROUND) : 0,
    themeBlocking:Object.fromEntries(known.map(id => [id, every.filter(e => e.thema === id && rSev(e) === "blockierend").map(e => e.id)]))};
}
async function reviewCurrent(data, gering){
  const st = await reviewStages(data), left = `noch ${st.open} offen`;
  if (st.blocking.length) return {name:"blockierend", items:st.blocking, head:`Stufe 1 · Blockierendes, einzeln · ${st.blocking.length} offen · ${left}`, st};
  if (st.themes.length){
    const [tid, title, items] = st.themes[0], minor = items.filter(e => rSev(e) === "gering"), hidden = (minor.length && minor.length < items.length && !gering) ? minor : [], shown = items.filter(e => !hidden.includes(e));
    const refs = st.themeBlocking[tid] || [];
    return {name:"thema", items:shown, head:`Stufe 2 · Thema ${st.themeNo} von ${st.themeTotal}: ${title} · ${shown.length} offen${hidden.length ? ` (+ ${hidden.length} geringe zu diesem Thema)` : ""}${refs.length ? ` · Blockierendes dazu: ${refs.join(", ")} (Stufe 1)` : ""} · ${left}`, st};
  }
  const gk = Object.keys(st.groups);
  if (gk.length) return {name:"gruppen", items:gk.map(k => Object.assign({}, st.groups[k][0], {id:R_PREFIX + k, abschnitt:`${st.groups[k].length} Stellen`, chapter_status:"", frage:`Alle ${st.groups[k].length} Stellen: wie vorgeschlagen (ja) · alle lassen (nein)`, varianten:[], schweregrad:"", _group:true})), head:`Stufe 2 · Gleiche Muster · ${gk.length} Gruppen · ${left}`, st};
  if (st.rounds.length) return {name:"runde", items:st.rounds[0], head:`Stufe 3 · Runde ${st.roundNo} von ${st.roundTotal} · ${left}`, st};
  if (st.gering.length) return gering ? {name:"gering", items:st.gering, head:`Stufe 4 · Geringes · ${st.gering.length} offen`, st} : {name:"gering-zu", items:[], head:`Stufe 4 · ${st.gering.length} geringe Hinweise zugeklappt`, st};
  return {name:"fertig", items:[], head:"Alle Einträge entschieden", st};
}
async function reviewData(file){
  const {data} = await reviewLoad(file), all = reviewEntries(data), done = all.filter(([, e]) => (e.entscheidung || "offen") !== "offen").length;
  const [y, m, dd] = String(data.erstellt || "").split("-");
  const row = (e, author) => Object.assign({E_ID:e.id, E_WHERE:e.abschnitt, E_CHAPTER_TEXT:reviewWhere(e) + (e.chapter_status ? " · " + (CH_STATUS[e.chapter_status] || e.chapter_status) : ""), E_KIND:e.art || "",
    E_REASON:(e.schweregrad === "blockierend" ? "⛔ blockierend: " : "") + (e.grund || ""), E_CONTEXT:e.kontext || "", E_OLD:e.alt || "", E_NEW:e.neu || (e.streichen ? "(entfällt)" : ""), E_DECISION:reviewState(e)},
    author ? {E_PROPOSED:e.vorschlag_von === "assistent" ? "1" : "", E_VARIANTS_JSON:(e.varianten || []).length ? JSON.stringify(e.varianten.map(String)) : "", E_QUESTION:(e.frage || "") + (e.varianten || []).map((v, k) => ` · Variante ${k + 1}: ${v}`).join("") + (e.antwort ? ` · Antwort: ${e.antwort}` : "") + (notReplacement(e) ? ` · ⚠️ ${notReplacement(e)}: wird nicht automatisch umgesetzt` : "")} : {});
  const d = Object.assign(base(), {REVIEW_FILE:file, REVIEW_BOOK:data.buch || "", REVIEW_DATE_TEXT:dd ? `Stand ${dd}.${m}.${y}` : "", REVIEW_COUNT_TEXT:(data.gesperrt ? `⛔ Gesperrt: ${data.gesperrt} · ` : "") + `${all.length} Einträge · ${done} entschieden · ${all.length - done} offen`});
  const openCount = all.filter(([, e]) => rOpen(e)).length; S.reviewInfo = {file, staged:false, name:"", gering:0};
  if (openCount >= R_STAGE_MIN && !S.reviewAll){   // #570: nur die aktuelle Stufe
    const cur = await reviewCurrent(data, S.reviewGering); d.REVIEW_COUNT_TEXT = cur.head;
    S.reviewInfo = {file, staged:true, name:cur.name, gering:cur.st.gering.length};
    const ids = new Set(cur.items.map(e => e.id)), authorRows = cur.name === "gruppen" ? cur.items.map(e => row(e, true)) : (data.autorenentscheidung || []).filter(e => ids.has(e.id)).map(e => row(e, true));
    const auto = (data.ohne_autor || []).filter(e => ids.has(e.id)).map(e => row(e, false));
    if (auto.length) d.AUTO = auto;
    if (authorRows.length) d.AUTHOR = authorRows;
    if ((data.ausgelassen || []).length) d.SKIPPED = data.ausgelassen.map(x => ({SK_REF:x.befund, SK_REASON:x.grund}));
    return d;
  }
  if ((data.ohne_autor || []).length) d.AUTO = data.ohne_autor.map(e => row(e, false));
  if ((data.autorenentscheidung || []).length) d.AUTHOR = data.autorenentscheidung.map(e => row(e, true));
  if ((data.ausgelassen || []).length) d.SKIPPED = data.ausgelassen.map(x => ({SK_REF:x.befund, SK_REASON:x.grund}));
  return d;
}
const queueCard = () => `<div class="card" style="margin-top:16px"><b>Hintergrund-Warteschlange</b><p class="dim" style="margin:2px 0 8px">Aufträge, die im Hintergrund laufen (z. B. Recherche mit Internet): ansehen, vorziehen oder abbrechen.</p><button class="btn" data-act="queue">Warteschlange ansehen</button></div>`;
