/* Projektdaten */
function projectEditData(){
  const p = S.cfg.project || {};
  return Object.assign(base(), {PROJECT_TITLE:p.title || p.working_title || "", PROJECT_SUBTITLE:p.subtitle || "", PROJECT_TITLE_SHORT:p.title_short || "", PROJECT_AUTHOR:p.author || "",
    PROJECT_DESCRIPTION_SHORT:p.description_short || "", PROJECT_DESCRIPTION:p.description || "", PROJECT_LANGUAGE:p.language || "de", PROJECT_BOOK_TYPE:p.book_type || "",
    PROJECT_TARGET_AUDIENCE:p.target_audience || "", PROJECT_TRANSLATIONS:(p.translations_planned || []).join(", ")});
}
function projectSet(text, key, value){
  // ein Feld im Block project: ersetzen (Kommentar bleibt), einfügen oder entfernen (value === null)
  const L = text.split("\n"), pi = L.findIndex(l => /^project:\s*$/.test(l)); if (pi < 0) throw {message:"ghostwriter.yml hat keinen Abschnitt „project“."};
  let end = pi + 1; while (end < L.length && (L[end].trim() === "" || /^ {2}/.test(L[end]))) end++;
  const re = new RegExp("^  " + key + ":"), i = L.findIndex((l, k) => k > pi && k < end && re.test(l));
  if (value === null){ if (i >= 0) L.splice(i, 1); return L.join("\n"); }
  if (i >= 0){ const m = /^(  [a-z_]+:[ \t]*)("(?:[^"\\]|\\.)*"|\[[^\]]*\]|[^#]*?)([ \t]*#.*)?$/.exec(L[i]); L[i] = m ? m[1] + value + (m[3] || "") : `  ${key}: ${value}`; }
  else { let last = end; while (last > pi + 1 && L[last - 1].trim() === "") last--; L.splice(last, 0, `  ${key}: ${value}`); }
  return L.join("\n");
}
async function projectUpdate(d){
  busy("Wird gespeichert …");
  try {
    const work = await prepareWork(); const cur = (await getFile("ghostwriter.yml", work, true)).text; let t = cur;
    for (const k of ["title", "subtitle", "title_short", "author", "description_short", "description", "book_type", "target_audience"]){
      if (!(k in d)) continue; const v = String(d[k] || "").trim(), was = String(((S.cfg.project || {})[k]) || "").trim();
      if (v === was || (k === "title" && !was && v === String((S.cfg.project || {}).working_title || "").trim())) continue;
      t = projectSet(t, k, v ? yq(v) : (k === "title" ? yq(v) : null));
    }
    if (d.language) t = projectSet(t, "language", yq(d.language));
    if (d.language === (S.cfg.project || {}).language) delete d.language;
    if (Array.isArray(d.translations_planned) && d.translations_planned.join(",") !== ((S.cfg.project || {}).translations_planned || []).join(",")) t = projectSet(t, "translations_planned", "[" + d.translations_planned.join(", ") + "]");
    const r = await commit(t === cur ? [] : [{path:"ghostwriter.yml", content:t}], "Projektdaten geändert", {action:"project.update"});
    S.msg = savedMsg("Projektdaten gespeichert.", r);
  } catch (e) { S.msg = failMsg(e); }
  S.from = null; show("project");
}

/* Kapitel */
async function chapterEditData(id){
  const ci = chIndex(id), c = chapters()[ci], r = await getFile(c.path + "/README.md", S.readRef).then(f => f.text).catch(() => ""), sub = /^\*([^*].*)\*$/m.exec(r);
  return Object.assign(base(), {CHAPTER_ID:c.id, CHAPTER_NUMBER:ci + 1, CHAPTER_TITLE:c.title, CHAPTER_SUBTITLE:sub ? sub[1] : "", CHAPTER_SUMMARY:part(r, "Kurzbeschreibung"), CHAPTER_GOAL:part(r, "Ziel des Kapitels")});
}
async function chapterUpdate(d){
  busy("Wird gespeichert …");
  const ci = chIndex(d.chapter_id);
  try {
    const work = await prepareWork(); await loadBookData(work);
    const c = chapters()[ci], files = {}, orig = {};
    const gy = (await getFile("ghostwriter.yml", work, true)).text; orig["ghostwriter.yml"] = gy;
    const st = splitStructure(gy); setLine(st.chs[ci].head, "title", yq(d.title), st); files["ghostwriter.yml"] = joinStructure(st);
    const rp = c.path + "/README.md"; let r = (await getFile(rp, work, true).catch(() => ({text:null}))).text; orig[rp] = r;
    if (r != null){
      r = r.replace(/^# Kapitel (\d+) [–-] .*$/m, `# Kapitel $1 – ${d.title}`);
      const hasSub = /^\*([^*].*)\*$/m.test(r);
      if (hasSub) r = d.subtitle ? r.replace(/^\*([^*].*)\*$/m, `*${d.subtitle}*`) : r.replace(/^\*([^*].*)\*\n\n?/m, "");
      else if (d.subtitle) r = r.replace(/^(# Kapitel .*\n)/m, `$1\n*${d.subtitle}*\n`);
      r = readmeSet(r, "Kurzbeschreibung", d.summary || ""); r = readmeSet(r, "Ziel des Kapitels", d.goal || "");
      files[rp] = r;
    }
    const res = await commit(changed(files, orig), `Kapitel ${ci + 1} „${d.title}“ bearbeitet`, {action:"chapter.update"});
    S.msg = savedMsg("Kapitel gespeichert.", res);
  } catch (e) { S.msg = failMsg(e); }
  S.from = null; show("chapter", ci);
}
async function chapterCreate(d){
  busy("Kapitel wird angelegt …");
  try {
    const work = await prepareWork(); await loadBookData(work);
    const chs = chapters(), pos = Math.max(0, Math.min(Number(d.position) || 0, chs.length));
    const nums = chs.map(c => +((/chapters\/(\d+)-/.exec(c.path) || [])[1] || 0)), dn = pad2(Math.max(chs.length, ...nums, 0) + 1), sl = slug(d.title);
    let id = `ch-${dn}-${sl}`; const ids = new Set(chs.map(c => c.id)); for (let k = 2; ids.has(id); k++) id = `ch-${dn}-${sl}-${k}`;
    const path = `chapters/${dn}-${sl}`;
    const gy = (await getFile("ghostwriter.yml", work, true)).text, st = splitStructure(gy);
    st.chs.splice(pos, 0, {head:chEntry(st, id, d.title, path), secs:[], tail:[], id});
    const files = {"ghostwriter.yml":joinStructure(st)}, orig = {"ghostwriter.yml":gy};
    files[path + "/README.md"] = `# Kapitel ${pos + 1} – ${d.title}\n\n## Kurzbeschreibung\n\n${(d.summary || "").trim() || "Offen."}\n\n## Ziel des Kapitels\n\n${(d.goal || "").trim() || "Offen."}\n\n## Abschnitte\n\n| Nummer | Abschnitt | Status |\n|---|---|---|\n\n## Kapitelstatus\n\n\`planned\`\n\n## Kapitelzusammenführung\n\nNoch nicht begonnen.\n`;
    orig[path + "/README.md"] = null;
    S.cfg.structure = window.jsyaml.load(files["ghostwriter.yml"]).structure; buildStruct();
    if (pos < chs.length) await renumber(chapters().slice(pos + 1).map(c => c.id), files, work, orig);
    const r = await commit(changed(files, orig), `Kapitel ${pos + 1} „${d.title}“ angelegt`, {action:"chapter.create"});
    S.msg = savedMsg(`Kapitel „${d.title}“ angelegt.`, r);
    S.from = null; return show("chapter", chIndex(id));
  } catch (e) { S.msg = failMsg(e); S.from = null; show("project"); }
}
async function sectionCreate(d){
  busy("Abschnitt wird angelegt …");
  try {
    const work = await prepareWork(); await loadBookData(work);
    const ci = chIndex(d.chapter_id), c = chapters()[ci], pos = Math.max(0, Math.min(Number(d.position) || 0, c.sections.length));
    const nums = c.sections.map(s => +((/sections\/(\d+)-/.exec(s.path) || [])[1] || 0)), fn = pad2(Math.max(c.sections.length, ...nums, 0) + 1), sl = slug(d.title);
    let id = `sec-${pad2(ci + 1)}-${fn}-${sl}`; const ids = new Set(allSecs().map(v => v.s.id)); for (let k = 2; ids.has(id); k++) id = `sec-${pad2(ci + 1)}-${fn}-${sl}-${k}`;
    const path = `${c.path}/sections/${fn}-${sl}.md`, num = `${ci + 1}.${pos + 1}`, fc = ["disabled", "optional", "requested"].includes(d.fact_check) ? d.fact_check : "optional";
    const file = `---\nid: ${id}\nnumber: "${num}"\ntitle: ${yq(d.title)}\nstatus: planned\nfact_check: ${fc}   # disabled | optional | requested\napprovals:\n  writing: false\n  section: false\n---\n\n# ${num} ${d.title}\n\n## Ziel des Abschnitts\n\n${(d.goal || "").trim() || "Offen."}\n\n## Kurzbeschreibung\n\n${(d.summary || "").trim() || "Offen."}\n\n## Recherche- und Brainstorming-Ergebnisse\n\nWerden in separaten Laufdateien dokumentiert.\n\n## Manuskript\n\nNoch nicht begonnen.\n`;
    const gy = (await getFile("ghostwriter.yml", work, true)).text, st = splitStructure(gy);
    st.chs[ci].secs.splice(pos, 0, secEntry(st, id, d.title, path));
    const files = {"ghostwriter.yml":joinStructure(st), [path]:file}, orig = {"ghostwriter.yml":gy, [path]:null};
    S.cfg.structure = window.jsyaml.load(files["ghostwriter.yml"]).structure; buildStruct();
    await renumber([c.id], files, work, orig);
    const r = await commit(changed(files, orig), `Abschnitt ${num} „${d.title}“ angelegt`, {action:"section.create"});
    S.msg = savedMsg(`Abschnitt ${num} „${d.title}“ angelegt.`, r);
    S.from = null; return show("section", id);
  } catch (e) { S.msg = failMsg(e); S.from = null; show("project"); }
}
async function reorder(chapterId, order){
  busy("Reihenfolge wird gespeichert …");
  const ci = chapterId ? chIndex(chapterId) : -1;
  try {
    const work = await prepareWork(); await loadBookData(work);
    const gy = (await getFile("ghostwriter.yml", work, true)).text, st = splitStructure(gy);
    const list = chapterId ? st.chs[ci].secs : st.chs, idOf = b => chapterId ? idOfBlock(b) : b.id;
    if (!Array.isArray(order) || order.length !== list.length || !order.every(id => list.some(b => idOf(b) === id))) throw {message:"Die Reihenfolge passt nicht zum aktuellen Stand. Bitte neu öffnen."};
    const sorted = order.map(id => list.find(b => idOf(b) === id));
    if (chapterId) st.chs[ci].secs = sorted; else st.chs = sorted;
    const files = {"ghostwriter.yml":joinStructure(st)}, orig = {"ghostwriter.yml":gy};
    S.cfg.structure = window.jsyaml.load(files["ghostwriter.yml"]).structure; buildStruct();
    await renumber(chapterId ? [chapterId] : null, files, work, orig);
    const r = await commit(changed(files, orig), chapterId ? `Abschnittsreihenfolge in Kapitel ${ci + 1} geändert` : "Kapitelreihenfolge geändert", {action:chapterId ? "section.reorder" : "chapter.reorder"});
    S.msg = savedMsg("Reihenfolge gespeichert.", r);
  } catch (e) { S.msg = failMsg(e); }
  S.from = null; chapterId ? show("chapter", chIndex(chapterId)) : show("project");
}

