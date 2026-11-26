/* Freigaben (START.md, „Freigaben“) */
const EMPTY_MS = ["", "Noch nicht begonnen.", "Offen."];
async function login(){ if (S.login) return S.login; try { S.login = (await GW_PORTS.git.me()) || "chat"; } catch (e) { S.login = "chat"; } return S.login; }
async function sha256full(t){ const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(t.trim())); return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join(""); }
function nowIso(){ const d = new Date(), o = -d.getTimezoneOffset(), p = n => String(Math.abs(n)).padStart(2, "0"); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}${o >= 0 ? "+" : "-"}${p(Math.trunc(o / 60))}:${p(o % 60)}`; }
async function approvalState(data){
  const kind = data.kind, revoke = !!data.revoke, checks = [], add = (s, t) => checks.push({CHECK_STATE:s, CHECK_TEXT:t});
  const waived = ((S.cfg.workflow || {}).require_section_writing_approval === false);
  let v = {};
  if (kind === "chapter"){
    const ci = chIndex(data.chapter_id), c = chapters()[ci];
    const fl = await readAll(c.sections.map(s => s.path), S.readRef), open = c.sections.filter(s => front(fl[s.path] || "").status !== "approved").length;
    v = {target:c.id, label:`Kapitel ${ci + 1} „${c.title}“`, c, ci};
    if (revoke){ v.title = "Kapitel wieder öffnen"; v.button = "Wieder öffnen"; if (c.status !== "approved") add("block", "Das Kapitel ist nicht abgeschlossen."); v.effect = "Das Kapitel geht zurück auf „in Arbeit“. Die Abschlüsse der Abschnitte bleiben bestehen."; }
    else { v.title = "Kapitel abschließen"; v.button = "Abschließen";
      if (c.status === "approved") add("block", "Das Kapitel ist bereits abgeschlossen.");
      if (open) add("block", `${open} von ${c.sections.length} Abschnitten sind noch nicht abgeschlossen.`); else add("ok", `Alle ${c.sections.length} Abschnitte sind abgeschlossen.`);
      if (!["ready_for_approval", "approved"].includes(c.status)) add("block", `Das Kapitel steht auf „${ST(c.status)}“ statt „bereit zum Abschluss“. Erst zusammenführen und durchsehen.`);
      v.effect = "Das Kapitel wird abgeschlossen. Du bestätigst das zusammengeführte Kapitel in diesem Stand."; }
    return {v, checks, kind, revoke};
  }
  const x = allSecs().find(q => q.s.id === data.section_id), ci = chapters().indexOf(x.c), si = x.c.sections.indexOf(x.s);
  const f = await getFile(x.s.path, S.readRef, true), h = front(f.text), ap = Object.assign({writing:false, section:false}, h.approvals || {}), ms = msOf(f.text);
  if (waived) ap.writing = true;
  v = {target:x.s.id, label:`Abschnitt ${ci + 1}.${si + 1} „${x.s.title}“`, x, f, h, ms};
  const marks = (ms.match(MARKER_RE) || []).length;
  if (kind === "writing" && revoke){
    v.title = v.button = "Schreiben sperren";
    if (waived) add("block", "Bei der Stufe „Zügig“ ist keine Schreibfreigabe nötig.");
    if (!ap.writing) add("block", "Schreiben ist nicht erlaubt.");
    if (ap.section) add("block", "Der Abschnitt ist abgeschlossen. Zuerst den Abschnitt wieder öffnen.");
    v.effect = "Schreiben wird gesperrt. Das Manuskript bleibt, wie es ist; weitergeschrieben werden kann erst nach einer neuen Freigabe.";
  } else if (kind === "writing"){
    v.title = v.button = "Schreiben erlauben";
    if (waived) add("block", "Bei der Stufe „Zügig“ ist keine Schreibfreigabe nötig.");
    if (ap.writing && !waived) add("block", "Schreiben ist bereits erlaubt.");
    add(part(f.text, "Ziel des Abschnitts") ? "ok" : "warn", part(f.text, "Ziel des Abschnitts") ? "Ziel des Abschnitts ist angegeben." : "Ziel des Abschnitts fehlt noch.");
    add(part(f.text, "Kurzbeschreibung") ? "ok" : "warn", part(f.text, "Kurzbeschreibung") ? "Kurzbeschreibung ist angegeben." : "Kurzbeschreibung fehlt noch.");
    v.effect = "Schreiben wird erlaubt; danach darf das Manuskript geschrieben werden." + (["planned", "research", "brainstorming", "ready_to_write"].includes(h.status) ? " Der Abschnitt geht auf „Schreiben“." : "");
  } else if (revoke){
    v.title = "Abschnitt wieder öffnen"; v.button = "Wieder öffnen";
    if (!ap.section) add("block", "Der Abschnitt ist nicht abgeschlossen.");
    if (x.c.status === "approved") add("warn", `Damit wird auch Kapitel ${ci + 1} wieder geöffnet (zurück auf „in Arbeit“).`);
    add("warn", "Schreiben wird dabei gesperrt; zum Weiterschreiben danach „Schreiben erlauben“.");
    v.effect = "Der Abschnitt wird wieder geöffnet und geht auf „Überarbeitung“.";
  } else {
    v.title = "Abschnitt abschließen"; v.button = "Abschließen";
    v.drift = ap.section ? await sectionDrift(x.s.id, ms, x.s.path) : null;   // #563: Text nach dem Abschließen geändert
    if (v.drift){
      v.title = "Geänderten Text neu abschließen";
      add("warn", "Der Text weicht von der letzten Freigabe ab.");
      v.drift.lines.forEach(t => add("warn", t));
    } else if (ap.section) add("block", "Der Abschnitt ist bereits abgeschlossen.");
    if (!ap.writing) add("block", "Schreiben ist für diesen Abschnitt nicht erlaubt.");
    if (EMPTY_MS.includes(ms.trim())) add("block", "Es gibt noch kein Manuskript."); else add("ok", `Manuskript: ${fmtNum(words(ms))} Wörter.`);
    add(marks ? "warn" : "ok", marks ? `${marks} offene${marks === 1 ? "r" : ""} Marker – sie bleiben im abgeschlossenen Text.` : "Keine offenen Marker.");
    if (h.fact_check === "requested") add("warn", "Ein Faktencheck ist angefordert – ist er erledigt?");
    v.effect = v.drift ? "Der Abschnitt bleibt abgeschlossen, jetzt mit dem geänderten Text. Die Freigabe wird neu festgehalten."
      : "Der Abschnitt wird abgeschlossen. Du bestätigst den Text so, wie er im Abschnittsformular steht; danach ist er gesperrt und lässt sich nur nach „Wieder öffnen“ ändern.";
  }
  return {v, checks, kind, revoke};
}
async function sectionDrift(id, ms, path){
  const f = await getFile("approvals.yml", S.readRef, true).catch(() => ({text:""}));
  let list = []; try { list = (window.jsyaml.load(f.text || "") || {}).entries || []; } catch (e) { return null; }
  const rec = list.filter(e => e && e.kind === "section" && e.id === id).pop();
  if (!rec || rec.action !== "granted" || !String(rec.note || "").startsWith("content_sha256=")) return null;
  const now = await sha256full(ms);
  if (rec.note === "content_sha256=" + now) return null;
  const lines = []; const commit = String(rec.commit || "");
  if (/^[0-9a-f]{40}$/.test(commit)){
    const old = await getFile(path, commit).then(r => msOf(r.text)).catch(() => null);
    if (old != null) lines.push(`Wörter bei der letzten Freigabe / jetzt: ${fmtNum(words(old))} / ${fmtNum(words(ms))}`);
  }
  return {rec, lines};
}
const ST = s => ({planned:"geplant", in_progress:"in Arbeit", ready_for_approval:"bereit zum Abschluss", approved:"abgeschlossen", writing:"Schreiben", revision:"Überarbeitung", research:"Recherche"}[s] || s);
async function approvalData(data){
  const {v, checks, kind, revoke} = await approvalState(data);
  return Object.assign(base(), {APPROVAL_KIND:kind, APPROVAL_REVOKE:revoke ? "true" : "", APPROVAL_TITLE:v.title, APPROVAL_BUTTON:v.button, APPROVAL_EFFECT:v.effect,
    TARGET_ID:v.target, TARGET_LABEL:v.label, HEAD_SHORT:String(S.head || "").slice(0, 7), CHECKS:checks});
}
async function approve(data){
  busy("Wird festgehalten …");
  try {
    const work = await prepareWork(); await loadBookData(work);
    const {v, checks, kind, revoke} = await approvalState(data);
    if (checks.some(c => c.CHECK_STATE === "block")) throw {message:"Die Freigabe ist nicht möglich: " + checks.filter(c => c.CHECK_STATE === "block").map(c => c.CHECK_TEXT).join(" ")};
    const by = await login(), at = nowIso(), headSha = data.expected_head_sha || S.head;
    const files = {}, orig = {}, entries = [];
    const entry = (k, id, action, note) => entries.push([`  - kind: ${k}`, `    id: ${id}`, `    action: ${action}`, `    at: ${yq(at)}`, `    by: ${by}`, `    commit: ${headSha}`, ...(note ? [`    note: ${yq(note)}`] : [])].join("\n"));
    const gyPath = "ghostwriter.yml";
    const load = async p => { if (!(p in files)){ const t = (await getFile(p, work, true).catch(() => ({text:null}))).text; files[p] = t; orig[p] = t; } return files[p]; };
    let msg = "";
    if (kind === "chapter"){
      const c = v.c, newSt = revoke ? "in_progress" : "approved";
      const st = splitStructure(await load(gyPath)); setLine(st.chs[v.ci].head, "status", newSt, st); files[gyPath] = joinStructure(st);
      const rp = c.path + "/README.md"; const r = await load(rp); if (r != null) files[rp] = r.replace(/(^## Kapitelstatus\n\n)`[^`]*`/m, `$1\`${newSt}\``);
      entry("chapter", c.id, revoke ? "revoked" : "granted");
      msg = `Kapitel ${v.ci + 1} ${revoke ? "wieder geöffnet" : "abgeschlossen"}`;
    } else {
      const p = v.x.s.path; let t = await load(p); const h = front(t);
      if (kind === "writing"){
        t = fmSet(t, "writing", revoke ? "false" : "true");
        if (!revoke && ["planned", "research", "brainstorming", "ready_to_write"].includes(h.status)) t = fmSet(t, "status", "writing");
        entry("writing", v.x.s.id, revoke ? "revoked" : "granted");
        msg = `${v.label}: Schreiben ${revoke ? "gesperrt" : "erlaubt"}`;
      } else if (!revoke){
        t = fmSet(t, "section", "true"); t = fmSet(t, "status", "approved");
        if (staleOf(t)) t = staleSet(t, null);   // erneutes Abschließen entfernt die Veraltet-Marke (#510)
        if (v.drift) entry("section", v.x.s.id, "revoked");   // #563: neu abschließen = revoked + granted in einem Commit
        entry("section", v.x.s.id, "granted", "content_sha256=" + await sha256full(msOf(orig[p])));
        msg = v.drift ? `${v.label}: geänderten Text neu abgeschlossen` : `${v.label} abgeschlossen`;
      } else {
        t = fmSet(t, "section", "false"); t = fmSet(t, "status", "revision"); t = fmSet(t, "writing", "false");
        entry("section", v.x.s.id, "revoked"); entry("writing", v.x.s.id, "revoked");
        if (v.x.c.status === "approved"){
          const ci = chapters().indexOf(v.x.c), st = splitStructure(await load(gyPath)); setLine(st.chs[ci].head, "status", "in_progress", st); files[gyPath] = joinStructure(st);
          const rp = v.x.c.path + "/README.md"; const r = await load(rp); if (r != null) files[rp] = r.replace(/(^## Kapitelstatus\n\n)`[^`]*`/m, "$1`in_progress`");
          entry("chapter", v.x.c.id, "revoked");
        }
        msg = `${v.label} wieder geöffnet`;
      }
      files[p] = t;
      await load(v.x.c.path + "/README.md"); await renumber([v.x.c.id], files, work, orig);
    }
    const ap = await load("approvals.yml");
    files["approvals.yml"] = (ap == null ? "entries:\n" : ap.replace(/\s*$/, "\n").replace(/^entries:\s*\[\]\s*$/m, "entries:")) + entries.join("\n") + "\n";
    const r = await commit(changed(files, orig), msg, {action:"approval.confirm"});
    S.msg = savedMsg(msg + ".", r);
  } catch (e) { S.msg = failMsg(e); }
  back();
}

