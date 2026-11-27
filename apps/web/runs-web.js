/* ---------- Ausgabe und Läufe: Actions starten und Ergebnisse holen (#662) ----------
   Probedruck, Vorabfassung, Manuskript ausgeben und Auschecken zum Gegenlesen starten die Actions des Buch-Repositorys per workflow_dispatch (Vertrag: templates/ui/BEFUELLUNG.md,
   Aktionstabelle). Die App zeigt die letzten Läufe mit Stand und Link (Ergebnisse stehen auf der Laufseite unter „Artifacts“, 14 Tage) und die letzten Releases mit Dateien.
   Der Token braucht dafür zusätzlich „Actions“: Lesen und Schreiben. Was Geld oder sichtbare Spuren kostet (Vorabfassung: Tag und Pre-Release; Auschecken sperrt einen Bereich),
   fragt vorher mit einem zweiten Klick nach; nie wird ohne Klick gestartet. Es gibt keinen Abruf im Takt: nur solange ein gestarteter Lauf läuft und die Ansicht offen ist. */
const RUN = {back:null, timer:0, until:0, focus:"", pending:{}, msg:""};
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
  if (S.owner){ try { runs = await GW_PORTS.git.listRuns(null, {perPage:15}); } catch (e) { err = runErr(e); } try { rels = await GW_PORTS.git.listReleases(); } catch (e) {} }
  const book = S.book, open = k => RUN.focus === k ? "open" : "";
  const none = !S.owner ? '<p class="dim">Zuerst ein Repository öffnen.</p>' : !book ? '<p class="dim">Zum Starten zuerst ein Buch öffnen (der Lauf gilt für den Stand dieses Buchs).</p>' : "";
  const forms = !S.owner || !book ? none : `
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
  const rows = runs.length ? `<table class="kv">${runs.map(r => { const s = RUN_STATE(r); return `<tr><td>${s[1]} ${s[0]}</td><td>${esc(r.name)}<div class="dim">${esc(r.branch || "")} · ${esc(fmtTime(Date.parse(r.created)))}</div></td><td><a href="${esc(r.url)}" target="_blank" rel="noopener">Öffnen</a></td></tr>`; }).join("")}</table><p class="dim" style="font-size:12px">Ergebnisse (PDF, DOCX …) stehen auf der Laufseite unter „Artifacts“ und bleiben 14 Tage.</p>` : `<p class="dim">${err ? esc(err) : "Noch keine Läufe."}</p>`;
  const rel = rels.length ? `<table class="kv">${rels.map(r => `<tr><td>${esc(r.name)}${r.pre ? ' <span class="dim">(Vorabfassung)</span>' : ""}<div class="dim">${esc(fmtTime(Date.parse(r.date)))}</div></td><td>${r.assets.length ? r.assets.map(a => `<a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.name)}</a> <span class="dim">${fmtBytes(a.size)}</span>`).join("<br>") : `<a href="${esc(r.url)}" target="_blank" rel="noopener">Öffnen</a>`}</td></tr>`).join("")}</table>` : '<p class="dim">Noch keine Auflagen oder Vorabfassungen.</p>';
  $("app").innerHTML = `<div class="one"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><b style="font-size:20px">Ausgabe und Läufe</b><button class="btn" data-act="runs-back">Zurück</button></div>${msgBox()}
    <section class="card"><b>Starten</b><p class="dim" style="margin:6px 0">Startet eine Action im Buch-Repository. Der Token braucht dafür zusätzlich das Recht „Actions“ (Lesen und Schreiben). Ohne dieses Recht kannst du die Läufe nur ansehen.${RUN.msg ? `<br><b>${esc(RUN.msg)}</b>` : ""}</p>${forms}</section>
    <section class="card"><div style="display:flex;justify-content:space-between"><b>Letzte Läufe</b><button class="btn" data-act="runs-refresh" title="Neu laden"><i class="ti ti-refresh"></i></button></div>${rows}</section>
    <section class="card"><b>Auflagen und Vorabfassungen</b>${rel}<p class="dim" style="font-size:12px">Eine neue <b>Auflage</b> (Auflagen-Änderungspaket mit Freigaben) legst du in dieser Fassung noch im Chat mit GhostWriter an; danach baut die Action „Auflage veröffentlichen“ und das Ergebnis erscheint hier.</p></section></div>`;
  window.scrollTo(0, 0);
  runsWatch(runs);
}
function runsWatch(runs){
  clearTimeout(RUN.timer);
  if (S.view !== "runs" || Date.now() > RUN.until || !(runsActive(runs) || Object.keys(RUN.pending).length)) return;
  RUN.timer = setTimeout(async () => {
    if (S.view !== "runs" || !S.owner) return;
    try {
      const rs = await GW_PORTS.git.listRuns(null, {perPage:15});
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
  const g = ev.target.closest && ev.target.closest("#runsbtn"); if (g){ ev.preventDefault(); RUN.focus = ""; RUN.msg = ""; return runsView(); }
  const a = ev.target.closest && ev.target.closest("[data-act]");
  if (a && a.dataset.act === "runs-back"){ ev.preventDefault(); clearTimeout(RUN.timer); const k = RUN.back || {view:"connect"}; RUN.back = null; return show(k.view, k.arg); }
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
