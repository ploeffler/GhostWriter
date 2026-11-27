/* ---------- Ausgabe und Läufe: Actions starten und Ergebnisse holen (#662) ----------
   Probedruck, Vorabfassung, Manuskript ausgeben und Auschecken zum Gegenlesen starten die Actions des Buch-Repositorys per workflow_dispatch (Vertrag: templates/ui/BEFUELLUNG.md,
   Aktionstabelle). Die App zeigt die letzten Läufe mit Stand und Link (Ergebnisse stehen auf der Laufseite unter „Artifacts“, 14 Tage) und die letzten Releases mit Dateien.
   Der Token braucht dafür zusätzlich „Actions“: Lesen und Schreiben. Was Geld oder sichtbare Spuren kostet (Vorabfassung: Tag und Pre-Release; Auschecken sperrt einen Bereich),
   fragt vorher mit einem zweiten Klick nach; nie wird ohne Klick gestartet. Es gibt keinen Abruf im Takt: nur solange ein gestarteter Lauf läuft und die Ansicht offen ist. */
const RUN = {back:null, timer:0, until:0, focus:"", pending:{}, msg:"", scope:""};
/* Umfang (v1.6): im Buch nur dessen Läufe und Auflagen, ohne Buch (Bücherregal) oder auf Wunsch („Alle Läufe der Bibliothek“) alle Läufe des Repositorys */
const runsScope = () => S.book && RUN.scope !== "lib" ? "book" : "lib";
const runBookOf = r => (S.lib && S.lib.books || []).find(b => b.branch === r.branch || workOf(b) === r.branch);
async function runsFetch(){
  if (runsScope() !== "book") return GW_PORTS.git.listRuns(null, {perPage:30});
  const b = S.book, [a, c] = await Promise.all([GW_PORTS.git.listRuns(null, {perPage:15, branch:b.branch}), GW_PORTS.git.listRuns(null, {perPage:15, branch:workOf(b)}).catch(() => [])]);
  return a.concat(c).sort((x, y) => Date.parse(y.created) - Date.parse(x.created)).slice(0, 15);
}
function runRelOfBook(r){   // Auflagen und Vorabfassungen tragen Kurztitel oder Buchname im Tag bzw. Namen; im Einzelbuch (Standard-Branch) gehören alle dazu
  const b = S.book; if (!b || !/^buch\//.test(b.branch)) return true;
  const slug = b.branch.replace(/^buch\//, "").toLowerCase(), hay = ((r.tag || "") + " " + (r.name || "")).toLowerCase();
  return hay.includes(slug) || [b.title_short, b.title].some(t => t && hay.includes(String(t).toLowerCase()));
}
const RUN_FORMATS = [["pdf", "PDF"], ["pdf_print", "Druck-PDF"], ["booklet", "Booklet"], ["cover", "Umschlag"], ["docx", "DOCX"], ["epub", "EPUB"]];
const RUN_FILES = {proof:"proof.yml", preview:"preview.yml", manuscript:"manuscript.yml", checkout:"checkout.yml"};
const RUN_STATE = r => r.status !== "completed" ? ["läuft", "⏳"] : r.conclusion === "success" ? ["fertig", "✓"] : r.conclusion === "cancelled" ? ["abgebrochen", "⏹"] : r.conclusion === "skipped" ? ["übersprungen", "–"] : ["fehlgeschlagen", "✗"];
const runsActive = rs => rs.some(r => r.status !== "completed");
function runErr(e){
  const c = e && e.code;
  if (c === "http_404") return "In diesem Buch fehlt die Action oder der Zweig. Zuerst GhostWriter aktualisieren (Actions → GhostWriter aktualisieren).";
  if (c === "http_403") return "Der Token darf keine Läufe starten. Lege ihn mit dem Recht „Actions“ (Lesen und Schreiben) neu an.";
  if (c === "http_422") return "GitHub hat den Start nicht angenommen: " + String((e && e.message) || "").slice(0, 200);
  return errText(e);
}
function runFormats(prefix, def){ return RUN_FORMATS.map(f => `<label style="margin-right:10px;font-size:13px"><input type="checkbox" name="${prefix}-fmt" value="${f[0]}" ${def.includes(f[0]) ? "checked" : ""}> ${f[1]}</label>`).join(""); }
async function runsView(){
  if (!RUN.back || S.view !== "runs") RUN.back = {view:S.view || "connect", arg:S.view === "section" ? S.sec && S.sec.id : S.chap};
  S.view = "runs"; crumbs(); busy("Läufe werden gelesen …");
  let runs = [], rels = [], err = "";
  if (S.owner){ try { runs = await runsFetch(); } catch (e) { err = runErr(e); } try { rels = await GW_PORTS.git.listReleases(); if (runsScope() === "book") rels = rels.filter(runRelOfBook); } catch (e) {} }
  const book = S.book, lib = runsScope() === "lib", open = k => RUN.focus === k ? "open" : "";
  const none = !S.owner ? '<p class="dim">Zuerst ein Repository öffnen.</p>' : !book ? '<p class="dim">Zum Starten zuerst ein Buch öffnen (der Lauf gilt für den Stand dieses Buchs).</p>' : "";
  const forms = !S.owner || !book ? none : lib ? '<p class="dim">Gestartet wird im jeweiligen Buch: Buch öffnen, dann den Drucker oben rechts.</p>' : `
    <details ${open("proof")}><summary><b>Probedruck</b> <span class="dim">· PDF zum Prüfen des Satzes, nichts wird veröffentlicht</span></summary><form data-run="proof" style="margin:8px 0">${runFormats("proof", ["pdf"])}
      <div style="margin:6px 0"><input class="in" name="chapters" placeholder="Kapitel, z. B. 1-4 oder 1,3 (leer = alle)" style="max-width:340px"></div><button class="btn pri" data-run-start="proof">Probedruck starten</button></form></details>
    <details ${open("preview")}><summary><b>Vorabfassung</b> <span class="dim">· legt einen Tag und ein Pre-Release an</span></summary><form data-run="preview" style="margin:8px 0">${runFormats("preview", [])}
      <div style="margin:6px 0"><input class="in" name="chapters" placeholder="Kapitel, z. B. 1-4 oder 1,3 (leer = alle)" style="max-width:340px"></div><div class="dim" style="font-size:12px;margin-bottom:6px">Ohne Auswahl gelten die Formate aus den Einstellungen des Buchs.</div>
      <button class="btn pri" data-run-start="preview" data-run-confirm="Es entsteht ein Tag <kurztitel>-vorab-N und ein im Repository sichtbares Pre-Release.">Vorabfassung anlegen</button></form></details>
    <details ${open("manuscript")}><summary><b>Manuskript ausgeben</b> <span class="dim">· PDF oder Lesefassung</span></summary><form data-run="manuscript" style="margin:8px 0">
      <select class="in" name="format" style="max-width:260px"><option value="pdf">PDF (ganzes Buch oder ein Kapitel)</option><option value="md">Lesefassung (Kapitel oder Abschnitt, Pflicht)</option></select>
      <div style="margin:6px 0"><input class="in" name="chapter" placeholder="Kapitel (5) oder Abschnitt (5.1); leer = ganzes Buch" style="max-width:340px"></div><button class="btn pri" data-run-start="manuscript">Manuskript ausgeben</button></form></details>
    <details ${open("checkout")}><summary><b>Auschecken zum Gegenlesen</b> <span class="dim">· sperrt den Bereich und baut DOCX und PDF</span></summary><form data-run="checkout" style="margin:8px 0">
      <div style="margin:6px 0"><input class="in" name="chapters" placeholder="Kapitel, z. B. 3-5 oder 1,3" style="max-width:340px"> <label style="font-size:13px"><input type="checkbox" name="book"> ganzes Buch</label></div>
      <div style="margin:6px 0"><input class="in" name="reader" placeholder="Gegenleser (GitHub-Login oder Name) – Pflicht" style="max-width:340px"> <input class="in" name="until" placeholder="Frist JJJJ-MM-TT (optional)" style="max-width:200px"></div>
      <label style="font-size:13px"><input type="checkbox" name="dry_run"> Probelauf (nichts sperren, nichts committen)</label>
      <div style="margin-top:6px"><button class="btn pri" data-run-start="checkout" data-run-confirm="Der Bereich wird gesperrt und es werden Dateien im Buch abgelegt.">Auschecken</button></div></form></details>`;
  const rows = runs.length ? `<table class="kv">${runs.map(r => { const s = RUN_STATE(r); return `<tr><td>${s[1]} ${s[0]}</td><td>${esc(r.name)}<div class="dim">${esc(lib && runBookOf(r) ? (runBookOf(r).title_short || runBookOf(r).title) : (r.branch || ""))}${lib && runBookOf(r) ? " · " + esc(r.branch || "") : ""} · ${esc(fmtTime(Date.parse(r.created)))}</div></td><td><a href="${esc(r.url)}" target="_blank" rel="noopener">Öffnen</a></td></tr>`; }).join("")}</table><p class="dim" style="font-size:12px">Ergebnisse (PDF, DOCX …) stehen auf der Laufseite unter „Artifacts“ und bleiben 14 Tage.</p>` : `<p class="dim">${err ? esc(err) : "Noch keine Läufe."}</p>`;
  const rel = rels.length ? `<table class="kv">${rels.map(r => `<tr><td>${esc(r.name)}${r.pre ? ' <span class="dim">(Vorabfassung)</span>' : ""}<div class="dim">${esc(fmtTime(Date.parse(r.date)))}</div></td><td>${r.assets.length ? r.assets.map(a => `<a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.name)}</a> <span class="dim">${fmtBytes(a.size)}</span>`).join("<br>") : `<a href="${esc(r.url)}" target="_blank" rel="noopener">Öffnen</a>`}</td></tr>`).join("")}</table>` : '<p class="dim">Noch keine Auflagen oder Vorabfassungen.</p>';
  $("app").innerHTML = `<div class="one"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><b style="font-size:20px">Ausgabe und Läufe${lib ? "" : '<span class="dim" style="font-size:14px;font-weight:400"> · ' + esc(book.title_short || book.title || "") + "</span>"}</b><span>${book ? `<button class="btn" data-act="runs-scope">${lib ? "Nur dieses Buch" : "Alle Läufe der Bibliothek"}</button> ` : ""}<button class="btn" data-act="runs-back">Zurück</button></span></div>${msgBox()}
    <section class="card"><b>Starten</b><p class="dim" style="margin:6px 0">Startet eine Action im Buch-Repository. Der Token braucht dafür zusätzlich das Recht „Actions“ (Lesen und Schreiben). Ohne dieses Recht kannst du die Läufe nur ansehen.${RUN.msg ? `<br><b>${esc(RUN.msg)}</b>` : ""}</p>${forms}</section>
    <section class="card"><div style="display:flex;justify-content:space-between"><b>${lib ? "Letzte Läufe der Bibliothek" : "Letzte Läufe dieses Buchs"}</b><button class="btn" data-act="runs-refresh" title="Neu laden"><i class="ti ti-refresh"></i></button></div>${rows}</section>
    <section class="card"><b>${lib ? "Auflagen und Vorabfassungen der Bibliothek" : "Auflagen und Vorabfassungen dieses Buchs"}</b>${rel}<p class="dim" style="font-size:12px">Eine neue <b>Auflage</b> (Auflagen-Änderungspaket mit Freigaben) legst du in dieser Fassung noch im Chat mit GhostWriter an; danach baut die Action „Auflage veröffentlichen“ und das Ergebnis erscheint hier.</p></section></div>`;
  window.scrollTo(0, 0);
  runsWatch(runs);
}
function runsWatch(runs){
  clearTimeout(RUN.timer);
  if (S.view !== "runs" || Date.now() > RUN.until || !(runsActive(runs) || Object.keys(RUN.pending).length)) return;
  RUN.timer = setTimeout(async () => {
    if (S.view !== "runs" || !S.owner) return;
    try {
      const rs = await runsFetch();
      Object.keys(RUN.pending).forEach(k => { if (rs.some(r => (r.name || "").length && Date.parse(r.created) >= RUN.pending[k] - 15000 && (r.event === "workflow_dispatch"))) delete RUN.pending[k]; });
      RUN.msg = Object.keys(RUN.pending).length ? "Gestartet. Warte auf den Lauf …" : (runsActive(rs) ? "Der Lauf läuft." : "Der Lauf ist beendet.");
      await runsView();
    } catch (e) {}
  }, 6000);
}
async function runDispatch(kind, form, confirmed){
  const f = {}; new FormData(form).forEach((v, k) => { f[k] = f[k] === undefined ? v : f[k] + "," + v; });
  const fmts = [...form.querySelectorAll('input[name$="-fmt"]:checked')].map(x => x.value);
  let inputs = {};
  if (kind === "proof") inputs = {formats:fmts.join(",") || "pdf", chapters:(f.chapters || "").trim()};
  if (kind === "preview") inputs = {formats:fmts.join(","), chapters:(f.chapters || "").trim()};
  if (kind === "manuscript"){ inputs = {format:f.format || "pdf", chapter:(f.chapter || "").trim()}; if (inputs.format === "md" && !inputs.chapter) return "Für die Lesefassung bitte ein Kapitel oder einen Abschnitt angeben."; }
  if (kind === "checkout"){
    inputs = {chapters:(f.chapters || "").trim(), book:f.book ? "true" : "false", reader:(f.reader || "").trim(), until:(f.until || "").trim(), dry_run:f.dry_run ? "true" : "false"};
    if (!inputs.reader) return "Bitte den Gegenleser angeben.";
    if (!f.book && !inputs.chapters) return "Bitte Kapitel angeben oder „ganzes Buch“ wählen.";
    if (inputs.until && !/^\d{4}-\d{2}-\d{2}$/.test(inputs.until)) return "Die Frist bitte als JJJJ-MM-TT angeben.";
  }
  if (/[^0-9,.\- ]/.test(inputs.chapters || "") || /[^0-9.]/.test(inputs.chapter || "")) return "Kapitel bitte nur als Zahlen angeben, z. B. 1-4 oder 1,3.";
  await GW_PORTS.git.dispatch(RUN_FILES[kind], S.book.branch, inputs);
  RUN.pending[kind] = Date.now(); RUN.until = Date.now() + 10 * 60 * 1000;
  return "";
}
GW_PORTS.views = Object.assign(GW_PORTS.views || {}, {runs:runsView});
GW_PORTS.actions = {
  "edition.create.open": () => { RUN.focus = ""; return runsView(); }, "edition.proof": () => { RUN.focus = "proof"; return runsView(); }, "edition.preview": () => { RUN.focus = "preview"; return runsView(); },
  "manuscript.export": () => { RUN.focus = "manuscript"; return runsView(); }, "checkout.start": () => { RUN.focus = "checkout"; return runsView(); }
};
document.addEventListener("click", async ev => {
  const g = ev.target.closest && ev.target.closest("#runsbtn"); if (g){ ev.preventDefault(); RUN.focus = ""; RUN.msg = ""; RUN.scope = ""; return runsView(); }
  const a = ev.target.closest && ev.target.closest("[data-act]");
  if (a && a.dataset.act === "runs-back"){ ev.preventDefault(); clearTimeout(RUN.timer); const k = RUN.back || {view:"connect"}; RUN.back = null; return show(k.view, k.arg); }
  if (a && a.dataset.act === "runs-scope"){ ev.preventDefault(); RUN.scope = runsScope() === "lib" ? "book" : "lib"; return runsView(); }
  if (a && a.dataset.act === "runs-refresh"){ ev.preventDefault(); RUN.until = Date.now() + 2 * 60 * 1000; return runsView(); }
  const b = ev.target.closest && ev.target.closest("[data-run-start]"); if (!b) return;
  ev.preventDefault();
  const kind = b.dataset.runStart, form = b.closest("form"), hint = b.dataset.runConfirm;
  if (hint && b.dataset.armed !== "1"){   // zweiter Klick ist die ausdrückliche Bestätigung
    b.dataset.armed = "1"; b.dataset.label = b.textContent; b.textContent = "Ja, jetzt starten";
    const n = document.createElement("div"); n.className = "dim"; n.style.cssText = "font-size:12px;margin-top:4px"; n.textContent = hint; n.setAttribute("data-run-hint", ""); b.parentNode.insertBefore(n, b.nextSibling); return;
  }
  b.disabled = true; b.textContent = "Wird gestartet …";
  try { const problem = await runDispatch(kind, form); if (problem){ b.disabled = false; b.textContent = b.dataset.label || "Starten"; b.dataset.armed = ""; const h = form.querySelector("[data-run-hint]"); if (h) h.remove(); RUN.msg = ""; alert(problem); return; }
    RUN.focus = ""; RUN.msg = "Gestartet. Warte auf den Lauf …"; await runsView();
  } catch (e) { S.msg = {kind:"err", html:esc(runErr(e))}; b.disabled = false; b.textContent = b.dataset.label || "Starten"; b.dataset.armed = ""; await runsView(); }
});

/* ---------- Seite „Daten“: „Branches aufräumen“ als Knopf (Action cleanup.yml) ----------
   Statt des Links zur Action zeigt die Seite „Daten“ hier Knöpfe, wenn der Token es darf (Schreibrecht am Repository, Recht „Actions“, Action im Buch vorhanden).
   „Nur anzeigen“ löscht nichts; „Branches aufräumen“ fragt vorher mit einem zweiten Klick. Gelöscht werden nur erledigte Arbeits-Branches (Änderungspaket übernommen oder
   vollständig im Buch enthalten); Branches mit offenem Änderungspaket oder eigenen Commits bleiben (Prüfung in der Action, nichts geht verloren). */
function cleanWhy(push, state, hasToken){
  if (!hasToken) return "Nicht angemeldet.";
  if (!push) return "Dein Token hat kein Schreibrecht an diesem Repository.";
  if (state === "forbidden") return "Dem Token fehlt das Recht „Actions“ (Lesen und Schreiben).";
  if (state === "missing") return "In diesem Repository fehlt die Action „Branches aufräumen“. Zuerst GhostWriter aktualisieren.";
  return "";
}
async function cleanPatch(root){
  const a = root.querySelector && root.querySelector('a[href$="/actions/workflows/cleanup.yml"]'); if (!a) return;
  const href = a.getAttribute("href"), box = document.createElement("span"); box.className = "cleanbox"; box.innerHTML = '<span class="dim">Rechte werden geprüft …</span>'; a.replaceWith(box);
  let info = null, state = "unknown";
  try { info = await GW_PORTS.git.repoInfo(S.owner, S.repo); state = await GW_PORTS.git.workflowState("cleanup.yml"); } catch (e) {}
  const why = cleanWhy(!!(info && info.permissions && info.permissions.push), state, !!token());
  box.dataset.ref = (info && info.default_branch) || "main"; box.dataset.href = href;
  box.innerHTML = why ? `<a href="${esc(href)}" target="_blank" rel="noopener">Branches aufräumen</a> <span class="dim" title="${esc(why)}">(${esc(why)})</span>`
    : `Branches aufräumen: <button class="btn" data-clean="dry">Nur anzeigen</button> <button class="btn" data-clean="run">Aufräumen</button>`;
}
{ const prev = GW_PORTS.afterRender; GW_PORTS.afterRender = (name, root) => { if (prev) prev(name, root); if (name === "daten") cleanPatch(root); }; }
async function cleanStart(box, dry){
  box.innerHTML = '<span class="dim">Wird gestartet …</span>';
  try { await GW_PORTS.git.dispatch("cleanup.yml", box.dataset.ref || "main", {dry_run:dry ? "true" : "false"}); }
  catch (e) { box.innerHTML = `<span class="note err">${esc(runErr(e))}</span> <a href="${esc(box.dataset.href || "#")}" target="_blank" rel="noopener">Auf GitHub öffnen</a>`; return; }
  box.innerHTML = `<b>${dry ? "Anzeige" : "Aufräumen"} gestartet.</b> <span id="cleanrun" class="dim">Lauf wird gesucht …</span>`;
  setTimeout(async () => {
    try { const r = (await GW_PORTS.git.listRuns("cleanup.yml", {perPage:1}))[0]; const el = $("cleanrun"); if (r && el) el.innerHTML = `<a href="${esc(r.url)}" target="_blank" rel="noopener">Lauf öffnen</a>`; } catch (e) {}
  }, 4000);
  [10000, 30000, 60000].forEach(ms => setTimeout(() => { if (S.view === "data") show("data"); }, ms));   // Zahl der Branches und letzte Läufe nachladen (nur solange die Seite offen ist)
}
document.addEventListener("click", ev => {
  const b = ev.target.closest && ev.target.closest("[data-clean]"); if (!b) return;
  ev.preventDefault(); const box = b.closest(".cleanbox");
  if (b.dataset.clean === "dry") return cleanStart(box, true);
  if (b.dataset.armed !== "1"){
    b.dataset.armed = "1"; b.textContent = "Ja, jetzt aufräumen";
    const n = document.createElement("div"); n.className = "dim"; n.style.cssText = "font-size:12px;margin-top:4px"; n.textContent = "Gelöscht werden nur erledigte Arbeits-Branches (Änderungspaket übernommen oder vollständig im Buch enthalten). Branches mit offenem Änderungspaket oder eigenen Commits bleiben.";
    box.appendChild(n); return;
  }
  cleanStart(box, false);
});
