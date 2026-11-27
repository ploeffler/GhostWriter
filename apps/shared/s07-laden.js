/* ---------- Laden ---------- */
async function loadRepo(spec){
  const m = /(?:github\.com\/)?([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/.exec(spec.trim());
  if (!m){ S.msg = {kind:"err", html:"Bitte als owner/repo eingeben."}; return show("connect"); }
  [S.owner, S.repo] = [m[1], m[2]]; store.set("gw.repo", S.owner + "/" + S.repo); S.files.clear(); S.lib = null; S.libCfg = undefined; S.webJobs = {};
  busy("Bücherregal wird geladen …");
  try { S.lib = JSON.parse((await getFile("library.json")).text); }
  catch (e) {
    try { await getFile("ghostwriter-index.json"); S.lib = {books:[{branch:"main", title:S.repo, status:"ready", work_branch:"ghostwriter/main"}]}; }
    catch (e2) { S.msg = {kind:"err", html:esc(await repoMissingText(e))}; S.owner = ""; return show("connect"); }
  }
  S.msg = null;
  if ((S.lib.books || []).length === 1) return openBook(S.lib.books[0].branch);
  show("library");
}
async function repoMissingText(e){   // #729: ein 404 auf library.json heißt nicht „Fehler der App“; erst klären, ob das Repository erreichbar ist
  if (!e || e.code !== "http_404") return errText(e);
  const name = S.owner + "/" + S.repo;
  try { await GW_PORTS.git.listDir("", ""); }
  catch (e3) {
    if (e3 && e3.code === "http_404") return "„" + name + "“ wurde nicht gefunden – oder der Token hat dafür keinen Zugriff (bei privaten Repositories antwortet GitHub ebenfalls mit „nicht gefunden“). Prüfe owner/repo und ob der Token genau dieses Repository enthält.";
    return errText(e3);
  }
  return "„" + name + "“ ist erreichbar, enthält aber weder ein Bücherregal (library.json) noch ein Buch (ghostwriter-index.json). Ein Programm-Repository ist kein Buch: Wähle das Repository, in dem dein Buch oder deine Bibliothek liegt.";
}
async function loadBookData(ref, overlay){
  S.readRef = ref; S.files.clear();
  S.idx = {project:{}, chapters:[]};
  try { const ix = await getFile("ghostwriter-index.json", ref, true); S.idx = JSON.parse(ix.text); S.head = ix.commit || S.head; } catch (e) {}
  const gy = await getFile("ghostwriter.yml", ref, true); if (gy.commit) S.head = gy.commit;
  S.cfg = {}; try { S.cfg = window.jsyaml.load(gy.text) || {}; } catch (e) {}
  buildStruct();
  S.checks = []; try { const d = window.jsyaml.load((await getFile("editorial/checks.yml", ref)).text); S.checks = ((d && d.checks) || []).filter(e => e && e.kind && e.result); } catch (e) {}
  S.rules = await getFile("SCHREIBREGELN.md", ref).then(f => f.text.slice(0, 8000)).catch(() => "");
  // nur lokal gespeicherte Änderungen (Anschluss mit Outbox, #662) liegen über dem Stand von GitHub, bis sie hochgeladen sind
  const pend = GW_PORTS.outbox && S.book ? await GW_PORTS.outbox.overlay(S.book.branch).catch(() => []) : [];
  if (pend.length || overlay) applyOverlay(ref, pend.concat(overlay || []));
}
function applyOverlay(ref, overlay){ // eben Geschriebenes sofort zeigen, auch wenn GitHub noch den alten Stand liefert
  overlay.forEach(f => { const k = ref + "|" + f.path, o = S.files.get(k); if (!o || o.text !== f.content) S.files.set(k, {text:f.content, commit:(o && o.commit) || S.head, sha:""}); });
  const g = overlay.slice().reverse().find(f => f.path === "ghostwriter.yml"); if (g){ try { S.cfg = window.jsyaml.load(g.content) || S.cfg; } catch (e) {} buildStruct(); }
}
function buildStruct(){
  const ixC = new Map((S.idx.chapters || []).map(c => [c.id, c])), ixS = new Map((S.idx.chapters || []).flatMap(c => (c.sections || []).map(s => [s.id, s])));
  const src = (S.cfg.structure && S.cfg.structure.chapters) || S.idx.chapters || [];
  S.struct = src.map(c => ({id:c.id, title:c.title, path:c.path, status:c.status || (ixC.get(c.id) || {}).status || "planned", cost:(ixC.get(c.id) || {}).cost,
    sections:(c.sections || []).map(s => ({id:s.id, title:s.title, path:s.path, status:(ixS.get(s.id) || {}).status || "planned", cost:(ixS.get(s.id) || {}).cost}))}));
}
async function openBook(branch){
  S.book = (S.lib.books || []).find(b => b.branch === branch); if (!S.book) return;
  S.chap = null; S.sec = null; S.chat = []; S.msg = null; S.showAll = false; crumbs(); busy("Buch wird geöffnet …");
  try {
    S.pr = await openPR(S.book).catch(() => null);
    if (S.pr) await prCommits(S.pr);
    await loadBookData(S.pr ? workOf(S.book) : S.book.branch);
    S.skills = null; S.skillsFor = ""; loadSkills().then(() => { if (S.view === "project" || S.view === "chapter" || S.view === "section") { const h = document.querySelector(".claude .ch-head p"); if (h) h.innerHTML = skillLine(h.dataset.base || h.textContent); } }).catch(() => {});
    show("project");
  } catch (e) { S.msg = {kind:"err", html:esc(errText(e))}; S.book = null; show("library"); }
}

