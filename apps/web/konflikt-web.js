/* ---------- Konflikt lösen (#662): lokale Fassung und GitHub-Fassung nebeneinander ----------
   Je Stelle (Absatz), an der beide Seiten verschieden geändert haben: „Meins behalten“, „GitHub übernehmen“, „Beides behalten“ (beide untereinander mit
   der Marke [KONFLIKT PRÜFEN: …]) oder „Selbst zusammenfügen“. Alles Übrige ist schon zusammengeführt. „Später – nichts verlieren“ legt den lokalen Stand
   auf einem eigenen Branch ab. Ohne Ausgangstext (ältere Einträge) gilt die Wahl für die ganze Datei. Es wird nie ohne ausdrückliche Wahl überschrieben. */
const KF = {id:0, chunks:null, remote:null, path:"", whole:false, back:null};
const kfSlug = t => String(t).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 30) || "buch";
async function kfOpen(id){
  const e = (await OB.all()).find(x => x.id === id); if (!e) return obRender();
  KF.back = KF.back || {view:S.view, arg:S.view === "section" ? S.sec && S.sec.id : S.chap};
  busy("Stand auf GitHub wird geholt …");
  try {
    const path = (e.conflict && e.conflict.path) || e.files[0].path, b = {branch:e.book.branch, work_branch:e.book.work_branch || undefined};
    const remote = await getFile(path, workOf(b), true), local = e.files.find(f => f.path === path).content;
    if (remote.text === local){ await OB.del(e.id); await obRender(true); S.msg = {kind:"ok", html:"Kein Konflikt mehr: GitHub hat schon dieselbe Fassung."}; return show(KF.back.view, KF.back.arg); }
    const base = e.base && e.base[path];
    Object.assign(KF, {id:e.id, path, remote, whole:typeof base !== "string", chunks:typeof base === "string" ? merge3(base, local, remote.text) : null});
    kfRender(e, remote, local);
  } catch (err) { S.msg = {kind:"err", html:esc(errText(err))}; show(KF.back.view, KF.back.arg); }
}
function kfRender(e, remote, local){
  const place = obPlace(KF.path);
  const approved = /approvals:[\s\S]{0,200}?section:\s*true/.test(remote.text.split("\n---")[0] || "");
  const opts = (n, who) => `<div class="kfopt"><label><input type="radio" name="c${n}" value="local"> Meins behalten</label> <label><input type="radio" name="c${n}" value="remote"> GitHub übernehmen</label> <label><input type="radio" name="c${n}" value="both"> Beides behalten</label> <label><input type="radio" name="c${n}" value="hand"> Selbst zusammenfügen</label></div>`;
  let n = 0, body;
  if (KF.whole){
    body = `<p class="dim">Zu diesem Eintrag gibt es keinen Ausgangstext; deshalb gilt die Wahl für die ganze Datei.</p><section class="kfc" data-i="0"><div class="kfcols"><div><b>Dieses Gerät</b><pre>${esc(local)}</pre></div><div><b>GitHub</b><pre>${esc(remote.text)}</pre></div></div>${opts(0)}<textarea class="in kfhand" rows="8" hidden>${esc(local)}</textarea></section>`;
    KF.chunks = [{conflict:{base:[], local:[local], remote:[remote.text]}}];
  } else {
    const done = KF.chunks.filter(c => typeof c === "string").length;
    body = `<p class="dim">${done} Absätze sind schon zusammengeführt. An ${m3Conflicts(KF.chunks)} ${m3Conflicts(KF.chunks) === 1 ? "Stelle" : "Stellen"} wurde derselbe Bereich auf beiden Seiten verschieden geändert:</p>` +
      KF.chunks.filter(c => typeof c !== "string").map(c => { const i = n++; return `<section class="kfc" data-i="${i}"><div class="kfcols"><div><b>Dieses Gerät</b><pre>${esc(c.conflict.local.join("\n\n") || "(gelöscht)")}</pre></div><div><b>GitHub</b><pre>${esc(c.conflict.remote.join("\n\n") || "(gelöscht)")}</pre></div></div>${opts(i)}<textarea class="in kfhand" rows="6" hidden>${esc(c.conflict.local.join("\n\n"))}</textarea></section>`; }).join("");
  }
  $("app").innerHTML = `<div class="one"><div class="card"><b style="font-size:18px">Konflikt in ${esc(place)}</b>
    <p class="dim">Dieselbe Stelle wurde auf diesem Gerät und auf GitHub verschieden geändert. Nichts wird überschrieben, bis du entschieden hast.</p>
    ${approved ? '<div class="note warn">Auf GitHub ist dieser Abschnitt inzwischen <b>abgeschlossen</b>. Nach dem Zusammenführen weicht der Text von der Freigabe ab und muss neu abgeschlossen werden.</div>' : ""}
    <form id="fKonflikt">${body}<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px"><button class="btn pri" data-kf="apply">Zusammenführen und hochladen</button><button type="button" class="btn" data-kf="later">Später – nichts verlieren</button><button type="button" class="btn" data-kf="cancel">Zurück</button></div></form>
    <div id="kfmsg" class="dim" style="margin-top:8px"></div></div></div>
    <style>.kfcols{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:700px){.kfcols{grid-template-columns:1fr}}.kfcols pre{white-space:pre-wrap;background:var(--surface-2,#f1efe7);padding:8px;border-radius:6px;font-size:13px}.kfc{border-top:.5px solid var(--border,#d6d3c8);padding:10px 0}.kfopt label{margin-right:12px;font-size:13px}</style>`;
}
async function kfApply(){
  const e = (await OB.all()).find(x => x.id === KF.id); if (!e) return;
  const choice = [], msg = $("kfmsg");
  const secs = [...document.querySelectorAll("#fKonflikt .kfc")];
  for (const s of secs){
    const v = (s.querySelector("input:checked") || {}).value;
    if (!v){ msg.textContent = "Bitte bei jeder Stelle eine Möglichkeit wählen."; return; }
    choice.push(v === "hand" ? s.querySelector("textarea").value : v);
  }
  const text = m3Join(KF.chunks, choice), f = e.files.find(x => x.path === KF.path);
  f.content = text; e.seen[KF.path] = KF.remote.sha; e.base = Object.assign(e.base || {}, {[KF.path]:KF.remote.text}); e.state = "wartet"; delete e.conflict; e.merged = true;
  await OB.put(e); const back = KF.back; KF.back = null; KF.chunks = null;
  S.msg = {kind:"ok", html:"<b>Zusammengeführt.</b> Es wird jetzt hochgeladen."}; show(back.view, back.arg);
  await GW_PORTS.outbox.flush();
}
async function kfLater(){
  const e = (await OB.all()).find(x => x.id === KF.id); if (!e) return;
  const name = `ghostwriter/konflikt-${kfSlug(e.book.branch)}-${new Date().toISOString().slice(0, 10)}-${e.id}`, work = workOf({branch:e.book.branch, work_branch:e.book.work_branch || undefined});
  $("kfmsg").textContent = "Wird auf einem eigenen Branch abgelegt …";
  try {
    try { await GW_PORTS.git.createBranch(name, work); } catch (x) { if (!/already exists|Reference already/i.test((x && x.message) || "")) throw x; }
    await GW_PORTS.git.pushFiles(name, e.files, e.message + " (Konflikt, zur Klärung abgelegt)", e.action);
    e.state = "spaeter"; e.branch = name; await OB.put(e);
    const back = KF.back; KF.back = null; KF.chunks = null; S.msg = {kind:"ok", html:`<b>Abgelegt.</b> Dein Stand liegt auf dem Branch <code>${esc(name)}</code> und geht nicht verloren. Der Konflikt bleibt oben markiert, bis er gelöst ist.`};
    await obRender(); show(back.view, back.arg);
  } catch (err) { $("kfmsg").textContent = "Nicht abgelegt: " + errText(err); }
}
document.addEventListener("click", ev => {
  const r = ev.target.closest && ev.target.closest('[data-act="outbox-resolve"]');
  if (r){ ev.preventDefault(); kfOpen(Number(r.dataset.id)); return; }
  const b = ev.target.closest && ev.target.closest("[data-kf]"); if (!b) return;
  ev.preventDefault();
  if (b.dataset.kf === "apply") kfApply(); else if (b.dataset.kf === "later") kfLater();
  else { const back = KF.back || {view:"project"}; KF.back = null; show(back.view, back.arg); }
});
document.addEventListener("change", ev => {
  if (!ev.target.matches || !ev.target.matches('#fKonflikt input[type="radio"]')) return;
  const ta = ev.target.closest(".kfc").querySelector("textarea"); ta.hidden = ev.target.value !== "hand";
});
