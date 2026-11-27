/* ---------- Rollen je Buch (#762, #455) ----------
   Dieselben Regeln wie scripts/team.py role(): `team` in ghostwriter.yml ordnet GitHub-Logins eine Rolle zu (owner, editor, reader; Bearbeiter mit approve: true
   dürfen abschließen). Ohne `team` ist jeder mit Schreibrecht Eigentümer, wer nicht im Team steht, Leser. Die GitHub-Rechte begrenzen immer; eine Rolle erweitert
   sie nie (D03). Gemeinsame Testfälle mit der Python-Fassung: tests/data/rollen_faelle.json. `validate` setzt die Regeln auf GitHub ohnehin durch (team.py gate). */
const TEAM_ROLE_DE = {owner:"Eigentümer", editor:"Bearbeiter", reader:"Leser"};
const APPROVAL_ACTIONS = ["approval.open", "approval.confirm", "edition.create.open", "edition.create", "series.omnibus.approve", "series.omnibus.revoke", "series.omnibus.publish"];
// Aktionen, die schreiben (Änderungspaket, Warteschlange, Figuren, Reihenfolge …); Leser bekommen keine davon, Ansichten und Probedruck bleiben
const WRITE_ACTIONS = ["section.update", "project.edit", "project.update", "chapter.create.open", "chapter.create", "chapter.edit.open", "chapter.update", "section.create.open", "section.create",
  "chapter.reorder.open", "section.reorder.open", "chapter.reorder", "section.reorder", "changes.merge.open", "changes.merge", "queue.prioritize", "queue.cancel", "queue.retry",
  "section.mark_stale", "section.clear_stale", "notes_review.decide", "notes_review.ask", "notes_review.plan", "notes_review.apply", "character.suggest.apply", "character.series.update",
  "character.detach", "character.align", "character.adopt", "character.create", "character.update", "run.start"];
function teamRole(cfg, login, push){   // push: GitHub-Schreibrecht (true/false), null = unbekannt
  const entries = (cfg && cfg.team) || [], lc = String(login || "").toLowerCase();
  const entry = entries.find(e => String(e.github || "").toLowerCase() === lc) || null;
  let r, source;
  if (!entries.length){ r = "owner"; source = "ohne team"; } else if (entry){ r = entry.role; source = "team"; } else { r = "reader"; source = "nicht im team"; }
  let write = r === "owner" || r === "editor", approve = r === "owner" || (r === "editor" && !!(entry && entry.approve));
  if (push === false){ write = false; approve = false; }   // GitHub-Rechte begrenzen immer
  const git = write && entry && entry.name && entry.email ? {name:entry.name, email:entry.email} : null;
  const approvers = entries.filter(e => e.role === "owner" || (e.role === "editor" && e.approve)).map(e => e.name || e.github);
  return {login, role:r, role_text:TEAM_ROLE_DE[r] || r, source, write, approve, github_push:push, git, approvers,
    not_offered: approve ? [] : write ? APPROVAL_ACTIONS.slice() : ["alle Schreibaktionen"]};
}
function roleSummary(i){
  let who = `${i.login}: ${i.role_text}`; if (i.source === "ohne team") who += " (kein Team eingetragen)"; else if (i.source === "nicht im team") who += " (nicht im Team)";
  let rights = i.approve ? "schreiben und abschließen" : i.write ? "schreiben, nicht abschließen" : "nur lesen";
  if (i.github_push === false && i.role !== "reader") rights += " (ohne GitHub-Schreibrecht)";
  return `${who} – ${rights}`;
}
async function loadRole(){   // beim Öffnen eines Buchs; ohne bekannten Login (Chat-Platzhalter) keine Einschränkung
  S.role = null;
  try {
    const who = await login(); if (!who || who === "chat") return;
    const info = await GW_PORTS.git.repoInfo(S.owner, S.repo).catch(() => null);
    S.role = teamRole(S.cfg, who, info && info.permissions ? !!info.permissions.push : null);
  } catch (e) { S.role = null; }
}
function roleWhy(action){   // Grund, warum die Rolle die Aktion nicht erlaubt (leer = erlaubt)
  const r = S.role; if (!r || !action) return "";
  const noWrite = r.github_push === false && r.role !== "reader" ? "Dein GitHub-Zugang hat kein Schreibrecht an diesem Repository." : "Du hast in diesem Buch nur Leserechte (Rolle Leser).";
  if (!r.write && WRITE_ACTIONS.concat(APPROVAL_ACTIONS).includes(action)) return noWrite;
  if (!r.approve && APPROVAL_ACTIONS.includes(action)) return "Abschließen, wieder öffnen, Auflagen und Sammelbände dürfen nur Freigabeberechtigte" + (r.approvers && r.approvers.length ? ": " + r.approvers.join(", ") : "") + ".";
  return "";
}
function roleNote(){   // ein Satz in der Projektübersicht; nur bei einem Team oder fehlendem Schreibrecht
  const r = S.role; if (!r || (r.source === "ohne team" && r.write && r.approve)) return "";
  const rights = r.write ? (r.approve ? "" : " Abschließen und Auflagen dürfen nur Freigabeberechtigte" + (r.approvers.length ? " (" + r.approvers.map(esc).join(", ") + ")" : "") + ".") : " Schreibknöpfe sind ausgeblendet.";
  return `<div class="note info" style="margin-top:12px">Du arbeitest als <b>${esc(r.role_text)}</b>: ${esc(roleSummary(r).split(" – ")[1])}.${rights}</div>`;
}
function needWrite(){ const w = roleWhy("section.update"); if (w) throw {message:w + " Änderungen werden nicht gespeichert."}; }
