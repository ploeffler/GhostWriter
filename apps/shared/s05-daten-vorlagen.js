/* ---------- Daten für die Vorlagen (wie scripts/render_view.py) ---------- */
/* wie render_view.jobs_text / jobs.status_text (#484): „Warteschlange: 2 fertig · 1 fehlgeschlagen · 3 warten“, leer ohne Aufträge */
function jobsText(i, total){
  if (!i) return "";
  const w = (i.waiting || 0) + (i.waiting_budget || 0), parts = [];
  if (i.done) parts.push(i.done + " fertig");
  if (i.failed) parts.push(i.failed + " fehlgeschlagen");
  if (w) parts.push(w + (w === 1 ? " wartet" : " warten"));
  return parts.length ? (total ? "Hintergrund-Warteschlange: " : "Warteschlange: ") + parts.join(" · ") : "";
}
function bookRow(b){
  const ready = b.status === "ready", st = b.sections_total || 0, sa = b.sections_approved || 0, ed = b.current_edition || 0;
  return {BOOK_BRANCH:b.branch, BOOK_TITLE:b.title || b.title_short || "Ohne Titel", BOOK_TITLE_SHORT:b.title_short || b.branch.split("/").pop(),
    BOOK_AUTHOR_TEXT:b.author ? "von " + b.author : "", BOOK_STATE:ready ? "ready" : "setup", BOOK_STATE_TEXT:ready ? "eingerichtet" : "im Aufbau",
    BOOK_PROGRESS:st ? Math.round(100 * sa / st) : 0,
    BOOK_PROGRESS_TEXT:ready ? `${sa} von ${plural(st, "Abschnitt", "Abschnitten")} freigegeben · ${b.chapters_approved || 0} von ${plural(b.chapters_total || 0, "Kapitel", "Kapiteln")}` : "Gliederung noch offen",
    BOOK_EDITION_TEXT:ed ? "Auflage " + ed : "noch keine Auflage", BOOK_COST:(b.cost && b.cost.text) || "–",
    BOOK_PENDING_TEXT:b.pending ? plural(b.pending, "Änderung", "Änderungen") + " offen" : "",
    BOOK_UPDATED_TEXT:b.updated_at ? `${ready ? "zuletzt geändert" : "angelegt"} am ${deDate(b.updated_at)}` : "",
    BOOK_JOBS_TEXT:jobsText(b.jobs), BOOK_CHECKOUT_TEXT:(b.checkouts || []).map(c => c.text).filter(Boolean).join(" · "),
    BOOK_SERIES:"", BOOK_SERIES_TITLE:"", BOOK_SERIES_KEY:"", BOOK_VOLUME_TEXT:""};
}
function libraryData(){
  const books = S.lib.books || [], byBranch = new Map(books.map(b => [b.branch, b])), ser = S.lib.series || [], rows = [], seen = new Set();
  // Bücher einer Serie zuerst, gruppiert und in Bandreihenfolge (#116, wie render_view.library_view); danach die übrigen
  ser.forEach((s, si) => (s.volumes || []).forEach((br, n) => { const b = byBranch.get(br); if (b && !seen.has(br)){ rows.push(Object.assign(bookRow(b), {BOOK_SERIES:s.id, BOOK_SERIES_TITLE:s.title || s.id, BOOK_SERIES_KEY:"S" + (si + 1), BOOK_VOLUME_NUMBER:n + 1, BOOK_VOLUME_TEXT:"Band " + (n + 1)})); seen.add(br); } }));
  books.forEach(b => { if (!seen.has(b.branch)) rows.push(bookRow(b)); });
  const emptySeries = ser.filter(s => !(s.volumes || []).some(br => byBranch.has(br))).map(s => ({S_ID:s.id, S_TITLE:s.title || s.id, S_KEY:"S" + (ser.indexOf(s) + 1)}));
  const editions = books.flatMap(b => (b.editions || []).map(e => { const n = e && typeof e === "object" ? (e.number || e.edition) : e; return n ? {E_BOOK_BRANCH:b.branch, E_NUMBER:n, E_TEXT:"Auflage " + n, E_DATE_TEXT:deDate((e && (e.date || e.published)) || ""), E_TAG:(e && e.tag) || ""} : null; }).filter(Boolean));
  const d = {LANGUAGE:"de", LIBRARY_NAME:S.owner + "/" + S.repo, BOOK_COUNT_TEXT:plural(rows.length, "Buch", "Bücher") + (ser.length ? " · " + plural(ser.length, "Serie", "Serien") : ""), JOBS_TEXT:jobsText(["done", "failed", "waiting", "waiting_budget"].reduce((t, k) => (t[k] = books.reduce((n, b) => n + ((b.jobs || {})[k] || 0), 0), t), {}), true), EMPTY:rows.length ? "" : "1", UPDATED_TEXT:"", SESSION_COUNT_TEXT:"", BOOKS:rows};
  if (editions.length) d.EDITIONS = editions;
  if (emptySeries.length) d.EMPTY_SERIES = emptySeries;
  return d;
}
const base = () => ({LANGUAGE:"de", HEAD_SHA:S.head});
const shortTitle = () => (S.cfg.project || {}).title_short || S.book.title_short || S.book.title;
/* Kosten nur fürs ganze Buch (#754): Gibt es Buchkosten, aber nirgends Kosten bei Kapiteln, ist „–“ dort kein Fehler. Gleiche Texte wie scripts/render_view.py. */
const projectOnlyCosts = () => { const c = (S.idx.project || {}).cost; return !!(c && c.amount != null) && !(S.struct || []).some(x => x.cost && x.cost.amount != null); };
const COST_ONLY_HINT = "Keine Kosten für diesen Teil erfasst: KI-API-Kosten (z. B. Medienaufträge) sind nur fürs ganze Buch erfasst, siehe Projektübersicht";
const costShown = (k, only) => (k && k.text && k.text !== "–") ? k.text : only ? "– (nur Buch)" : "–";
const costTip = (k, base, only) => (k && k.text && k.text !== "–") || !only ? base : COST_ONLY_HINT;
async function projectData(){
  await loadSecFiles(allSecs(), "Projektübersicht wird geladen");
  const p = S.cfg.project || {}, ix = S.idx.project || {};
  const rows = chapters().map((c, i) => {
    let w = 0, done = 0;
    for (const s of c.sections || []){ const f = cached(s.path); if (!f) continue; w += words(msOf(f.text)); done += front(f.text).status === "approved" ? 1 : 0; }
    const tags = tagsFor((c.sections || []).map(s => s.id));
    const row = {CHAPTER_NUMBER:i + 1, CHAPTER_TITLE:c.title, CHAPTER_STATUS:c.status, CHAPTER_COST:(c.cost && c.cost.text) || "–", CHAPTER_COST_HINT:costTip(c.cost, "Summe der Abschnittskosten", projectOnlyCosts()),
      CHAPTER_ID:c.id, CHAPTER_WORDS:w, CHAPTER_WORDS_TEXT:fmtNum(w) + (w === 1 ? " Wort" : " Wörter"),
      CHAPTER_APPROVED_TEXT:(c.sections || []).length ? `${done} von ${c.sections.length}` : "", CHAPTER_CHECKS_JSON:pick(tags, J_SLIM), CHAPTER_NOTES_TEXT:"", CHAPTER_CHECK_DETAILS:""};
    const sm = staleMarks((c.sections || []).map((s, si) => [`${i + 1}.${si + 1}`, (cached(s.path) || {}).text]));
    row.CHAPTER_STALE_TEXT = sm[0]; row.CHAPTER_STALE_HINT = sm[1];
    return row;
  });
  const longest = Math.max(0, ...rows.map(r => r.CHAPTER_WORDS));
  rows.forEach(r => { r.CHAPTER_WORDS_PCT = longest ? Math.round(100 * r.CHAPTER_WORDS / longest) : 0; });
  const ed = p.current_edition || ix.current_edition || 0;
  const d = Object.assign(base(), {PROJECT_TITLE:p.title || p.working_title || ix.title || S.book.title, PROJECT_TITLE_SHORT:shortTitle(),
    PROJECT_AUTHOR:p.author || ix.author || "", PROJECT_DESCRIPTION_SHORT:p.description_short || "", PROJECT_DESCRIPTION:p.description || "",
    PROJECT_COST:(ix.cost && ix.cost.text) || "–", PROJECT_COST_HINT:"Zusätzliche KI-API-Kosten über das GhostWriter-Backend",
    PROJECT_EDITION_TEXT:ed ? "Auflage " + ed : "noch keine Auflage", CREDIT_TEXT:"Entwickelt mit Unterstützung von Claude (Anthropic)", CREDIT_URL:"https://claude.ai", CHAPTERS:rows});
  if (S.checks.length){ d.CHECKS_RECENT_TEXT = recentText(); d.CHECKS_LEGEND = LEGEND_LATEST; }
  if (S.pr){ const n = S.pr.commits || 1; Object.assign(d, {PENDING_COUNT:n, PENDING_TEXT:plural(n, "Änderung", "Änderungen"), PENDING_PR:S.pr.number}); }
  if ((S.lib.books || []).length >= 2) d.LIBRARY_COUNT = S.lib.books.length;
  if (charItems().length) d.CHARACTER_COUNT = charItems().length;
  for (const [key, area] of [["front_matter", "MATTER_FRONT"], ["back_matter", "MATTER_BACK"]]){   // Vor- und Nachspann mit Marke „veraltet“ (#510)
    const items = (S.cfg.structure && S.cfg.structure[key]) || [], out = [];
    for (const it of items){
      const t = (await getFile(it.path, S.readRef).catch(() => ({text:""}))).text, h = front(t), ms = msOf(t), sm = staleMarks([[it.title, t]]);
      out.push({MATTER_ID:it.id, MATTER_TITLE:it.title, MATTER_STATUS:h.status || "planned", MATTER_MARKERS:(ms.match(MARKER_RE) || []).length, MATTER_STALE_TEXT:sm[0], MATTER_STALE_HINT:sm[1].replace(/^[^:]+: /, "")});
    }
    if (out.length) d[area] = out;
  }
  const nStale = rows.reduce((n, r) => n + (r.CHAPTER_STALE_TEXT ? (parseInt(r.CHAPTER_STALE_TEXT, 10) || 1) : 0), 0) + [...(d.MATTER_FRONT || []), ...(d.MATTER_BACK || [])].filter(m => m.MATTER_STALE_TEXT).length;
  if (nStale) d.STALE_TEXT = `${nStale} veraltet`;
  return d;
}
async function chapterData(ci){
  const c = chapters()[ci], secs = c.sections || [];
  await loadSecFiles(secs.map(s => ({c, s})), "Kapitel wird geladen");
  const readme = await getFile(c.path + "/README.md", S.readRef).then(f => f.text).catch(() => "");
  const sub = /^\*([^*].*)\*$/m.exec(readme);
  let markers = 0, approved = 0;
  const rows = secs.map((s, si) => {
    const f = cached(s.path), t = f ? f.text : "", ms = msOf(t), st = f ? (front(t).status || s.status) : s.status;
    const cnt = k => (ms.match(new RegExp("\\[" + k, "g")) || []).length;
    const m = {a:cnt("PLATZHALTER-ANEKDOTE"), q:cnt("QUELLE PRÜFEN"), me:cnt("MEDIZIN PRÜFEN"), r:cnt("RECHT PRÜFEN"), k:cnt("KONTINUITÄT PRÜFEN")};
    markers += m.a + m.q + m.me + m.r + m.k; approved += st === "approved" ? 1 : 0;
    return {SECTION_ID:s.id, SECTION_NUMBER:`${ci + 1}.${si + 1}`, SECTION_TITLE:s.title, SECTION_STATUS:st, SECTION_COST:(s.cost && s.cost.text) || "–",
      MARKERS_ANEKDOTE:m.a, MARKERS_QUELLE:m.q, MARKERS_MEDIZIN:m.me, MARKERS_RECHT:m.r, MARKERS_KONTINUITAET:m.k, SECTION_CHECKS_JSON:pick(tagsFor([s.id]), J_FULL),
      SECTION_STALE_TEXT:staleMarks([["", t]])[0], SECTION_STALE_HINT:staleMarks([[`${ci + 1}.${si + 1}`, t]])[1].replace(/^[^:]+: /, "")};
  });
  const n = secs.length, ids = secs.map(s => s.id), tags = tagsFor(ids), hist = historyFor(ids);
  const d = Object.assign(base(), {PROJECT_TITLE_SHORT:shortTitle(), CHAPTER_ID:c.id, CHAPTER_NUMBER:ci + 1,
    CHAPTER_GOAL:part(readme, "Ziel des Kapitels"), CHAPTER_SUMMARY:part(readme, "Kurzbeschreibung"), CHAPTER_TITLE:c.title, CHAPTER_SUBTITLE:sub ? sub[1] : (c.subtitle || ""),
    SECTION_COUNT_TEXT:n + (n === 1 ? " Abschnitt" : " Abschnitte"), MARKER_COUNT_TEXT:markers ? `${markers} offene${markers === 1 ? "r" : ""} Marker` : "keine offenen Marker",
    CHAPTER_COST:costShown(c.cost, projectOnlyCosts()), CHAPTER_COST_HINT:costTip(c.cost, "Summe der Abschnittskosten", projectOnlyCosts()), APPROVED_COUNT_TEXT:`${approved} von ${n}`,
    CHAPTER_APPROVABLE:c.status === "ready_for_approval" && n && approved === n ? "true" : "", CHAPTER_REVISION_READY:"", SECTIONS:rows});
  if (S.checks.length) d.CHECKS_LEGEND = LEGEND_FULL;
  if (tags.length) d.CHECKS_JSON = pick(tags, J_FULL);
  if (hist.length){ d.CHECKS_HISTORY_COUNT = hist.length; d.CHECKS_HISTORY_JSON = pick(hist, J_HIST); }
  return d;
}
async function sectionData(id){
  const x = allSecs().find(v => v.s.id === id); if (!x) throw {message:"Abschnitt nicht gefunden."};
  const ci = chapters().indexOf(x.c), secs = x.c.sections, si = secs.indexOf(x.s);
  const f = await getFile(x.s.path, S.readRef); if (!f.dg) f.dg = await sha16(msOf(f.text));
  const t = f.text, h = front(t), ms = msOf(t), markers = [];
  for (const m of ms.matchAll(MARKER_RE)) markers.push({MARKER_TYPE:MK[m[1]], MARKER_LABEL:MK_LABEL[MK[m[1]]], MARKER_TEXT:(m[2] || "").trim() || "–"});
  const nav = k => k >= 0 && k < secs.length ? [secs[k].id, `Abschnitt ${ci + 1}.${k + 1} „${secs[k].title}“ bearbeiten`] : ["", ""];
  const [pid, ptx] = nav(si - 1), [nid, ntx] = nav(si + 1), ap = h.approvals || {}, waived = ((S.cfg.workflow || {}).require_section_writing_approval === false);
  const tags = tagsFor([id]), hist = historyFor([id]);
  const d = Object.assign(base(), {PROJECT_TITLE_SHORT:shortTitle(), CHAPTER_ID:x.c.id, CHAPTER_NUMBER:ci + 1,
    SECTION_ID:id, SECTION_NUMBER:`${ci + 1}.${si + 1}`, SECTION_TITLE:x.s.title, SECTION_STATUS:h.status || x.s.status, SECTION_COST:costShown(x.s.cost, projectOnlyCosts()),
    SECTION_COST_HINT:costTip(x.s.cost, "Summe der Kosteneinträge", projectOnlyCosts()), SECTION_GOAL:part(t, "Ziel des Abschnitts"), SECTION_SUMMARY:part(t, "Kurzbeschreibung"), SECTION_MANUSCRIPT:ms,
    MARKER_COUNT_TEXT:markers.length ? `${markers.length} offene${markers.length === 1 ? "r" : ""} Marker` : "keine offenen Marker",
    FACT_CHECK:h.fact_check || "disabled", APPROVAL_WRITING:String(!!ap.writing || waived), APPROVAL_SECTION:String(!!ap.section),
    WRITING_NOW_AVAILABLE:S.sample ? "true" : "false", RESEARCH_NOW_AVAILABLE:S.sample ? "true" : "false",   // „Sofort“ braucht Chat oder Modell (#759)
    PREV_SECTION_ID:pid, PREV_SECTION_PROMPT:ptx, NEXT_SECTION_ID:nid, NEXT_SECTION_PROMPT:ntx, MARKERS:markers});
  const st = staleOf(t);
  Object.assign(d, {STALE_TEXT:st ? staleHint(st) : "", STALE_NONE:st ? "" : "1", STALE_ARGS:JSON.stringify({section_id:id})});
  if (tags.length) d.CHECKS_JSON = pick(tags, J_FULL);
  if (hist.length){ d.CHECKS_HISTORY_COUNT = hist.length; d.CHECKS_HISTORY_JSON = pick(hist, J_HIST); }
  return {d, x, f};
}
function mergeData(){
  const list = S.pr.list || [];
  return Object.assign(base(), {HEAD_SHA:S.pr.head || S.head, PENDING_TEXT:plural(S.pr.commits || list.length || 1, "Änderung", "Änderungen"), PENDING_PR:S.pr.number, BOOK_BRANCH:S.book.branch, WORK_BRANCH:workOf(S.book),
    CHANGES:list.map(c => ({CHANGE_MESSAGE:String(c.message || "").split("\n")[0], CHANGE_DATE:(c.author && c.author.date) ? new Date(c.author.date).toLocaleString("de-AT", {day:"2-digit", month:"2-digit", year:"numeric", hour:"2-digit", minute:"2-digit"}) : "", CHANGE_SHA:String(c.sha || "").slice(0, 7)}))});
}

