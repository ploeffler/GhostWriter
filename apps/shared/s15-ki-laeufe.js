/* KI-Lauf „Sofort“ (Recherche, KI-Entwurf) über Claude in der App */
async function runStart(d){
  if (d.task === "research" && (d.mode === "web" || (d.mode === "immediate" && !d.offline))){
    const w = await webProvider();
    if (w){ S.msg = {kind:"info", html:`<b>Recherche mit Internet über ${esc(w.name)}?</b> Eine GitHub-Action sucht im Netz und legt die Recherche mit Quellen ins Änderungspaket. Das dauert meist ein bis zwei Minuten; die Kosten bei ${esc(w.name)} werden erfasst. Übernommen wird erst mit deiner Bestätigung.<div style="margin-top:8px"><button class="btn pri" data-act="webres" data-s="${esc(d.section_id)}"><i class="ti ti-file-search"></i> Recherche starten</button> <button class="btn" data-act="webcancel" data-s="${esc(d.section_id)}">Abbrechen</button></div>`};
      return show("section", d.section_id); }
  }
  if (d.mode !== "immediate"){ S.msg = {kind:"info", html:"„Zeitgesteuert“ ist noch nicht verfügbar. Nimm „Sofort“."}; return show("section", d.section_id); }
  if (!S.sample){ S.msg = {kind:"warn", html:"Claude ist in dieser Ansicht nicht verfügbar."}; return show("section", d.section_id); }
  const x = allSecs().find(v => v.s.id === d.section_id), f = await getFile(x.s.path, S.readRef, true), h = front(f.text), ap = h.approvals || {};
  const waived = ((S.cfg.workflow || {}).require_section_writing_approval === false);
  if (d.task === "writing" && !(ap.writing || waived)){ S.msg = {kind:"warn", html:"<b>KI-Entwurf ist für diesen Abschnitt nicht erlaubt.</b> Erlaube zuerst das Schreiben (unten bei „Schreiben und Abschluss“)."}; return show("section", d.section_id); }
  if (d.task === "writing" && ap.section){ S.msg = {kind:"warn", html:"Der Abschnitt ist abgeschlossen. Zum Schreiben zuerst wieder öffnen."}; return show("section", d.section_id); }
  if (S.view !== "section" || !S.sec || S.sec.id !== d.section_id) await show("section", d.section_id);
  else { S.msg = null; await show("section", d.section_id); }
  const runs = await runFiles(x, "research");
  const prompt = d.task === "research"
    ? `Erstelle einen Recherchelauf für diesen Abschnitt. WICHTIG: Du hast in dieser App keinen Internetzugang. Recherchiere aus deinem Wissen, kennzeichne Unsicherheiten ausdrücklich, erfinde keine Quellen, URLs, Zitate oder Zahlen. Nenne nur Quellen, die du sicher kennst, jeweils mit dem Vermerk „bitte prüfen“, und schreibe ausdrücklich, dass keine Internetrecherche stattgefunden hat.
Antworte NUR mit dem Inhalt zwischen den Zeilen <<<RECHERCHE und RECHERCHE>>>, gegliedert in genau diese Überschriften: ## Fragestellung und Suchumfang, ## Rechercheergebnisse, ## Quellen, ## Widersprüche und Unsicherheiten, ## Offene Fragen, ## Relevanz für den Abschnitt. Davor höchstens zwei Sätze Zusammenfassung.`
    : `Schreibe das Manuskript dieses einen Abschnitts (KI-Entwurf). Grundlage: Ziel, Kurzbeschreibung, Buchprofil, Schreibregeln und die Rechercheläufe unten. Erfinde keine Fakten; offene Stellen als Marker wie [QUELLE PRÜFEN: …] oder [PLATZHALTER-ANEKDOTE: …]. Vermeide KI-typische Muster (ankündigende Schlusssätze, Floskeln, Dreierreihen von Adjektiven, erklärende Moral). Nur dieser Abschnitt.
Setze den vollständigen Manuskripttext zwischen die Zeilen <<<MANUSKRIPT und MANUSKRIPT>>>. Danach in zwei, drei Sätzen: wichtigste Annahmen und Stellen, die der Autor prüfen sollte.${runs.length ? "\n\nRECHERCHELÄUFE DES ABSCHNITTS\n" + runs.map(r => r.text.slice(0, 6000)).join("\n\n---\n\n") : "\n\n(Keine Rechercheläufe vorhanden.)"}`;
  S.pendingRun = {task:d.task, section_id:d.section_id};
  chat(prompt, d.task === "research" ? "Recherche · Sofort" : "KI-Entwurf · Sofort");
}
async function runFiles(x, folder){
  const dir = `${x.c.path}/${folder}/${x.s.id}`;
  try { const r = await GW_PORTS.git.listDir(dir, S.readRef);
    const list = r.filter(e => /^run-\d+\.md$/.test(e.name)).sort((a, b) => a.name.localeCompare(b.name));
    const out = []; for (const e of list.slice(-3)) out.push({name:e.name, text:(await getFile(e.path || dir + "/" + e.name, S.readRef)).text});
    out.count = list.length; out.max = Math.max(0, ...list.map(e => +e.name.slice(4, -3)));
    return out;
  } catch (e) { const o = []; o.count = 0; o.max = 0; return o; }
}
/* Recherche mit Internet über den eingestellten Anbieter: Auftrag für die Action „Recherche“ (#462) */
const WEB_PROVIDERS = {anthropic:"Anthropic", openai:"OpenAI", google:"Google Gemini"};
function pickWeb(ap){
  if (!ap) return null;
  const r = ((ap.research || {}).provider || "").trim(), sv = ap.services || {};
  if (r) return WEB_PROVIDERS[r] ? r : null;
  return (ap.available || []).find(p => WEB_PROVIDERS[p] && (sv[p] || {}).access === "api") || null;
}
async function webProvider(){
  const ap = S.cfg.ai_providers || {};
  let id = pickWeb(ap);
  const bookSet = ((ap.research || {}).provider || "").trim() || (ap.available || []).length;
  if (!id && !bookSet){
    if (S.libCfg === undefined){ S.libCfg = null; try { S.libCfg = window.jsyaml.load((await getFile("ghostwriter.yml", "", true)).text) || null; } catch (e) {} }
    id = pickWeb(S.libCfg && S.libCfg.ai_providers);
  }
  return id ? {id, name:WEB_PROVIDERS[id]} : null;
}
async function listDir(dir, ref){
  try { return await GW_PORTS.git.listDir(dir, ref); }
  catch (e) { return []; }
}
async function webResearch(id, confirmLow){
  const x0 = allSecs().find(v => v.s.id === id); if (!x0) return;
  const w = await webProvider(); if (!w) return runStart({section_id:id, task:"research", mode:"immediate", offline:true});
  busy("Rechercheauftrag wird gespeichert …");
  try {
    const work = await prepareWork();
    // Der Auftrag startet die Action in der Fassung des Arbeits-Branchs: weicht sie vom Buch ab (Änderungspaket älter
    // als das letzte Update), das Änderungspaket erst auf den Buchstand bringen.
    const wf = async ref => ((await listDir(".github/workflows", ref)).find(e => e.name === "research.yml") || {}).sha || "";
    const want = await wf(S.book.branch);
    if (!want) throw {message:"In diesem Buch fehlt die Action „Recherche“. Zuerst GhostWriter aktualisieren (Actions → GhostWriter aktualisieren)."};
    if ((await wf(work)) !== want){
      const pr = await openPR(S.book);
      if (pr){ busy("Änderungspaket wird auf den Buchstand gebracht …");
        await GW_PORTS.git.updatePRBranch(pr.number);
        for (let i = 0; i < 12 && (await wf(work)) !== want; i++) await new Promise(r => setTimeout(r, 1500)); }
      if ((await wf(work)) !== want)
        throw {message:"Das Änderungspaket ist älter als das letzte GhostWriter-Update und ließ sich nicht automatisch auf den Buchstand bringen. Auf GitHub im Änderungspaket „Update branch“ klicken oder es zuerst übernehmen, dann die Recherche noch einmal starten."};
    }
    await loadBookData(work);
    const x = allSecs().find(v => v.s.id === id); if (!x) throw {message:"Abschnitt nicht gefunden."};
    const dir = `${x.c.path}/research/${x.s.id}`, jobs = await sectionJobs(x, work);
    // „Trotzdem starten“ (#483): den wartenden Auftrag bestätigen statt einen zweiten anzulegen
    const waiting = confirmLow && jobs.find(j => j.state === "waiting_budget");
    let r, name;
    if (waiting){
      const d = Object.assign({}, waiting.data, {confirm_low_budget:true}); delete d.waiting;
      name = waiting.name;
      r = await commit([{path:`${dir}/${name}.yml`, content:window.jsyaml.dump(d, {lineWidth:-1})}], `Rechercheauftrag für Abschnitt ${x.s.id} trotz knappem KI-Budget bestätigt`, {action:"research.web"});
    } else {
      const list = await listDir(dir, work);
      name = "request-" + String(Math.max(0, ...list.map(e => (/^request-(\d+)\.yml$/.exec(e.name) || [])[1] || 0).map(Number)) + 1).padStart(3, "0");
      const file = `type: research\nsection_id: ${x.s.id}\nrequested_at: "${nowIso()}"\nrequested_by: web-app\nprovider: ${w.id}\n` + (confirmLow ? "confirm_low_budget: true\n" : "");
      r = await commit([{path:`${dir}/${name}.yml`, content:file}], `Rechercheauftrag für Abschnitt ${x.s.id} (mit Internet, ${w.name})`, {action:"research.web"});
    }
    const mine = S.webJobs[id] = S.webJobs[id] || [];
    if (!mine.includes(name)) mine.push(name);
    const ahead = jobs.filter(j => j.name !== name && j.state === "open").length;
    S.msg = {kind:"info", html:`<b>${waiting ? "Bestätigt – die Recherche läuft" : "Recherche ist in der Warteschlange"} (GitHub, ${esc(w.name)}).</b> ${ahead ? `Vor ihr ${ahead === 1 ? "wartet ein Auftrag" : `warten ${ahead} Aufträge`} zu diesem Abschnitt. ` : ""}Das dauert meist ein bis zwei Minuten; du kannst die App solange schließen. Das Ergebnis kommt ins Änderungspaket${r.pr ? ` <a href="${esc(r.pr.url)}" target="_blank" rel="noopener">#${r.pr.number}</a>` : ""}. <button class="btn" data-act="webcheck" data-s="${esc(id)}"><i class="ti ti-refresh"></i> Nachsehen</button>`};
  } catch (e) { S.msg = failMsg(e); }
  show("section", id);
}
/* Aufträge der Hintergrund-Warteschlange an einem Abschnitt (#476/#483), Zustände wie scripts/jobs.py */
function jobState(d){
  if (d.error) return "failed";
  if (d.waiting === "budget" && !d.confirm_low_budget) return "waiting_budget";
  return "open";
}
async function sectionJobs(x, work){
  const dir = `${x.c.path}/research/${x.s.id}`, out = [];
  for (const e of (await listDir(dir, work)).filter(e => /^request-\d+\.yml$/.test(e.name)).sort((a, b) => a.name.localeCompare(b.name))){
    let data = {}; try { data = window.jsyaml.load((await getFile(`${dir}/${e.name}`, work, true)).text) || {}; } catch (err) {}
    if ((data.type || "research") === "research") out.push({name:e.name.replace(/\.yml$/, ""), data, state:jobState(data)});
  }
  return out;
}
async function webCheck(id){
  const x = allSecs().find(v => v.s.id === id); if (!x) return;
  busy("Wird nachgesehen …");
  const work = workOf(S.book), dir = `${x.c.path}/research/${x.s.id}`;
  const jobs = await sectionJobs(x, work), names = jobs.map(j => j.name);
  const mine = S.webJobs[id] || [], gone = mine.filter(n => !names.includes(n));
  const again = `<button class="btn" data-act="webcheck" data-s="${esc(id)}"><i class="ti ti-refresh"></i> Nochmals nachsehen</button>`;
  // Fertig: Aufträge, die verschwunden sind, haben eine Laufdatei mit `request: <name>`
  const done = [];
  if (gone.length || !jobs.length){
    const runs = (await listDir(dir, work)).filter(e => /^run-\d+\.md$/.test(e.name)).sort((a, b) => b.name.localeCompare(a.name));
    for (const e of runs){
      if (gone.length && done.length >= gone.length) break;
      try { const t = (await getFile(`${dir}/${e.name}`, work, true)).text, h = front(t);
        if (gone.includes(h.request) || (!mine.length && h.web_research && !done.length)) done.push({name:e.name, head:h}); } catch (err) {}
      if (!mine.length && done.length) break;
    }
  }
  const lines = [], btns = new Set();
  for (const r of done){
    const h = r.head, cost = h.cost == null ? "Kosten ohne Preisangabe erfasst" : `Kosten etwa ${String(h.cost).replace(".", ",")}`;
    lines.push(`<b>Fertig:</b> ${esc(r.name)} mit ${h.sources || 0} Quellen aus ${h.searches || 0} Suchanfragen (${esc(cost)}). <button class="link" data-report="${esc(dir + "/" + r.name)}">Ansehen</button>`);
  }
  for (const j of jobs){
    if (j.state === "open") lines.push(`<b>Wartet bzw. läuft:</b> ${esc(j.name)}${j.data.confirm_low_budget ? " (trotz knappem Budget bestätigt)" : ""}.`);
    else if (j.state === "waiting_budget"){ lines.push(`<b>Wartet auf deine Bestätigung:</b> ${esc(j.name)} – das KI-Budget ist fast aufgebraucht.`); btns.add(`<button class="btn" data-act="webreslow" data-s="${esc(id)}">Trotzdem starten</button>`); }
    else {
      lines.push(`<b>Fehlgeschlagen:</b> ${esc(j.name)} – ${esc(j.data.error)}`);
      if (/KI-Budget/.test(j.data.error)) btns.add(`<button class="btn" data-act="webreslow" data-s="${esc(id)}">Trotzdem starten</button>`);
      btns.add(`<button class="btn" data-act="offres" data-s="${esc(id)}">Ohne Internet über Claude</button>`);
    }
  }
  const pending = jobs.some(j => j.state === "open"), missing = gone.length > done.length;
  if (done.length){ S.webJobs[id] = mine.filter(n => names.includes(n)); await loadBookData(work); }
  if (!lines.length) lines.push(missing ? "<b>Noch kein Ergebnis.</b>" : "<b>Keine Rechercheaufträge zu diesem Abschnitt.</b>");
  if (done.length) lines.push("Übernehmen kannst du Ergebnisse mit dem Änderungspaket in der Projektübersicht.");
  if (pending || missing) btns.add(again);
  const kind = jobs.some(j => j.state === "failed") ? "err" : done.length && !pending ? "ok" : "info";
  S.msg = {kind, html:lines.map(l => `<div>${l}</div>`).join("") + (btns.size ? `<div style="margin-top:8px">${[...btns].join(" ")}</div>` : "")};
  show("section", id);
}
async function saveRun(i){
  const m = S.chat[i], run = m.run, x0 = allSecs().find(v => v.s.id === run.section_id); if (!x0) return;
  const RES_RE = /<<<RECHERCHE\n?([\s\S]*?)RECHERCHE>>>/, body = run.task === "research" ? (RES_RE.exec(m.content) || [])[1] : (PROPOSAL.exec(m.content) || [])[1];
  if (!body){ S.msg = {kind:"err", html:"Im Ergebnis fehlt der Teil zum Speichern. Bitte den Lauf wiederholen."}; return show("section", run.section_id); }
  busy(run.task === "research" ? "Recherche wird gespeichert …" : "Entwurf wird gespeichert …");
  try {
    const work = await prepareWork(); await loadBookData(work);
    const x = allSecs().find(v => v.s.id === run.section_id); if (!x) throw {message:"Abschnitt nicht gefunden."};
    const folder = run.task === "research" ? "research" : "writing", runs = await runFiles(x, folder), n = String(runs.max + 1).padStart(3, "0"), today = nowIso().slice(0, 10);
    const ci = chapters().indexOf(x.c), si = x.c.sections.indexOf(x.s), num = `${ci + 1}.${si + 1}`;
    const cur = (await getFile(x.s.path, work, true)).text, h = front(cur), files = {}, orig = {[x.s.path]:cur};
    let t = cur;
    if (run.task === "research"){
      files[`${x.c.path}/research/${x.s.id}/run-${n}.md`] = `---\nid: run-${n}\ntype: research\nsection_id: ${x.s.id}\nstatus: completed\ndate: ${today}\nprovider: chat\nmodel: claude\n---\n\n# Recherchelauf ${n}\n\n> Erstellt mit GhostWriter für Claude, ohne Internetrecherche. Angaben und Quellen vor der Verwendung prüfen.\n\n${body.trim()}\n`;
      if (h.status === "planned") t = fmSet(t, "status", "research");
    } else {
      if ((h.approvals || {}).section) throw {message:"Der Abschnitt ist inzwischen abgeschlossen."};
      const old = msOf(cur), had = !EMPTY_MS.includes(old.trim()), newSt = ["writing", "revision"].includes(h.status) && had ? "revision" : "writing";
      t = setBlock(t, "Manuskript", body.trim()); t = fmSet(t, "status", newSt);
      const marks = {}; for (const mm of body.matchAll(MARKER_RE)) marks[mm[1]] = (marks[mm[1]] || 0) + 1;
      files[`${x.c.path}/writing/${x.s.id}/run-${n}.md`] = `---\nid: run-${n}\ntype: writing\nsection_id: ${x.s.id}\nstatus: completed\ndate: ${today}\nprovider: chat\nmodel: claude\nmode: immediate\n---\n\n# Ghostwriting-Lauf ${n}\n\nProtokoll des Laufs. Der geschriebene Text steht im Manuskript der\nAbschnittsdatei, nicht hier (kein zweites Exemplar des Buchtexts).\n\n## Grundlage\n\n- Recherche: ${(await runFiles(x, "research")).map(r => r.name).join(", ") || "keine"}\n- Ziel und Kurzbeschreibung des Abschnitts\n- Schreibregeln und Buchprofil\n\n## Ergebnis\n\n- Wörter: ${words(body)}\n- Neue Marker: ${Object.entries(marks).map(([k, v]) => `${v}× ${k}`).join(", ") || "keine"}\n- Statuswechsel: ${h.status} → ${newSt}\n\n## Hinweise\n\n${m.content.replace(PROPOSAL, "").trim() || "–"}\n`;
    }
    files[x.s.path] = t;
    await renumber([x.c.id], files, work, orig);
    const r = await commit(changed(files, orig), run.task === "research" ? `Recherche für Abschnitt ${num}` : `Entwurf für Abschnitt ${num}`, {action:"run.start"});
    m.saved = true; S.msg = savedMsg(run.task === "research" ? "Recherche gespeichert." : "Entwurf gespeichert.", r);
  } catch (e) { S.msg = failMsg(e); }
  show("section", run.section_id);
}

async function merge(data){
  if (!S.pr || Number(data.pull_request) !== S.pr.number) return;
  busy("Wird übernommen …");
  try {
    await GW_PORTS.git.mergePR(S.pr.number, {expectedHeadSha:data.expected_head_sha});
    S.msg = {kind:"ok", html:`<b>Übernommen.</b> Änderungspaket #${S.pr.number} ist jetzt im Buch.`};
    S.pr = null; await loadBookData(S.book.branch);
  } catch (e) { S.msg = {kind:"err", html:"<b>Nicht übernommen.</b> " + esc(errText(e))}; }
  S.from = null; show("project");
}


