/* ---------- Aktionen aus den Widgets ---------- */
function parseAction(text){
  let m = /```gw\n([\s\S]*?)\n```/.exec(text);
  if (m){ try { const o = JSON.parse(m[1]); const a = o.action; delete o.action; return {action:a, data:o, text:text.split("\n\n")[0]}; } catch (e) {} }
  m = /`gw:([^\s`]+)([^`]*)`/.exec(text);
  if (m){ const data = {}; m[2].trim().split(/\s+/).filter(Boolean).forEach(kv => { const i = kv.indexOf("="); if (i < 0) return; const k = kv.slice(0, i), v = kv.slice(i + 1); data[k] = /^-?\d+$/.test(v) ? Number(v) : v === "true" ? true : v === "false" ? false : v; }); return {action:m[1], data, text:text.split("\n\n")[0]}; }
  return {action:"", data:{}, text};
}
window.sendPrompt = text => { const a = parseAction(String(text)); setTimeout(() => act(a), 0); };
const chIndex = id => chapters().findIndex(c => c.id === id);
function back(){ const f = S.from || {view:"project"}; S.from = null; return show(f.view, f.arg); }
function here(){ return S.view === "section" ? {view:"section", arg:S.sec && S.sec.id} : S.view === "chapter" ? {view:"chapter", arg:S.chap} : {view:"project"}; }
async function act({action, data, text}){
  try {
    switch (action){
      case "library.book.open": return openBook(data.branch);
      case "view.library": S.msg = null; return show("library");
      case "view.project": S.msg = null; return show("project");
      case "view.chapter": S.msg = null; return show("chapter", chIndex(data.chapter_id));
      case "view.section": S.msg = null; return show("section", data.section_id);
      case "section.update": return saveSection(data);
      case "view.data": S.msg = null; return show("data");
      case "changes.merge.open": S.msg = null; return S.pr ? show("merge") : show("project");
      case "changes.merge": return merge(data);
      case "form.cancel": S.msg = {kind:"info", html:"Abgebrochen – nichts wurde gespeichert."}; return back();
      case "approval.open": S.from = here(); S.msg = null; return form("freigabe-bestaetigen", await approvalData(data));
      case "approval.confirm": return approve(data);
      case "project.edit": S.from = here(); S.msg = null; return form("projektdaten-bearbeiten", projectEditData());
      case "project.update": return projectUpdate(data);
      case "chapter.create.open": S.from = here(); S.msg = null; return form("kapitel-anlegen", Object.assign(base(), {POSITIONS:positions(chapters().map((c, i) => [`Kapitel ${i + 1}`, c.title]), "Kapitel 1", "Als erstes Kapitel")}));
      case "chapter.create": return chapterCreate(data);
      case "chapter.edit.open": S.from = here(); S.msg = null; return form("kapitel-bearbeiten", await chapterEditData(data.chapter_id));
      case "chapter.update": return chapterUpdate(data);
      case "section.create.open": { S.from = here(); S.msg = null; const ci = chIndex(data.chapter_id), c = chapters()[ci];
        return form("abschnitt-anlegen", Object.assign(base(), {CHAPTER_ID:c.id, CHAPTER_NUMBER:ci + 1, CHAPTER_TITLE:c.title, FACT_CHECK_DEFAULT:(S.cfg.workflow || {}).fact_checking_default || "optional",
          POSITIONS:positions(c.sections.map((s, si) => [`${ci + 1}.${si + 1}`, s.title]), `${ci + 1}.1`, "Als erster Abschnitt")})); }
      case "section.create": return sectionCreate(data);
      case "chapter.reorder.open": S.from = here(); S.msg = null; return form("reihenfolge", Object.assign(base(), {REORDER_KIND:"chapter", REORDER_HEADING:"Kapitelreihenfolge ändern", CHAPTER_ID:"", CHAPTER_NUMBER:"", ITEMS:chapters().map((c, i) => ({ITEM_ID:c.id, ITEM_NUMBER:String(i + 1), ITEM_TITLE:c.title}))}));
      case "section.reorder.open": { S.from = here(); S.msg = null; const ci = chIndex(data.chapter_id), c = chapters()[ci];
        return form("reihenfolge", Object.assign(base(), {REORDER_KIND:"section", REORDER_HEADING:`Abschnittsreihenfolge in Kapitel ${ci + 1} ändern`, CHAPTER_ID:c.id, CHAPTER_NUMBER:ci + 1, ITEMS:c.sections.map((s, si) => ({ITEM_ID:s.id, ITEM_NUMBER:`${ci + 1}.${si + 1}`, ITEM_TITLE:s.title}))})); }
      case "chapter.reorder": return reorder(null, data.order);
      case "section.reorder": return reorder(data.chapter_id, data.order);
      case "view.characters": S.msg = null; S.from = null; return show("characters");
      case "view.character": S.from = {view:"characters"}; S.msg = null; return form("figur-bearbeiten", await charEditData(data.character_id));
      case "view.notes_review": { S.msg = null; const fs = await reviewFiles(); const f = data.file || (fs.length ? "editorial/" + fs[fs.length - 1] : ""); if (!f){ S.msg = {kind:"info", html:"Es gibt noch keine Hinweisdurchsicht in diesem Buch."}; return show("project"); } return show("review", f); }
      case "view.queue": S.msg = null; return show("queue");
      case "queue.prioritize": return queueChange("prioritize", data);
      case "queue.cancel": return queueChange("cancel", data);
      case "queue.retry": return queueChange("retry", data);
      case "section.mark_stale": return staleChange("mark", data);
      case "section.clear_stale": return staleChange("clear", data);
      case "stale.list": return staleList();
      case "notes_review.decide": return reviewDecide(data);
      case "notes_review.ask": return reviewAsk(data);
      case "notes_review.plan": return reviewPlan(data);
      case "notes_review.apply": return reviewApply(data);
      case "character.suggest": return characterSuggest(data);
      case "character.suggest.apply": return characterSuggestApply(data);
      case "character.series.update": return characterSeries("update", data);
      case "character.detach": return characterSeries("detach", data);
      case "character.align": return characterSeries("align", data);
      case "character.adopt": return characterSeries("adopt", data);
      case "character.create": return characterCreate(data);
      case "character.update": return characterUpdate(data);
      case "run.start": return runStart(data);
      default: if (GW_PORTS.actions && GW_PORTS.actions[action]) return GW_PORTS.actions[action](data);   // Aktionen, die nur ein Anschluss kann (eigene Web-App: Actions starten)
        return unsupported(text, action, data);
    }
  } catch (e) { S.msg = {kind:"err", html:esc(errText(e))}; return show(S.view === "form" ? "project" : S.view, S.view === "section" ? S.sec && S.sec.id : S.chap); }
}
function form(name, data){ S.view = "form"; widget(name, data); }
function positions(items, first, only){
  if (!items.length) return [{POSITION_LABEL:only, POSITION_SELECTED:"selected"}];
  const out = [{POSITION_LABEL:`Am Anfang (vor ${first})`, POSITION_SELECTED:""}];
  items.forEach(([n, t], i) => out.push({POSITION_LABEL:i === items.length - 1 ? `Am Ende (nach ${n} „${t}“)` : `Nach ${n} „${t}“`, POSITION_SELECTED:i === items.length - 1 ? "selected" : ""}));
  return out;
}
function unsupported(text, action, data){
  const prompt = text + (action ? `\n\n\`gw:${action}${Object.entries(data || {}).map(([k, v]) => ` ${k}=${typeof v === "object" ? JSON.stringify(v) : v}`).join("")}\`` : "");
  S.msg = {kind:"info", html:`<b>Das geht in dieser App noch nicht.</b> Im Chat mit GhostWriter löst du es mit diesem Text aus: <button class="link" data-act="copy">Text kopieren</button><pre id="cpy">${esc(prompt)}</pre>`};
  const old = document.querySelector("#app .note"), html = msgBox();
  if (old) old.outerHTML = html; else if ($("gw")) $("gw").insertAdjacentHTML("beforebegin", html);
  window.scrollTo(0, 0);
}

