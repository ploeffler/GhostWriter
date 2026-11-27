/* Figuren (#53): characters/<id>.md, Liste in ghostwriter.yml → characters (wie scripts/characters.py) */
const ROLE_DE = {main:"Hauptfigur", supporting:"Nebenfigur", minor:"Randfigur"};
const CHAR_FIELDS = ["id", "name", "role", "short", "age", "appearance", "traits", "voice", "visual", "portrait", "relations"];
const charItems = () => (S.cfg.characters || []).filter(c => c && c.id);
const tagSlug = t => String(t).replace(/[äÄ]/g, "ae").replace(/[öÖ]/g, "oe").replace(/[üÜ]/g, "ue").replace(/ß/g, "ss").normalize("NFKD").replace(/[^\x00-\x7f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
function charParts(text){
  const m = /^---\n([\s\S]*?)\n---\n/.exec(text), body = m ? text.slice(m[0].length) : text;
  const sec = n => { const mm = new RegExp("^## " + n + "\\n([\\s\\S]*?)(?=^## |(?![\\s\\S]))", "m").exec(body); const v = mm ? mm[1].trim() : ""; return v.startsWith("<") ? "" : v; };
  return {head:front(text), desc:sec("Beschreibung"), notes:sec("Notizen")};
}
async function charFile(it, ref){ return (await getFile(it.path, ref || S.readRef).catch(() => ({text:""}))).text; }
function charUsage(){
  const out = {};
  chapters().forEach((c, ci) => (c.sections || []).forEach((s, si) => { const f = cached(s.path); if (!f) return; (front(f.text).characters || []).forEach(id => (out[id] = out[id] || []).push(`${ci + 1}.${si + 1}`)); }));
  return out;
}
/* Profilbilder (#417): `portrait` im Figurenkopf, sonst das erste freigegebene Referenzbild mit Rolle visual_reference und Link person:<id>;
   immer nur eine quadratisch beschnittene, verkleinerte Ableitung, nie das Original */
function blobOf(res){
  for (const b of (res && res.content) || []){
    if (b.type === "resource" && b.resource && typeof b.resource.blob === "string") return {b64:b.resource.blob, mime:b.resource.mimeType || "image/jpeg"};
    if (b.type === "image" && typeof b.data === "string") return {b64:b.data, mime:b.mimeType || "image/jpeg"};
  }
  return null;
}
async function refImages(){
  if (S.refs && S.refs.ref === S.readRef) return S.refs.list;
  const dir = "reference-images", entries = await listDir(dir, S.readRef), byName = new Map(entries.map(e => [e.name, e]));
  const metas = await pool(entries.filter(e => /^ref-img-.+\.yml$/.test(e.name)).sort((a, b) => a.name.localeCompare(b.name)), 8, async e => window.jsyaml.load((await getFile(dir + "/" + e.name, S.readRef)).text) || {});
  const list = metas.filter(m => m && m.status === "approved" && m.file && byName.has(String(m.file))).map(m => { const f = byName.get(String(m.file)); return {id:m.id, path:dir + "/" + m.file, sha:f.sha || "", size:f.size || 0, roles:m.roles || [], links:m.links || []}; });
  S.refs = {ref:S.readRef, list}; return list;
}
const portraitOf = (id, head, refs) => (head.portrait && refs.find(m => m.id === head.portrait)) || refs.find(m => m.roles.includes("visual_reference") && m.links.some(l => l.kind === "person" && l.id === id)) || null;
async function portraitData(ref, px){
  if (!ref || (ref.size && ref.size > 12 * 1024 * 1024)) return "";
  const key = `${ref.path}|${ref.sha}|${px}`; S.portraits = S.portraits || new Map();
  if (S.portraits.has(key)) return S.portraits.get(key);
  let url = "";
  try {
    const b = await GW_PORTS.git.getBlob(ref.path, S.readRef); if (!b) throw new Error("kein Bild");
    const bin = atob(b.b64), bytes = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const obj = URL.createObjectURL(new Blob([bytes], {type:b.mime}));
    const img = await new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => no(new Error("Bild nicht lesbar")); im.src = obj; });
    URL.revokeObjectURL(obj);
    const c = document.createElement("canvas"); c.width = c.height = px; const sq = Math.min(img.naturalWidth, img.naturalHeight);
    c.getContext("2d").drawImage(img, (img.naturalWidth - sq) / 2, (img.naturalHeight - sq) / 2, sq, sq, 0, 0, px, px);
    url = c.toDataURL("image/jpeg", 0.7);
  } catch (e) { url = ""; }   // ohne Bild bleibt das Feld leer
  S.portraits.set(key, url); return url;
}
/* Figuren der Serie (#116): series/<ser-id>/series.yml und series/<ser-id>/characters/char-*.md auf dem Standard-Branch;
   gelesen ohne Branch-Angabe (= Standard-Branch), geschrieben direkt dorthin (kein Änderungspaket, wie im Chat) */
const SOURCE_DE = {series:"aus der Serie", copy:"Kopie der Serie (gleich)", copy_diff:"Kopie, weicht von der Serie ab", own:"nur in diesem Buch"};
async function listDefault(dir){
  try { return await GW_PORTS.git.listDir(dir); } catch (e) { return []; }
}
async function defaultBranch(){
  if (S.defBranch && S.defBranch.repo === S.owner + "/" + S.repo) return S.defBranch.name;
  let name = "";
  try { const it = await GW_PORTS.git.repoInfo(S.owner, S.repo); name = (it && it.default_branch) || ""; } catch (e) {}
  if (!name){   // Rückfall: der Branch, dessen Spitze der Standard-Stand von library.json ist
    try { const lj = await GW_PORTS.git.getFile("library.json"), sha = lj.commit, br = await GW_PORTS.git.listBranches(S.owner, S.repo), hit = br.filter(b => b.commit && b.commit.sha === sha).map(b => b.name);
      name = hit.includes("main") ? "main" : hit.includes("master") ? "master" : hit[0] || ""; } catch (e) {}
  }
  name = name || "main"; S.defBranch = {repo:S.owner + "/" + S.repo, name}; return name;
}
async function loadSeries(){
  if (S.seriesFor === S.book.branch + "|" + S.readRef) return S.series;
  let found = null;
  for (const d of (await listDefault("series")).filter(e => e.type === "dir" || (e.type == null && !String(e.name).includes(".")))){
    try { const sy = window.jsyaml.load((await getFile(`series/${d.name}/series.yml`, null, true)).text) || {};
      if ((sy.volumes || []).includes(S.book.branch)){ found = Object.assign({}, sy, {id:sy.id || d.name}); break; } } catch (e) {}
  }
  if (found){
    const files = (await listDefault(`series/${found.id}/characters`)).filter(e => /^char-.+\.md$/.test(e.name));
    found.chars = (await pool(files, 8, async e => { const t = (await getFile(e.path || `series/${found.id}/characters/${e.name}`, null, true)).text, h = front(t); return {id:h.id || e.name.replace(/\.md$/, ""), name:h.name || e.name.replace(/\.md$/, ""), path:`series/${found.id}/characters/${e.name}`, text:t}; })).filter(Boolean);
  }
  S.series = found; S.seriesFor = S.book.branch + "|" + S.readRef; return found;
}
/* alle Figuren des Bandes: eigene und die der Serie; eine eigene mit gleicher ID ist die Kopie */
async function allChars(){
  const own = charItems().map(c => Object.assign({}, c)), ser = await loadSeries().catch(() => null);
  if (!ser) return {items:own, ser:null};
  const byId = new Map(own.map(c => [c.id, c]));
  for (const sc of ser.chars){
    const o = byId.get(sc.id);
    if (o){ o._copy_of = ser.id; o._differs = (await charFile(o)).trim() !== sc.text.trim(); }
    else own.push({id:sc.id, name:sc.name, path:sc.path, _series:ser.id, _text:sc.text});
  }
  return {items:own, ser};
}
const charSource = (it, ser) => !ser ? "" : it._series ? "series" : it._copy_of ? (it._differs ? "copy_diff" : "copy") : "own";
async function commitDefault(files, message, action){
  needWrite();
  const branch = await defaultBranch(); files = files.filter(f => f && typeof f.content === "string"); if (!files.length) return;
  await GW_PORTS.git.pushFiles(branch, files, message, action);
  S.seriesFor = null;   // nächstes Lesen holt den neuen Stand
}

async function charListData(){
  await loadSecFiles(allSecs(), "Figuren werden geladen");
  const used = charUsage(), items = charItems();
  const heads = await pool(items, 8, async it => charParts(await charFile(it)).head);
  const {items:all, ser} = await allChars();
  const headsAll = all.map(it => { const k = items.findIndex(x => x.id === it.id); return it._series ? charParts(it._text).head : (heads[k] || {}); });
  const refs = await refImages().catch(() => []), pics = await pool(all.map((it, i) => portraitOf(it.id, headsAll[i], refs)), 3, ref => portraitData(ref, 80));
  const rows = all.map((it, i) => { const h = headsAll[i] || {}, src = charSource(it, ser); return {C_PORTRAIT:pics[i] || "", C_ID:it.id, C_NAME:it.name, C_ROLE:ROLE_DE[h.role] || "", C_SHORT:h.short || "", C_USED:(used[it.id] || []).join(", ") || "–", C_SOURCE:src, C_SOURCE_TEXT:SOURCE_DE[src] || ""}; });
  return Object.assign(base(), {PROJECT_TITLE_SHORT:shortTitle(), SERIES_TITLE:ser ? ser.title || "" : "", CHARACTERS:rows});
}
async function charEditData(id){
  await loadSecFiles(allSecs());
  const {items:all, ser} = await allChars(), it = all.find(c => c.id === id); if (!it) throw {message:"Figur nicht gefunden."};
  const {head, desc, notes} = charParts(it._series ? it._text : await charFile(it)), names = new Map(all.map(c => [c.id, c.name]));
  const pref = portraitOf(it.id, head, await refImages().catch(() => [])), pic = await portraitData(pref, 192), src = charSource(it, ser);
  return Object.assign(base(), {PROJECT_TITLE_SHORT:shortTitle(), CHARACTER_ID:it.id, CHARACTER_NAME:it.name, CHARACTER_ROLE:head.role || "main", CHARACTER_SHORT:head.short || "",
    CHARACTER_AGE:head.age == null ? "" : String(head.age), CHARACTER_APPEARANCE:head.appearance || "", CHARACTER_TRAITS:(head.traits || []).join(", "), CHARACTER_VOICE:head.voice || "",
    CHARACTER_VISUAL:head.visual || "", CHARACTER_DESCRIPTION:desc, CHARACTER_NOTES:notes, CHARACTER_USED:(charUsage()[it.id] || []).join(", ") || "noch nirgends",
    CHARACTER_PORTRAIT:pic, CHARACTER_PORTRAIT_ID:pic && pref ? pref.id : "", CHARACTER_SOURCE:src, CHARACTER_SOURCE_TEXT:SOURCE_DE[src] || "", SERIES_ID:ser ? ser.id : "", SERIES_TITLE:ser ? ser.title || "" : "",
    RELATIONS:(head.relations || []).map(r => ({R_TO:r.to, R_NAME:names.get(r.to) || r.to, R_KIND:r.kind})), OTHERS:all.filter(c => c.id !== it.id).map(c => ({O_ID:c.id, O_NAME:c.name}))});
}
function charApply(head, desc, notes, d){
  head = Object.assign({}, head);
  for (const k of CHAR_FIELDS.slice(1)){
    if (!(k in d)) continue;
    let v = d[k]; if (typeof v === "string") v = v.trim();
    if (k === "traits" && typeof v === "string") v = v.split(",").map(t => t.trim()).filter(Boolean);
    if (v === "" || v == null || (Array.isArray(v) && !v.length)) delete head[k]; else head[k] = v;
  }
  if (!head.name) throw {message:"Der Name darf nicht leer sein."};
  if (typeof d.description === "string") desc = d.description.trim();
  if (typeof d.notes === "string") notes = d.notes.trim();
  const ordered = {}; CHAR_FIELDS.forEach(k => { const v = head[k]; if (k in head && v !== "" && v != null && !(Array.isArray(v) && !v.length)) ordered[k] = v; });
  const text = "---\n" + window.jsyaml.dump(ordered, {lineWidth:-1}) + "---\n\n" + `# ${ordered.name}\n\n## Beschreibung\n\n` + (desc ? desc + "\n\n" : "") + "## Notizen\n" + (notes ? "\n" + notes + "\n" : "");
  return {ordered, text};
}
function charListWrite(gy, items){
  // Block `characters:` in ghostwriter.yml ersetzen bzw. vor `structure:` einfügen; der Rest bleibt Zeichen für Zeichen
  const block = items.length ? "characters:\n" + items.map(i => `- id: ${i.id}\n  name: ${yq(i.name)}\n  path: ${i.path}\n`).join("") : "";
  const m = /^characters:.*\n(?:(?:[ -].*|)\n)*/m.exec(gy);
  let out;
  if (m) out = gy.slice(0, m.index) + block + gy.slice(m.index + m[0].length);
  else { const st = /^structure:/m.exec(gy); if (!st) throw {message:"ghostwriter.yml: structure nicht gefunden."}; out = gy.slice(0, st.index) + block + gy.slice(st.index); }
  const back = (window.jsyaml.load(out) || {}).characters || [];
  if (back.length !== items.length || back.some((b, i) => b.id !== items[i].id || b.name !== items[i].name)) throw {message:"ghostwriter.yml ließ sich nicht sicher ändern; bitte im Chat mit GhostWriter anlegen."};
  return out;
}
async function characterCreate(d){
  busy("Figur wird angelegt …");
  try {
    const name = String(d.name || "").trim(); if (!name) throw {message:"Der Name fehlt."};
    const work = await prepareWork(); await loadBookData(work);
    const items = charItems(), known = (await allChars()).items;
    if (known.some(i => String(i.name).toLowerCase() === name.toLowerCase())) throw {message:`Die Figur „${name}“ gibt es schon.`};
    let cid = "char-" + (tagSlug(name) || "figur"), n = 2; const used = new Set(known.map(i => i.id));
    const base0 = cid; while (used.has(cid)){ cid = `${base0}-${n++}`; }
    const role = ["main", "supporting", "minor"].includes(d.role) ? d.role : "main", path = `characters/${cid}.md`;
    const file = `---\nid: ${cid}\nname: ${yq(name)}\nrole: ${role}\nshort: ""\n---\n\n# ${name}\n\n## Beschreibung\n\n<Wer ist die Figur, was will sie, was fürchtet sie? Nur Arbeitsgrundlage, kommt nicht ins Buch.>\n\n## Notizen\n`;
    const gy = (await getFile("ghostwriter.yml", work, true)).text;
    const files = {"ghostwriter.yml":charListWrite(gy, [...items.map(i => ({id:i.id, name:i.name, path:i.path})), {id:cid, name, path}]), [path]:file}, orig = {"ghostwriter.yml":gy, [path]:null};
    const r = await commit(changed(files, orig), `Figur „${name}“ angelegt`, {action:"character.create"});
    S.msg = savedMsg(`Figur „${name}“ angelegt.`, r);
  } catch (e) { S.msg = failMsg(e); }
  S.from = null; show("characters");
}
async function characterUpdate(d){
  busy("Wird gespeichert …");
  try {
    const work = await prepareWork(); await loadBookData(work);
    const it = charItems().find(c => c.id === d.character_id);
    if (!it){ const sc = ((await allChars()).items.find(c => c.id === d.character_id)); throw {message:sc && sc._series ? `„${sc.name}“ gehört zur Serie: dort bearbeiten (gilt für alle Bände) oder für dieses Buch eine Kopie anlegen.` : "Figur nicht gefunden."}; }
    const cur = await charFile(it, work), {head, desc, notes} = charParts(cur), {ordered, text} = charApply(head, desc, notes, d);
    const files = {[it.path]:text}, orig = {[it.path]:cur};
    if (ordered.name !== it.name){
      const gy = (await getFile("ghostwriter.yml", work, true)).text; orig["ghostwriter.yml"] = gy;
      files["ghostwriter.yml"] = charListWrite(gy, charItems().map(i => ({id:i.id, name:i.id === it.id ? ordered.name : i.name, path:i.path})));
    }
    const r = await commit(changed(files, orig), `Figur „${ordered.name}“ bearbeitet`, {action:"character.update"});
    S.msg = savedMsg("Figur gespeichert.", r);
  } catch (e) { S.msg = failMsg(e); }
  S.from = null; show("characters");
}

async function characterSeries(kind, d){
  const labels = {update:"Figur der Serie wird gespeichert …", detach:"Kopie wird angelegt …", align:"Wird angeglichen …", adopt:"Figur wird in die Serie übernommen …"};
  busy(labels[kind]);
  try {
    const work = await prepareWork(); await loadBookData(work); S.seriesFor = null;
    const {items:all, ser} = await allChars(); if (!ser) throw {message:"Dieses Buch gehört zu keiner Serie."};
    const it = all.find(c => c.id === d.character_id); if (!it) throw {message:"Figur nicht gefunden."};
    const own = charItems().map(c => ({id:c.id, name:c.name, path:c.path}));
    if (kind === "update"){
      if (!it._series) throw {message:`„${it.name}“ gehört nicht zur Serie.`};
      const sc = ser.chars.find(c => c.id === it.id), cur = (await getFile(sc.path, null, true)).text, {head, desc, notes} = charParts(cur), {ordered, text} = charApply(head, desc, notes, d);
      await commitDefault([{path:sc.path, content:text}], `Figur „${ordered.name}“ der Serie gespeichert`, "character.series.update");
      S.msg = {kind:"ok", html:`<b>Figur „${esc(ordered.name)}“ der Serie gespeichert.</b> Sie gilt in allen Bänden ohne eigene Kopie. Gespeichert wurde direkt auf dem Standard-Branch (kein Änderungspaket).`};
    } else if (kind === "detach"){
      if (!it._series) throw {message:`„${it.name}“ ist keine Figur der Serie${it._copy_of ? " (schon eine Kopie)" : ""}.`};
      const path = `characters/${it.id}.md`, gy = (await getFile("ghostwriter.yml", work, true)).text;
      const files = {[path]:it._text, "ghostwriter.yml":charListWrite(gy, [...own, {id:it.id, name:it.name, path}])}, orig = {[path]:null, "ghostwriter.yml":gy};
      S.msg = savedMsg(`Kopie von „${it.name}“ nur für dieses Buch angelegt.`, await commit(changed(files, orig), `Figur „${it.name}“: Kopie für dieses Buch`, {action:"character.detach"}));
    } else if (kind === "align"){
      if (!it._copy_of) throw {message:`„${it.name}“ ist keine Kopie einer Figur der Serie.`};
      const gy = (await getFile("ghostwriter.yml", work, true)).text, files = {"ghostwriter.yml":charListWrite(gy, own.filter(c => c.id !== it.id))}, orig = {"ghostwriter.yml":gy};
      const r = await commit(changed(files, orig), `Figur „${it.name}“ an die Serie angeglichen`, {action:"character.align"});
      S.msg = savedMsg(`„${it.name}“ gilt wieder so wie in der Serie.`, r); S.msg.html += ` <span class="dim">Die Datei <code>${esc(it.path)}</code> bleibt im Buch liegen, weil die App keine Dateien löschen kann; sie wird nicht mehr benutzt.</span>`;
    } else {
      if (it._series) throw {message:`„${it.name}“ gehört schon zur Serie.`};
      const text = await charFile(it, work), dest = `series/${ser.id}/characters/${it.id}.md`;
      await commitDefault([{path:dest, content:text}], `Figur „${it.name}“ gehört jetzt zur Serie`, "character.adopt");
      const gy = (await getFile("ghostwriter.yml", work, true)).text, files = {"ghostwriter.yml":charListWrite(gy, own.filter(c => c.id !== it.id))}, orig = {"ghostwriter.yml":gy};
      const r = await commit(changed(files, orig), `Figur „${it.name}“ in die Serie übernommen`, {action:"character.adopt"});
      S.msg = savedMsg(`„${it.name}“ gehört jetzt zur Serie und gilt in allen Bänden.`, r); S.msg.html += ` <span class="dim">Die Datei <code>${esc(it.path)}</code> bleibt im Buch liegen, weil die App keine Dateien löschen kann; sie wird nicht mehr benutzt.</span>`;
    }
  } catch (e) { S.msg = failMsg(e); }
  S.from = null; show("characters");
}

/* Figuren aus dem Text vorschlagen (#53): Claude liest die Texte, es entsteht nur ein Vorschlag; übernommen wird nach Auswahl */
const SUGGEST_FIELDS = ["role", "short", "age", "appearance", "traits", "voice"], SUGGEST_SIZE = 40000;
function suggestScope(scope){
  // → {scope: book | N | N.M, list: [[Schlüssel, Titel, Abschnitt]]} oder null (Teile von Vor-/Nachspann und Serien gibt es hier noch nicht)
  const chs = chapters(); scope = String(scope || "book").trim();
  const sec = (ci, si) => [`${ci + 1}.${si + 1}`, chs[ci].sections[si].title, chs[ci].sections[si]];
  if (scope === "book" || scope === "buch") return {scope:"book", list:allSecs().map(({c, s}) => sec(chs.indexOf(c), c.sections.indexOf(s)))};
  if (/^\d+$/.test(scope)){ const ci = +scope - 1; return chs[ci] ? {scope, list:chs[ci].sections.map((x, si) => sec(ci, si))} : null; }
  if (/^\d+\.\d+$/.test(scope)){ const [a, b] = scope.split(".").map(Number); return chs[a - 1] && chs[a - 1].sections[b - 1] ? {scope, list:[sec(a - 1, b - 1)]} : null; }
  const x = allSecs().find(v => v.s.id === scope); if (x){ const ci = chs.indexOf(x.c), si = x.c.sections.indexOf(x.s); return {scope:`${ci + 1}.${si + 1}`, list:[sec(ci, si)]}; }
  const ci = chs.findIndex(c => c.id === scope); return ci >= 0 ? {scope:String(ci + 1), list:chs[ci].sections.map((y, si) => sec(ci, si))} : null;
}
const scopeText = sc => sc === "book" ? "ganzes Buch" : /^\d+$/.test(sc) ? "Kapitel " + sc : "Abschnitt " + sc;
function parseSuggest(text){
  const m = /```(?:json)?\s*([\s\S]*?)```/.exec(text) || [null, text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1)];
  try { const o = JSON.parse(m[1]); return Array.isArray(o) ? o : (o.items || []); } catch (e) { return null; }
}
const norm = t => String(t || "").replace(/\s+/g, " ").trim().toLowerCase();
function mergeSuggest(into, items){
  for (const it of items){
    if (!it || !String(it.name || "").trim()) continue;
    const names = [it.name, ...(it.aliases || [])].map(norm);
    const hit = into.find(x => [x.name, ...(x.aliases || [])].map(norm).some(n => names.includes(n)));
    if (!hit){ into.push(Object.assign({aliases:[], traits:[], relations:[], sections:[], evidence:[]}, it)); continue; }
    ["role", "short", "age", "appearance", "voice"].forEach(k => { if (!hit[k] && it[k]) hit[k] = it[k]; });
    const add = (k, key) => { (it[k] || []).forEach(v => { if (!(hit[k] || (hit[k] = [])).some(w => key(w) === key(v))) hit[k].push(v); }); };
    add("aliases", norm); add("traits", norm); add("sections", String); add("relations", r => norm(r.to) + "|" + norm(r.kind)); add("evidence", e => norm(e.where) + "|" + norm(e.quote));
  }
}
function matchChar(it, items){
  const names = [it.name, ...(it.aliases || [])].map(norm).filter(Boolean);
  return items.find(c => names.includes(norm(c.name)) || names.includes(c.id));
}
async function characterSuggest(d){
  const sc = suggestScope(d.scope);
  if (!sc){ S.msg = {kind:"info", html:"<b>Das geht in dieser App noch nicht für diesen Bereich.</b> Figuren aus dem Text schlägt die App für das ganze Buch, ein Kapitel oder einen Abschnitt vor."}; return show("characters"); }
  if (!S.sample){ S.msg = {kind:"warn", html:"Claude ist in dieser Ansicht nicht verfügbar."}; return show("characters"); }
  try {
    busy("Texte werden gelesen …");
    const files = await loadSecFiles(sc.list.map(([, , s]) => ({s})), "Texte werden gelesen");
    const blocks = sc.list.map(([key, title, s], i) => { const ms = files[i] ? msOf(files[i].text).trim() : ""; return EMPTY_MS.includes(ms) ? null : {key, text:`### ${key} ${title}\n\n${ms}\n`}; }).filter(Boolean);
    if (!blocks.length){ S.msg = {kind:"info", html:"In diesem Bereich steht noch kein Text. Schreibe zuerst etwas, dann kann ich Figuren vorschlagen."}; return show("characters"); }
    const chunks = []; let cur = [], len = 0;
    for (const b of blocks){ if (cur.length && len + b.text.length > SUGGEST_SIZE){ chunks.push(cur); cur = []; len = 0; } cur.push(b); len += b.text.length; }
    if (cur.length) chunks.push(cur);
    const {items:allKnown, ser:serK} = await allChars(), known = allKnown.map(c => `- ${c.name} (${c.id}${c._series ? ", Serie" : ""})`).join("\n") || "keine";
    const found = [];
    for (let i = 0; i < chunks.length; i++){
      busy(`Figuren werden gesucht – Teil ${i + 1} von ${chunks.length} …`);
      const body = chunks[i].map(b => b.text).join("\n");
      const prompt = `Du liest Textabschnitte eines Buchs und schlägst Figuren vor – nur aus dem Text, nichts erfinden, nichts aus Weltwissen ergänzen. Was der Text nicht sagt, bleibt leer. Personen, die nur erwähnt werden (Autoren von Quellen, Fachleute im Sachbuch), nur vorschlagen, wenn sie im Text handeln oder sprechen. Dieselbe Person unter mehreren Namen zusammenführen (aliases).\n\nBEKANNTE FIGUREN\n${known}\n\nAntworte NUR mit einem JSON-Block, ohne weiteren Text:\n\`\`\`json\n{"items":[{"name":"","aliases":[],"role":"main|supporting|minor","short":"ein Satz","age":"","appearance":"","traits":[],"voice":"","relations":[{"to":"Name der anderen Figur","kind":"Art"}],"sections":["1.2"],"evidence":[{"where":"1.2","quote":"kurze wörtliche Stelle aus dem Text"}]}]}\n\`\`\`\n"sections" nennt die Abschnittsnummern (wie in den Überschriften ###), in denen die Figur vorkommt.\n\nTEXT (Teil ${i + 1} von ${chunks.length})\n\n${body}`;
      const r = await S.sample([{role:"user", content:prompt}], {cache:false, onText:() => {}});
      const items = parseSuggest(r.text || ""); if (!items) throw {message:"Claude hat keine auswertbare Antwort geliefert. Bitte nochmals versuchen."};
      const src = norm(chunks[i].map(b => b.text).join(" "));
      items.forEach(it => { it.evidence = (it.evidence || []).filter(e => e && e.quote && src.includes(norm(e.quote))); });   // Fundstellen prüfen, ohne KI
      mergeSuggest(found, items);
    }
    S.suggest = {scope:sc.scope, items:found};
    const known2 = allKnown, rows = found.map((it, i) => {
      const hit = matchChar(it, known2), details = [it.age ? "Alter: " + it.age : "", it.appearance || "", (it.traits || []).join(", "), it.voice ? "spricht: " + it.voice : ""].filter(Boolean).join("; ");
      return {S_IDX:i, S_NAME:it.name, S_ALIASES:(it.aliases || []).join(", "), S_ROLE:["main", "supporting", "minor"].includes(it.role) ? it.role : "supporting", S_SHORT:it.short || "", S_DETAILS:details, S_SECTIONS:(it.sections || []).join(", "),
        S_EVIDENCE:(it.evidence || []).slice(0, 3).map(e => `${e.where || ""}: „${e.quote}“`).join(" · "), S_STATE:hit ? (hit._series ? "series" : "existing") : "new", S_EXISTING:hit ? hit.name : "", S_STATE_TEXT:hit ? (hit._series ? "Figur der Serie: " : "schon da: ") + hit.name : "neu"};
    });
    S.from = {view:"characters"}; S.msg = null;
    return form("figuren-vorschlag", Object.assign(base(), {SCOPE:sc.scope, SCOPE_TEXT:scopeText(sc.scope), SUGGEST_COUNT_TEXT:plural(rows.length, "Vorschlag", "Vorschläge"), SERIES_ID:serK ? serK.id : "", SERIES_TITLE:serK ? serK.title || "" : "", RUN_ID:"", RUN_TEXT:"", CONFLICTS_TEXT:"", SERIES_LEVEL:"",
      SUGGESTIONS:rows, MERGE:allKnown.map(c => ({M_ID:c.id, M_NAME:c.name}))}));
  } catch (e) { S.msg = e.code ? {kind:"err", html:esc(e.code === "not_granted" ? "Claude ist für diese App nicht freigegeben." : e.code === "rate_limited" ? "Dein Claude-Kontingent ist gerade ausgeschöpft. Bitte später noch einmal versuchen." : errText(e))} : {kind:"err", html:esc(errText(e))}; show("characters"); }
}
function setSecChars(text, ids){
  const m = /^---\n([\s\S]*?)\n---\n/.exec(text); if (!m) return text;
  let head = (m[1] + "\n").replace(/^characters:.*\n?/m, "").replace(/\n+$/, "");
  if (ids.length){ const line = "characters: [" + ids.join(", ") + "]"; head = /^approvals:/m.test(head) ? head.replace(/^approvals:/m, line + "\napprovals:") : head + "\n" + line; }
  return "---\n" + head + "\n---\n" + text.slice(m[0].length);
}
async function characterSuggestApply(d){
  busy("Figuren werden übernommen …");
  try {
    const sug = S.suggest; if (!sug || !Array.isArray(d.choices)) throw {message:"Der Vorschlag ist nicht mehr da. Bitte die Figuren nochmals vorschlagen lassen."};
    const picked = d.choices.map(c => Object.assign({}, sug.items[c.index], {name:String(c.name || "").trim(), role:c.role, short:c.short, merge_into:c.merge_into, target:c.target})).filter(it => it.name);
    const work = await prepareWork(); await loadBookData(work);
    const gy = (await getFile("ghostwriter.yml", work, true)).text, list = charItems().map(c => ({id:c.id, name:c.name, path:c.path}));
    S.seriesFor = null; const {items:known, ser} = await allChars(), seriesFiles = [], seriesCreated = [];
    const files = {}, orig = {"ghostwriter.yml":gy}, ids = {}, created = [], updated = [], texts = {};
    const text = async path => { if (!(path in texts)){ texts[path] = files[path] != null ? files[path] : (await getFile(path, work, true).catch(() => ({text:""}))).text; orig[path] = texts[path] || null; } return texts[path]; };
    const put = (path, t) => { files[path] = t; texts[path] = t; };
    for (const it of picked){
      const hit = it.merge_into ? known.find(c => c.id === it.merge_into || norm(c.name) === norm(it.merge_into)) : matchChar(it, known);
      if (hit){
        ids[it.name] = hit.id;
        if (hit._series) continue;   // Figuren der Serie bleiben unverändert
        const {head, desc, notes} = charParts(await text(hit.path)), fill = {};
        SUGGEST_FIELDS.forEach(k => { if (it[k] && !head[k] && !(Array.isArray(it[k]) && !it[k].length)) fill[k] = it[k]; });
        if (Object.keys(fill).length){ put(hit.path, charApply(head, desc, notes, fill).text); updated.push(hit.name); }
        continue;
      }
      const toSeries = it.target === "series" && ser;
      let cid = "char-" + (tagSlug(it.name) || "figur"), n = 2; const b0 = cid; while (known.some(c => c.id === cid) || list.some(c => c.id === cid)) cid = `${b0}-${n++}`;
      const role = ["main", "supporting", "minor"].includes(it.role) ? it.role : "supporting", path = toSeries ? `series/${ser.id}/characters/${cid}.md` : `characters/${cid}.md`;
      const start = `---\nid: ${cid}\nname: ${yq(it.name)}\nrole: ${role}\nshort: ${yq(it.short || "")}\n---\n\n# ${it.name}\n\n## Beschreibung\n\n<Wer ist die Figur, was will sie, was fürchtet sie? Nur Arbeitsgrundlage, kommt nicht ins Buch.>\n\n## Notizen\n`;
      const {head, desc, notes} = charParts(start), fill = {}; SUGGEST_FIELDS.slice(2).forEach(k => { if (it[k] && !(Array.isArray(it[k]) && !it[k].length)) fill[k] = it[k]; });
      const body = Object.keys(fill).length ? charApply(head, desc, notes, fill).text : start;
      if (toSeries){ seriesFiles.push({path, content:body}); known.push({id:cid, name:it.name, path, _series:ser.id}); ids[it.name] = cid; seriesCreated.push(it.name); continue; }
      put(path, body); orig[path] = null;
      list.push({id:cid, name:it.name, path}); known.push({id:cid, name:it.name, path}); ids[it.name] = cid; created.push(it.name);
    }
    for (const it of picked){   // Beziehungen: nur neue Einträge
      const cid = ids[it.name], c = list.find(x => x.id === cid), rels = (it.relations || []).filter(r => r && r.to && r.kind);
      if (!c || !rels.length) continue;
      const {head, desc, notes} = charParts(await text(c.path)), have = new Set((head.relations || []).map(r => r.to + "|" + r.kind)), next = [...(head.relations || [])];
      for (const r of rels){ const o = known.find(x => x.id === (ids[r.to] || r.to) || norm(x.name) === norm(r.to)); if (o && o.id !== cid && !have.has(o.id + "|" + r.kind)){ next.push({to:o.id, kind:r.kind}); have.add(o.id + "|" + r.kind); } }
      if (next.length !== (head.relations || []).length) put(c.path, charApply(head, desc, notes, {relations:next}).text);
    }
    const bySec = {};   // Zuordnung zu Abschnitten: ergänzen, nichts entfernen
    for (const it of picked) for (const key of it.sections || []) if (/^\d+\.\d+$/.test(String(key))) (bySec[key] = bySec[key] || []).push(ids[it.name]);
    for (const [key, add] of Object.entries(bySec)){
      const [a, b] = key.split(".").map(Number), sec = chapters()[a - 1] && chapters()[a - 1].sections[b - 1]; if (!sec) continue;
      const t = await text(sec.path), have = front(t).characters || [], merged = [...have, ...add.filter((v, i) => v && !have.includes(v) && add.indexOf(v) === i)];
      if (merged.length !== have.length) put(sec.path, setSecChars(t, merged));
    }
    if (created.length) files["ghostwriter.yml"] = charListWrite(gy, list);
    if (seriesFiles.length) await commitDefault(seriesFiles, `Figuren der Serie aus dem Text übernommen (${seriesFiles.length} neu)`, "character.suggest.apply");
    const r = await commit(changed(files, orig), `Figuren aus dem Text übernommen (${created.length} neu, ${updated.length} ergänzt)`, {action:"character.suggest.apply"});
    S.suggest = null; S.msg = savedMsg(`Figuren übernommen: ${created.length} neu, ${updated.length} ergänzt${seriesCreated.length ? `, ${seriesCreated.length} als Figur der Serie` : ""}.`, r);
  } catch (e) { S.msg = failMsg(e); }
  S.from = null; show("characters");
}

