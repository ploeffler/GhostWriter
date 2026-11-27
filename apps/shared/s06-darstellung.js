/* ---------- Darstellung ---------- */
function crumbs(){
  const c = [];
  if (S.owner && S.lib) c.push(`<button data-go="library">${esc(S.owner + "/" + S.repo)}</button>`);
  if (S.book) c.push(`›<button data-go="project">${esc(S.book.title_short || S.book.title)}</button>`);
  if (S.book && S.chap != null && S.chap >= 0) c.push(`›<button data-go="chapter">Kapitel ${S.chap + 1}</button>`);
  if (S.sec) c.push(`›<span style="padding:0 6px">${esc(S.secNo)}</span>`);
  $("crumbs").innerHTML = c.join(" ");
}
const msgBox = () => S.msg ? `<div class="note ${S.msg.kind}" role="status">${S.msg.html}${S.msg.kind === "err" && GW_PORTS.report ? GW_PORTS.report.button() : ""}</div>` : "";
function busy(t){ $("app").innerHTML = `<div class="one"><p class="dim"><span class="spin"></span>${esc(t)}</p></div>`; }
/* Fehlende Platzhalter gelten als leer (#685, wie _PACK ab UI 0.72): Die eingebaute Laufzeit lässt unbekannte {{NAME}} stehen.
   Nach dem Rendern aus Text und Attributen entfernen; Ereignisbehandler bleiben, weil nur Knotenwerte geändert werden. */
const RAW = /\{\{[#\/]?[A-Z_]+\}\}/g;
function blankRaw(root){
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = tw.nextNode(); n; n = tw.nextNode()) if (RAW.test(n.nodeValue)) n.nodeValue = n.nodeValue.replace(RAW, "");
  root.querySelectorAll("*").forEach(el => [...el.attributes].forEach(a => { if (RAW.test(a.value)) a.value = a.value.replace(RAW, ""); }));
}
/* Knopf-Inventar (#662): Aktionen, die diese App nicht kann, sind vor dem Klick ausgegraut. Die Liste steht in aktionen.json (Test: tests/test_app_aktionen.py);
   sobald die eingebaute Laufzeit UI 0.80.0 hat, übernimmt GW.capabilities das. */
const NA = /*GW-NA*/{"analysis.apply":"Das geht im Chat.","analysis.open":"Das geht im Chat.","analysis.start":"Das geht im Chat.","anecdote.capture":"Das geht im Chat.","anecdote.plan":"Das geht im Chat.","anecdote.show":"Das geht im Chat.","anecdote.suggest":"Das geht im Chat.","anecdote.use":"Das geht im Chat.","backup.create":"Das geht im Chat.","chapter.research.open":"Das geht im Chat.","chapter.research.start":"Das geht im Chat.","chapter.revision.start":"Das geht im Chat.","chapter.sections.add":"Das geht im Chat.","chapter.texts.update":"Das geht im Chat.","character.talk.apply":"Das geht im Chat.","character.talk.end":"Das geht im Chat.","character.talk.start":"Das geht im Chat.","character.talk.switch":"Das geht im Chat.","character.talk.until":"Das geht im Chat.","checkout.aufbau":"Das geht im Chat.","checkout.end":"Das geht im Chat.","checkout.return":"Das geht im Chat.","checkout.start":"Das geht im Chat.","edition.create":"Das geht im Chat.","edition.create.open":"Das geht im Chat.","edition.preview":"Das geht im Chat.","edition.proof":"Das geht im Chat.","figurenbild.change":"Das geht im Chat.","figurenbild.pick":"Das geht im Chat.","figurenbild.stil.save":"Das geht im Chat.","image.add":"Das geht im Chat.","image.layout":"Das geht im Chat.","image.place":"Das geht im Chat.","image.prompt":"Das geht im Chat.","import.apply":"Das geht im Chat.","import.edit":"Das geht im Chat.","import.outline.apply":"Das geht im Chat.","import.outline.open":"Das geht im Chat.","import.outline.start":"Das geht im Chat.","library.book.create":"Das geht im Chat.","library.book.create.open":"Das geht im Chat.","library.edition.open":"Das geht im Chat.","manuscript.export":"Das geht im Chat.","material.add":"Das geht im Chat.","matter.create":"Das geht im Chat.","matter.glossary.from_series":"Das geht im Chat.","matter.glossary.suggest":"Das geht im Chat.","matter.glossary.to_series":"Das geht im Chat.","matter.glossary.update":"Das geht im Chat.","matter.update":"Das geht im Chat.","project.ai_disclosure.open":"Das geht im Chat.","project.ai_disclosure.update":"Das geht im Chat.","project.analysis.open":"Das geht im Chat.","project.analysis.update":"Das geht im Chat.","project.output.open":"Das geht im Chat.","project.output.update":"Das geht im Chat.","project.providers.open":"Das geht im Chat.","project.providers.update":"Das geht im Chat.","project.rules.open":"Das geht im Chat.","project.rules.update":"Das geht im Chat.","project.settings.open":"Das geht im Chat.","project.settings.update":"Das geht im Chat.","series.create":"Das geht im Chat.","series.create.open":"Das geht im Chat.","series.edit.open":"Das geht im Chat.","series.omnibus.approve":"Das geht im Chat.","series.omnibus.edit.open":"Das geht im Chat.","series.omnibus.publish":"Das geht im Chat.","series.omnibus.revoke":"Das geht im Chat.","series.omnibus.update":"Das geht im Chat.","series.reorder":"Das geht im Chat.","series.update":"Das geht im Chat.","series.volume.add":"Das geht im Chat.","series.volume.remove":"Das geht im Chat.","update.apply":"Das geht im Chat.","view.images":"Das geht im Chat.","view.matter":"Das geht im Chat.","view.series":"Das geht im Chat.","view.timeline":"Das geht im Chat.","wizard.answer":"Das geht im Chat.","wizard.skip":"Das geht im Chat."}/*GW-NA-END*/;
function applyNa(root){
  root.querySelectorAll("[data-a],[data-gw-send]").forEach(b => {
    const a = b.getAttribute("data-a") || b.getAttribute("data-gw-send") || "", why = Object.prototype.hasOwnProperty.call(NA, a) ? NA[a] : "";
    if (!why || b.hasAttribute("data-gw-na") || (GW_PORTS.actions && GW_PORTS.actions[a])) return;
    b.setAttribute("disabled", ""); b.setAttribute("aria-disabled", "true"); b.setAttribute("data-gw-na", why); b.setAttribute("title", why); b.classList.add("gw-na");
  });
}
function gwRender(name, data){ try { window.GW.render(name, data, $("gw"), "de"); blankRaw($("gw")); applyNa($("gw")); if (GW_PORTS.afterRender) GW_PORTS.afterRender(name, $("gw")); } catch (e) { $("gw").innerHTML = `<div class="note err">Ansicht konnte nicht dargestellt werden: ${esc(e.message || e)}</div>`; } }
function widget(name, data, extra){ $("app").innerHTML = `<div class="one">${msgBox()}<div id="gw"></div>${extra || ""}</div>`; gwRender(name, data); patchRun(); crumbs(); window.scrollTo(0, 0); }
/* Abschnittssteuerung an die App anpassen (#462): „Sofort“ läuft hier in der App, nicht im Chat. Ist ein Dienst mit
   Websuche eingestellt, recherchiert die Action „Recherche“: dieser Knopf ist dann aktiv, „Sofort“ (ohne Internet) aus. */
function patchRun(){
  const gw = $("gw"); if (!gw || !gw.querySelector(".gw-card[data-task]")) return;
  gw.querySelectorAll('.gw-opt[data-mode="sofort"] span').forEach(sp => { const t = sp.lastChild; if (t && t.nodeType === 3) t.nodeValue = " · hier in der App"; });
  webProvider().then(w => {
    const card = gw.querySelector('.gw-card[data-task="Recherche"]'); if (!w || !card || !gw.isConnected) return;
    const swap = (b, html, on) => { const n = b.cloneNode(false); n.innerHTML = html; n.dataset.available = on ? "true" : "false"; n.disabled = !on; b.replaceWith(n); return n; };
    const sched = card.querySelector('.gw-opt[data-mode="zeitgesteuert"]'), now = card.querySelector('.gw-opt[data-mode="sofort"]');
    if (sched){ const n = swap(sched, `<i class="ti ti-file-search" style="font-size:16px;color:var(--text-secondary)" aria-hidden="true"></i><span style="font-size:13px"><span style="font-weight:500">Mit Internet</span> · GitHub-Action (${esc(w.name)})</span>`, true);
      n.title = "Recherche mit Websuche über " + w.name + " in der Action „Recherche“";
      n.addEventListener("click", () => runStart({section_id:(S.sec && S.sec.id) || "", task:"research", mode:"web"})); }
    if (now){ const n = swap(now, `<i class="ti ti-bolt" style="font-size:16px;color:var(--text-secondary)" aria-hidden="true"></i><span style="font-size:13px"><span style="font-weight:500">Sofort</span> · hier in der App</span><span class="gw-later">ohne Internet</span>`, false);
      n.title = "Claude hat in der App keine Websuche: Recherche mit Internet über den Knopf darüber."; }
  });
}
function desk(name, data, extra, key){
  if (S.chatKey !== key){ S.chat = []; S.chatKey = key; }
  $("app").innerHTML = GW_PORTS.noChat ? `<div class="one">${msgBox()}<div id="gw"></div>${extra || ""}</div>` : `<div class="desk"><div>${msgBox()}<div id="gw"></div>${extra || ""}</div>${claudePanel()}</div>`;
  gwRender(name, data); patchRun(); crumbs(); renderChat(); window.scrollTo(0, 0);
}
async function show(view, arg){
  S.view = view;
  try {
    if (GW_PORTS.views && GW_PORTS.views[view]) return GW_PORTS.views[view](arg);   // Ansichten, die nur ein Anschluss kennt (eigene Web-App: Einstellungen)
    if (view === "connect"){ crumbs(); return connectView(); }
    if (view === "library"){ S.book = null; S.chap = null; S.sec = null; crumbs(); return widget("buecherregal", libraryData()); }
    if (view === "project"){ S.chap = null; S.sec = null; crumbs(); busy("Projektübersicht wird geladen …"); const d = await projectData(); return desk("projektuebersicht", d, checksCard() + queueCard() + await reviewCard() + await checkinCard(), "project"); }
    if (view === "checkin"){ crumbs(); busy("Rückgabe wird gelesen …"); return widget("rueckgabe", await checkinData(arg)); }
    if (view === "chapter"){ S.chap = arg; S.sec = null; crumbs(); busy("Kapitel wird geladen …"); const d = await chapterData(arg); return desk("kapitelansicht", d, "", "chapter:" + (chapters()[arg] || {}).id); }
    if (view === "queue"){ crumbs(); busy("Warteschlange wird gelesen …"); return widget("warteschlange", await queueData()); }
    if (view === "review"){ crumbs(); busy("Hinweisdurchsicht wird geladen …"); const rd = await reviewData(arg), ri = S.reviewInfo || {}, bar = [];
      if (ri.name === "gering-zu") bar.push(`<button class="btn" data-act="gering" data-f="${esc(arg)}">${ri.gering} geringe Hinweise lassen (nein)</button>`, `<button class="btn" data-act="gering-show" data-f="${esc(arg)}">Geringes einzeln ansehen</button>`);
      if (ri.staged || S.reviewAll) bar.push(`<button class="btn" data-act="all-show" data-f="${esc(arg)}">${S.reviewAll ? "Wieder in Stufen" : "Alle Einträge zeigen"}</button>`);
      return widget("hinweisdurchsicht", rd, bar.length ? `<div class="row" style="margin-top:10px;gap:8px">${bar.join(" ")}</div>` : ""); }
    if (view === "characters"){ S.chap = null; S.sec = null; crumbs(); busy("Figuren werden geladen …"); return widget("figuren", await charListData()); }
    if (view === "data"){ S.book = null; S.chap = null; S.sec = null; crumbs(); busy("Daten werden gesammelt …"); const d = await dataData(); return widget("daten", d); }
    if (view === "section"){
      busy("Abschnitt wird geladen …");
      const {d, x, f} = await sectionData(arg);
      S.sec = x.s; S.secNo = d.SECTION_NUMBER; S.chap = chapters().indexOf(x.c); S.secFile = f;
      return desk("abschnitt-bearbeiten", d, "", "section:" + x.s.id);
    }
    if (view === "merge"){ crumbs(); return widget("aenderungen-uebernehmen", mergeData()); }
    if (view === "report"){ $("app").innerHTML = `<div class="one"><div class="card report"><button class="btn" data-go="back" style="margin-bottom:16px">‹ Zurück</button><p class="dim">${esc(S.report.path)}</p>${mdDoc(S.report.text)}</div></div>`; window.scrollTo(0, 0); return; }
  } catch (e) { S.msg = {kind:"err", html:esc(errText(e))}; $("app").innerHTML = `<div class="one">${msgBox()}</div>`; }
}
function checksCard(){
  if (!S.checks.length) return "";
  const scopeName = sc => (Array.isArray(sc) ? sc : [sc]).map(id => { if (id === "book") return "ganzes Buch"; let r = id; chapters().forEach((c, ci) => { if (c.id === id) r = "Kapitel " + (ci + 1); (c.sections || []).forEach((s, si) => { if (s.id === id) r = `Abschnitt ${ci + 1}.${si + 1}`; }); }); return r; }).join(", ");
  const kn = k => k.startsWith("analysis:") ? "Analyse: " + (ANA[k.slice(9)] || k.slice(9)) : (KIND_LONG[k] || k);
  const fd = e => deDate(String(e.date || "")) + (e.time ? ", " + e.time : "");
  const list = S.checks.map((e, i) => [i, e]).sort((a, b) => rankOf(b[1], b[0]).localeCompare(rankOf(a[1], a[0]))).map(v => v[1]);
  const items = (S.showAll ? list : list.slice(0, 5)).map(e => `<li><div><b>${esc(kn(e.kind))}</b> <span class="w">· ${esc(scopeName(e.scope || []))} · ${esc(fd(e))}</span></div><span class="res ${esc(e.result)}">${esc(RES[e.result] || e.result)}</span>${e.note ? `<div class="nt">${esc(e.note)}</div>` : ""}${e.report ? `<div class="nt"><button class="link" data-report="${esc(e.report)}">Bericht öffnen</button></div>` : ""}</li>`).join("");
  return `<div class="card" style="margin-top:16px"><b>Prüfberichte</b><ul class="chk" style="margin-top:6px">${items}</ul>${list.length > 5 ? `<button class="link" data-act="allchecks" style="margin-top:6px">${S.showAll ? "Weniger anzeigen" : "Alle " + list.length + " Prüfungen"}</button>` : ""}</div>`;
}
function mdDoc(t){
  const L = esc(t.replace(/^---\n[\s\S]*?\n---\n/, "")).split("\n"), out = []; let list = null;
  const inl = x => x.replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<i>$2</i>");
  for (const l of L){
    const li = /^\s*(?:[-*]|\d+[.)])\s+(.*)/.exec(l);
    if (li){ if (!list){ list = /^\s*\d/.test(l) ? "ol" : "ul"; out.push(`<${list}>`); } out.push(`<li>${inl(li[1])}</li>`); continue; }
    if (list){ out.push(`</${list}>`); list = null; }
    const h = /^(#{1,4})\s+(.*)/.exec(l);
    if (h) out.push(`<h${h[1].length}>${inl(h[2])}</h${h[1].length}>`);
    else if (/^&gt;\s?/.test(l)) out.push(`<blockquote>${inl(l.replace(/^&gt;\s?/, ""))}</blockquote>`);
    else if (/^\s*\|/.test(l)) out.push(`<p><code>${l}</code></p>`);
    else if (l.trim() && !/^-{3,}$/.test(l.trim())) out.push(`<p>${inl(l)}</p>`);
  }
  if (list) out.push(`</${list}>`);
  return out.join("");
}

