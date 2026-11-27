/* ---------- Serienansicht (#742, nur anzeigen) ----------
   „Serie öffnen ›“ im Bücherregal zeigt die Serie: Titel, Art, Bände in Reihenfolge mit „Band öffnen“, Figuren und Begriffe der Serie (lesend), Sammelband.
   Gelesen aus series/<ser-id>/ auf dem Standard-Branch (series.yml, characters/char-*.md, glossary.yml, omnibus.yml); die Bände aus library.json.
   Ändern (Titel, Reihenfolge, Bände, Sammelband, Glossar-Abgleich) bleibt im Chat; es gibt hier keine Freigaben. */
const SER_KIND = {continuous:"durchgehende Handlung", standalone:"eigenständige Bände"};
async function serYaml(path){ try { return window.jsyaml.load((await getFile(path, null, true)).text) || {}; } catch (e) { return null; } }
async function seriesData(id){
  const sy = await serYaml(`series/${id}/series.yml`); if (!sy) throw {message:"Die Serie „" + id + "“ ist nicht lesbar (series/" + id + "/series.yml)."};
  const books = new Map(((S.lib && S.lib.books) || []).map(b => [b.branch, b])), vols = sy.volumes || [], inLib = ((S.lib && S.lib.series) || []).find(s => s.id === id);
  const rows = vols.map((br, n) => { const b = books.get(br);
    if (!b) return {V_NUMBER:n + 1, V_BRANCH:br, V_TITLE:br, V_TITLE_SHORT:br.split("/").pop(), V_STATE:"setup", V_STATE_TEXT:"nicht gefunden", V_PROGRESS:0, V_PROGRESS_TEXT:"", V_EDITION_TEXT:""};
    const r = bookRow(b); return {V_NUMBER:n + 1, V_BRANCH:br, V_TITLE:r.BOOK_TITLE, V_TITLE_SHORT:r.BOOK_TITLE_SHORT, V_STATE:r.BOOK_STATE, V_STATE_TEXT:r.BOOK_STATE_TEXT, V_PROGRESS:r.BOOK_PROGRESS, V_PROGRESS_TEXT:r.BOOK_PROGRESS_TEXT, V_EDITION_TEXT:r.BOOK_EDITION_TEXT}; });
  const files = (await listDefault(`series/${id}/characters`)).filter(e => /^char-.+\.md$/.test(e.name));
  const chars = (await pool(files, 8, async e => { try { const h = front((await getFile(e.path || `series/${id}/characters/${e.name}`, null, true)).text); return {SC_ID:h.id || e.name.replace(/\.md$/, ""), SC_NAME:h.name || e.name.replace(/\.md$/, ""), SC_ROLE:h.role || "", SC_SHORT:h.short_description || h.description || ""}; } catch (x) { return null; } })).filter(Boolean);
  const gl = await serYaml(`series/${id}/glossary.yml`), terms = ((gl && gl.terms) || []).map(t => ({ST_TERM:t.term || "", ST_TEXT:t.text || ""}));
  const om = await serYaml(`series/${id}/omnibus.yml`);
  const d = {LANGUAGE:"de", LIBRARY_NAME:S.owner + "/" + S.repo, SERIES_ID:sy.id || id, SERIES_TITLE:sy.title || (inLib && inLib.title) || id, SERIES_SUBTITLE:sy.subtitle || "", SERIES_DESCRIPTION:sy.description || "",
    SERIES_KIND_TEXT:SER_KIND[sy.kind] || SER_KIND.continuous, VOLUME_COUNT_TEXT:plural(rows.length, "Band", "Bände"), VOLUMES:rows};
  if (chars.length) d.SERIES_CHARACTERS = chars;
  if (terms.length) d.SERIES_TERMS = terms;
  if (om && Object.keys(om).length) Object.assign(d, {OMNIBUS_STATE:om.status === "approved" ? "approved" : "draft", OMNIBUS_TITLE:om.title || "", OMNIBUS_TEXT:`${plural((om.volumes || []).length, "Band", "Bände")} · ${om.status === "approved" ? "freigegeben" : "Entwurf"}${om.current_edition ? " · Auflage " + om.current_edition : ""}`});
  return d;
}
function seriesHtml(d){
  const vol = d.VOLUMES.map(v => `<tr><td style="width:56px">Band ${v.V_NUMBER}</td><td><b>${esc(v.V_TITLE)}</b><div class="dim">${esc(v.V_STATE_TEXT)}${v.V_PROGRESS_TEXT ? " · " + esc(v.V_PROGRESS_TEXT) : ""}${v.V_EDITION_TEXT ? " · " + esc(v.V_EDITION_TEXT) : ""}</div>${v.V_STATE === "ready" ? `<div class="bar" style="height:4px;background:var(--border,#d6d3c8);border-radius:2px;margin-top:4px"><i style="display:block;height:4px;width:${v.V_PROGRESS}%;background:var(--accent,#3d7a5a);border-radius:2px"></i></div>` : ""}</td>
    <td style="white-space:nowrap;text-align:right">${v.V_STATE_TEXT === "nicht gefunden" ? "" : `<button class="btn" data-ser-open="${esc(v.V_BRANCH)}">Band öffnen ›</button>`}</td></tr>`).join("");
  const chars = (d.SERIES_CHARACTERS || []).map(c => `<tr><td><b>${esc(c.SC_NAME)}</b>${c.SC_ROLE ? ` <span class="dim">${esc(c.SC_ROLE)}</span>` : ""}${c.SC_SHORT ? `<div class="dim">${esc(c.SC_SHORT)}</div>` : ""}</td></tr>`).join("");
  const terms = (d.SERIES_TERMS || []).map(t => `<tr><td style="width:30%"><b>${esc(t.ST_TERM)}</b></td><td>${esc(t.ST_TEXT)}</td></tr>`).join("");
  return `<div class="one"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><div><b style="font-size:20px">${esc(d.SERIES_TITLE)}</b>${d.SERIES_SUBTITLE ? `<div class="dim">${esc(d.SERIES_SUBTITLE)}</div>` : ""}</div><button class="btn" data-ser-back="1">Zurück zum Bücherregal</button></div>${msgBox()}
    <section class="card"><span class="dim">${esc(d.SERIES_KIND_TEXT)} · ${esc(d.VOLUME_COUNT_TEXT)}</span>${d.SERIES_DESCRIPTION ? `<p style="margin:6px 0">${esc(d.SERIES_DESCRIPTION)}</p>` : ""}</section>
    <section class="card"><b>Bände</b>${vol ? `<table class="kv">${vol}</table>` : '<p class="dim">Diese Serie hat noch keine Bände.</p>'}</section>
    ${chars ? `<section class="card"><b>Figuren der Serie</b><table class="kv">${chars}</table></section>` : ""}${terms ? `<section class="card"><b>Begriffe der Serie</b><table class="kv">${terms}</table></section>` : ""}
    ${d.OMNIBUS_TEXT ? `<section class="card"><b>Sammelband</b> ${esc(d.OMNIBUS_TITLE)}<div class="dim">${esc(d.OMNIBUS_TEXT)}</div></section>` : ""}
    <p class="dim">Hier wird nur angezeigt. Serie ändern, Bände ordnen, Sammelband und Glossar-Abgleich gehen weiter im Chat mit GhostWriter.</p></div>`;
}
async function seriesView(id){
  S.book = null; S.chap = null; S.sec = null; crumbs(); busy("Serie wird geladen …");
  try { const d = await seriesData(id); $("app").innerHTML = seriesHtml(d); window.scrollTo(0, 0); }
  catch (e) { S.msg = {kind:"err", html:esc(errText(e))}; show("library"); }
}
GW_PORTS.views = Object.assign(GW_PORTS.views || {}, {series:seriesView});
GW_PORTS.actions = Object.assign(GW_PORTS.actions || {}, {"view.series": data => { S.msg = null; return show("series", data && data.series_id); }});
document.addEventListener("click", ev => {
  const o = ev.target.closest && ev.target.closest("[data-ser-open]"); if (o){ ev.preventDefault(); return openBook(o.dataset.serOpen); }
  const b = ev.target.closest && ev.target.closest("[data-ser-back]"); if (b){ ev.preventDefault(); S.msg = null; return show("library"); }
});
