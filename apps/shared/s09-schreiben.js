/* ---------- Schreiben ins Repository (ein Commit je Aufgabe, Arbeits-Branch, Änderungspaket) ---------- */
async function prepareWork(book){
  const b = book || S.book, work = workOf(b);
  if (await openPR(b)) return work;
  const bk = await getFile("ghostwriter.yml", b.branch, true);
  const wk = await getFile("ghostwriter.yml", work, true).catch(() => null);
  if (!wk){ await GW_PORTS.git.createBranch(work, b.branch); return work; }
  if (wk.commit && bk.commit && wk.commit === bk.commit) return work;
  // Arbeits-Branch ist älter als das Buch: erst auf den Buchstand bringen (nur Buch → Arbeits-Branch)
  try {
    await GW_PORTS.git.createPR({head:b.branch, base:work, title:`GhostWriter: Arbeits-Branch auf den Stand von ${b.branch} bringen`, body:"Automatisch vor dem nächsten Speichern: übernimmt den aktuellen Buchstand in den Arbeits-Branch. Das Buch selbst ändert sich dadurch nicht."});
    const p = (await GW_PORTS.git.listPRs({head:b.branch, base:work}))[0];
    if (p) await GW_PORTS.git.mergePR(p.number, {title:`Buchstand von ${b.branch} in den Arbeits-Branch übernommen`});
  } catch (e) { if (!/no commits|nothing to compare|already/i.test((e && e.message) || "")) throw e; }
  return work;
}
async function commit(files, message, opts){
  const b = S.book, work = workOf(b);
  files = files.filter(f => f && typeof f.content === "string");
  if (!files.length) return {nothing:true};
  try { await GW_PORTS.git.pushFiles(work, files, message, opts && opts.action); }
  catch (e) { if (GW_PORTS.outbox && e && (e.code === "offline" || e.code === "server_unavailable")) return localCommit(files, message, opts); throw e; }
  let pr = await openPR(b), note = "";
  if (!pr){ try { await GW_PORTS.git.createPR({head:work, base:b.branch, title:`GhostWriter: Änderungen für ${b.branch}`, body:"Angelegt mit " + GW_PORTS.agent + ". Übernahme ins Buch nur nach ausdrücklicher Bestätigung."}); pr = await openPR(b); } catch (e) { note = errText(e); } }
  if (pr) await prCommits(pr);
  S.pr = pr;
  await loadBookData(work, files);
  return {pr, note};
}
/* Ohne Netz (nur Anschlüsse mit Outbox, #662): erst auf diesem Gerät sichern, später hochladen. Gelesen wird die lokale Fassung sofort. */
async function localCommit(files, message, opts){
  const b = S.book;
  files = files.filter(f => f && typeof f.content === "string");
  if (!files.length) return {nothing:true};
  const seen = {}, base = {}; files.forEach(f => { const o = S.files.get(S.readRef + "|" + f.path); seen[f.path] = (o && o.sha) || null; if (o && o.sha && typeof o.text === "string") base[f.path] = o.text; });   // null: Stand unbekannt, keine Prüfung; base: Ausgangstext für das Zusammenführen
  Object.assign(seen, (opts && opts.seen) || {}); Object.assign(base, (opts && opts.base) || {});                                    // der Stand, auf dem das Formular beruhte, geht vor
  const n = await GW_PORTS.outbox.add({repo:S.owner + "/" + S.repo, book:{branch:b.branch, work_branch:b.work_branch || ""}, files, message, action:opts && opts.action, seen, base});
  applyOverlay(S.readRef, files);
  return {local:true, pending:n};
}
function savedMsg(what, r){
  if (r.nothing) return {kind:"info", html:"Keine Änderungen – nichts gespeichert."};
  if (r.local) return {kind:"warn", html:`<b>${esc(what)}</b> Nur auf diesem Gerät gespeichert, noch nicht hochgeladen. Es wird hochgeladen, sobald GitHub wieder erreichbar ist; oben steht, was wartet.`};
  return r.pr ? {kind:"ok", html:`<b>${esc(what)}</b> Änderungspaket <a href="${esc(r.pr.url)}" target="_blank" rel="noopener">#${r.pr.number}</a> ist offen – übernehmen kannst du es in der Projektübersicht.`}
              : {kind:"warn", html:`<b>${esc(what)}</b> Gespeichert auf dem Arbeits-Branch. Das Änderungspaket konnte nicht angelegt werden: ${esc(r.note)}`};
}
const failMsg = e => ({kind:"err", html:"<b>Nicht gespeichert.</b> " + esc(errText(e)) + (e && (e.code === "server_unavailable" || e.code === "upstream_error") ? " Möglicherweise ist es trotzdem angekommen – lade neu, bevor du es nochmals versuchst." : "")});
async function readAll(paths, ref){ const out = {}; await pool(paths, 8, async p => { try { out[p] = (await getFile(p, ref, true)).text; } catch (e) { out[p] = null; } }); return out; }

/* Text-Bausteine (ghostwriter.yml, Abschnittsdateien, Kapitel-README) */
const yq = s => JSON.stringify(String(s));
function slug(t){ return String(t).toLowerCase().replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss").normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40).replace(/-+$/, "") || "ohne-titel"; }
const pad2 = n => String(n).padStart(2, "0");
const ind = l => l.length - l.trimStart().length;
function splitStructure(text){
  const L = text.split("\n"), si = L.findIndex(l => /^structure:\s*$/.test(l));
  const ci = L.findIndex((l, i) => i > si && /^  chapters:\s*(\[\])?\s*$/.test(l));
  if (si < 0 || ci < 0) throw {message:"Die Gliederung in ghostwriter.yml hat ein unerwartetes Format."};
  const first = L.findIndex((l, i) => i > ci && l.trim() !== ""), I = first > 0 && /^\s*- /.test(L[first]) && ind(L[first]) >= 2 ? ind(L[first]) : 4, K = I + 2;
  let end = ci + 1; while (end < L.length && (L[end].trim() === "" || ind(L[end]) > I || (ind(L[end]) === I && L[end].trimStart().startsWith("- ")))) end++;
  while (end > ci + 1 && L[end - 1].trim() === "") end--;
  const chs = []; L.slice(ci + 1, end).forEach(l => { if (ind(l) === I && l.trimStart().startsWith("- ")) chs.push([l]); else if (chs.length) chs[chs.length - 1].push(l); });
  let J = null;
  const parsed = chs.map(lines => {
    const k = lines.findIndex(l => ind(l) === K && /^\s*sections:/.test(l));
    const head = k < 0 ? lines : lines.slice(0, k), rest = k < 0 ? [] : lines.slice(k + 1);
    const f = rest.find(l => l.trim() !== ""); const j = f && f.trimStart().startsWith("- ") && ind(f) >= K ? ind(f) : null; if (j != null && J == null) J = j;
    let e = 0; if (j != null) while (e < rest.length && (rest[e].trim() === "" || ind(rest[e]) > j || (ind(rest[e]) === j && rest[e].trimStart().startsWith("- ")))) e++;
    const secs = []; rest.slice(0, e).forEach(l => { if (ind(l) === j && l.trimStart().startsWith("- ")) secs.push([l]); else if (secs.length) secs[secs.length - 1].push(l); });
    return {head, secs, tail:rest.slice(e), id:(/- id:\s*"?([^"\s]+)/.exec(lines[0]) || [])[1]};
  });
  const quoted = chs.length ? /- id:\s*"/.test(chs[0][0]) : false;
  return {pre:L.slice(0, ci), chs:parsed, post:L.slice(end), I, K, J:J == null ? K : J, quoted};
}
function joinStructure(st){
  const out = [...st.pre, st.chs.length ? "  chapters:" : "  chapters: []"], sp = n => " ".repeat(n);
  st.chs.forEach(c => { out.push(...c.head); out.push(sp(st.K) + (c.secs.length ? "sections:" : "sections: []")); c.secs.forEach(s => out.push(...s)); out.push(...c.tail); });
  return [...out, ...st.post].join("\n");
}
const setLine = (lines, key, value, st) => { const re = new RegExp("^" + " ".repeat(st.K) + key + ":"); const i = lines.findIndex(l => re.test(l)); if (i >= 0) lines[i] = " ".repeat(st.K) + key + ": " + value; };
const idv = (st, v) => st.quoted ? yq(v) : v;
const secEntry = (st, id, title, path) => [" ".repeat(st.J) + "- id: " + idv(st, id), " ".repeat(st.J + 2) + "title: " + yq(title), " ".repeat(st.J + 2) + "path: " + idv(st, path)];
const chEntry = (st, id, title, path) => [" ".repeat(st.I) + "- id: " + idv(st, id), " ".repeat(st.K) + "title: " + yq(title), " ".repeat(st.K) + "path: " + idv(st, path), " ".repeat(st.K) + "status: planned"];
const idOfBlock = b => (/- id:\s*"?([^"\s]+)/.exec(b[0]) || [])[1];
function fmSet(text, key, value){
  const m = /^---\n([\s\S]*?)\n---\n/.exec(text); if (!m) return text;
  let fm = m[1];
  if (key === "writing" || key === "section") fm = fm.replace(new RegExp("^(\\s+" + key + ":\\s*)(true|false)", "m"), (a, p) => p + value);
  else fm = new RegExp("^" + key + ":", "m").test(fm) ? fm.replace(new RegExp("^(" + key + ":[ \\t]*)([^#\\n]*?)([ \\t]*(#.*)?)$", "m"), (a, p, v, c) => p + value + (c || "")) : fm + `\n${key}: ${value}`;
  return "---\n" + fm + "\n---\n" + text.slice(m[0].length);
}
/* Veraltet-Vermerk (#510, #592): `stale: {since, reason, source}` im Kopf der Abschnittsdatei wie scripts/stale.py */
const isoDay = v => v instanceof Date ? v.toISOString().slice(0, 10) : String(v || "");
function staleOf(t){ const st = front(t || "").stale; return st && typeof st === "object" ? {since:isoDay(st.since), reason:String(st.reason || ""), source:String(st.source || "")} : null; }
const staleHint = st => `Als veraltet markiert seit ${st.since}: ${st.reason}`;
function staleMarks(items){   // items [[Nummer, Text]] -> [Text, Tooltip]
  const marked = items.map(([n, t]) => [n, staleOf(t)]).filter(x => x[1]);
  if (!marked.length) return ["", ""];
  return [marked.length === 1 ? "veraltet" : `${marked.length} veraltet`, marked.slice(0, 5).map(([n, st]) => `${n}: ${staleHint(st)}`).join("; ")];
}
function staleSet(text, entry){   // entry null = entfernen
  const m = /^---\n([\s\S]*?)\n---\n/.exec(text); if (!m) return text;
  const fm = m[1].replace(/^stale:\n(?:[ \t]+.*\n?)+/m, "").replace(/\n+$/, "");
  const q = v => JSON.stringify(String(v));
  const add = entry ? `\nstale:\n  since: ${entry.since}\n  reason: ${q(entry.reason)}` + (entry.source ? `\n  source: ${q(entry.source)}` : "") : "";
  return "---\n" + fm + add + "\n---\n" + text.slice(m[0].length);
}
function readmeSet(text, h, val){ return block(text, h) ? setBlock(text, h, val) : text; }
async function renumber(scopeIds, files, ref, orig){
  // Nummern und Überschriften der Abschnitte und die Abschnittslisten der Kapitel-READMEs (wie scripts/sections.py renumber)
  const chs = chapters(), need = [];
  chs.forEach(c => { if (!scopeIds || scopeIds.includes(c.id)){ need.push(c.path + "/README.md"); c.sections.forEach(s => need.push(s.path)); } });
  const missing = need.filter(p => !(p in files)), got = await readAll(missing, ref); Object.assign(files, got); if (orig) missing.forEach(p => { if (!(p in orig)) orig[p] = got[p]; });
  chs.forEach((c, ci) => {
    if (scopeIds && !scopeIds.includes(c.id)) return;
    const rows = c.sections.map((s, si) => {
      let t = files[s.path]; if (t == null) return `| ${ci + 1}.${si + 1} | ${s.title} | \`${s.status || "planned"}\` |`;
      const h = front(t), num = `${ci + 1}.${si + 1}`;
      if (String(h.number) !== num){ t = t.replace(/^number: .*$/m, `number: "${num}"`).replace(new RegExp("^# " + String(h.number).replace(".", "\\.") + " ", "m"), `# ${num} `); files[s.path] = t; }
      return `| ${num} | ${s.title} | \`${h.status || "planned"}\` |`;
    });
    const rp = c.path + "/README.md"; let r = files[rp]; if (r == null) return;
    r = r.replace(/^# Kapitel \d+ /m, `# Kapitel ${ci + 1} `);
    const table = "| Nummer | Abschnitt | Status |\n|---|---|---|\n" + rows.map(x => x + "\n").join("");
    r = /^\| Nummer \| Abschnitt \| Status \|$/m.test(r) ? r.replace(/^\| Nummer \| Abschnitt \| Status \|\n\|---\|---\|---\|\n(?:\|.*\n)*/m, table) : r;
    files[rp] = r;
  });
  return files;
}
function changed(files, orig){ return Object.entries(files).filter(([p, c]) => c != null && c !== orig[p]).map(([path, content]) => ({path, content})); }

/* Abschnitt speichern */
async function saveSection(data){
  const x = allSecs().find(v => v.s.id === data.section_id); if (!x) return;
  const seen = S.secFile; busy("Wird gespeichert …");
  const netErr = e => !!(e && (e.code === "offline" || e.code === "server_unavailable"));
  const attempt = async local => {
    const work = local ? workOf(S.book) : await prepareWork();
    const cur = local ? {text:seen.text, sha:seen.sha} : await getFile(x.s.path, work, true);
    if (seen && seen.sha && cur.sha && seen.sha !== cur.sha && seen.text !== cur.text) throw {message:"Der Abschnitt wurde inzwischen an anderer Stelle geändert. Lade ihn neu (deine Eingaben vorher kopieren)."};
    const h = front(cur.text), ap = h.approvals || {};
    let md = cur.text;
    md = setBlock(md, "Ziel des Abschnitts", data.goal || ""); md = setBlock(md, "Kurzbeschreibung", data.summary || "");
    if (data.manuscript != null && data.manuscript.trim() !== msOf(cur.text)){
      if (ap.section) throw {message:"Der Abschnitt ist abgeschlossen. Den Text kannst du erst ändern, wenn du ihn wieder öffnest."};
      md = setBlock(md, "Manuskript", data.manuscript);
    }
    if (data.fact_check) md = setFact(md, data.fact_check);
    const files = md === cur.text ? [] : [{path:x.s.path, content:md}], what = `Abschnitt ${S.secNo} „${x.s.title}“ gespeichert`;
    const r = local ? await localCommit(files, what, {action:"section.update", seen:{[x.s.path]: cur.sha || null}, base:{[x.s.path]: cur.text}}) : await commit(files, what, {action:"section.update"});
    S.msg = savedMsg("Gespeichert.", r);
  };
  try {
    // ohne Netz (oder solange Älteres wartet) auf Grundlage des geladenen Stands lokal sichern; sonst wie bisher gegen den Arbeits-Branch
    const canLocal = !!(GW_PORTS.outbox && seen && seen.text != null);
    const local = canLocal && (GW_PORTS.outbox.offline() || await GW_PORTS.outbox.pending(S.book.branch));
    // Die App weiß erst nach dem ersten Fehlschlag, dass das Netz weg ist (WLAN ohne Internet, Funkloch): dann in jeder Vorstufe (Arbeits-Branch, frisches Lesen) auf die lokale Sicherung ausweichen (#744)
    try { await attempt(!!local); } catch (e) { if (local || !canLocal || !netErr(e)) throw e; await attempt(true); }
  } catch (e) { S.msg = failMsg(e); }
  show("section", x.s.id);
}

