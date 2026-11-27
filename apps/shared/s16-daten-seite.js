/* Letzte Läufe der Actions auf der Seite „Daten“: Anschlüsse, die Läufe lesen können (eigene Web-App), zeigen sie; sonst der Link zu GitHub */
async function dataRuns(own, rp){
  const all = {R_NAME:"Alle Läufe der Actions auf GitHub ansehen", R_STATE:"other", R_TEXT:"auf GitHub öffnen", R_URL:`https://github.com/${own}/${rp}/actions`};
  if (!GW_PORTS.git.listRuns) return [Object.assign({}, all, {R_NAME:"Läufe der Actions auf GitHub ansehen", R_TEXT:"in dieser App nicht abrufbar – auf GitHub öffnen"})];
  try {
    const rs = await GW_PORTS.git.listRuns(null, {perPage:6}), st = r => r.status !== "completed" ? ["other", "läuft"] : r.conclusion === "success" ? ["ok", "fertig"] : r.conclusion === "cancelled" ? ["other", "abgebrochen"] : ["fail", "fehlgeschlagen"];
    return rs.map(r => ({R_NAME:r.name || "Lauf", R_STATE:st(r)[0], R_TEXT:`${st(r)[1]} · ${deDate(String(r.created || "").slice(0, 10))}`, R_URL:r.url})).concat([all]);
  } catch (e) { return [Object.assign({}, all, {R_TEXT:"nicht lesbar (" + errText(e).slice(0, 70) + ") – auf GitHub öffnen"})]; }
}
/* Seite „Daten“ (wie render_view.py data; Läufe der Actions sind über den Konnektor nicht abrufbar) */
async function dataData(){
  const lib = S.lib || {}, prog = lib.program || {}, own = S.owner, rp = S.repo;
  const [repoR, brR, prR, upR] = await Promise.all([
    GW_PORTS.git.repoInfo(own, rp, true).catch(() => null),
    (async () => { const all = []; for (let pg = 1; pg <= 5; pg++){ const a = await GW_PORTS.git.listBranches(own, rp, pg); all.push(...a); if (a.length < 100) break; } return all; })().catch(() => null),
    GW_PORTS.git.listPRs({owner:own, repo:rp, perPage:100}).catch(() => null),
    (async () => { const [u, ref] = String(prog.upstream || "ploeffler/GhostWriter:main").split(":"); const [o, r] = u.split("/");
      const f = await GW_PORTS.git.getFile("ghostwriter-manifest.yml", ref || "main", {owner:o, repo:r}); return (window.jsyaml.load(f.text) || {}).version; })().catch(() => null)
  ]);
  const repo = repoR || null, pulls = prR || [];
  const size = repo && repo.size, sizeText = size == null ? "Größe unbekannt" : size >= 1024 ? (size / 1024).toFixed(1).replace(".", ",") + " MB" : size + " KB";
  const vis = repo ? (repo.private ? "privat" : "öffentlich") : "Sichtbarkeit unbekannt", brText = brR ? plural(brR.length, "Branch", "Branches") : "Zahl der Branches unbekannt";
  const vcmp = (a, b) => { const x = String(a || "").split(".").map(Number), y = String(b || "").split(".").map(Number); for (let i = 0; i < Math.max(x.length, y.length); i++){ const d = (x[i] || 0) - (y[i] || 0); if (d) return d; } return 0; };
  const upd = upR == null ? "nicht abgefragt" : vcmp(upR, prog.version) > 0 ? `neuere Version ${upR} verfügbar` : "aktuell";
  const books = (lib.books || []).map(b => {
    const pr = pulls.find(p => ((p.head || {}).ref) === b.work_branch), pending = b.pending || 0, ed = b.last_edition;
    return {B_TITLE:b.title || b.title_short || b.branch, B_BRANCH:b.branch, B_COMMIT_TEXT:[deDate(b.updated_at), b.last_commit || ""].filter(Boolean).join(" · "),
      B_PENDING_TEXT:pending ? `${plural(pending, "Änderung", "Änderungen")} ausstehend` + (pr ? ` · Änderungspaket #${pr.number}` : "") : "keine ausstehenden Änderungen", B_PENDING:pending ? "1" : "",
      B_AUTOMERGE_TEXT:"Änderungen sofort übernehmen: " + (b.auto_merge ? "an" : "aus"),
      B_EDITION_TEXT:ed ? `Auflage ${ed.number} vom ${deDate(ed.date)} (${ed.tag})` : "noch keine Auflage",
      B_PROOF_TEXT:"in dieser App nicht abrufbar", B_DATA_TEXT:`Datenstand ${b.data_version != null ? b.data_version : "?"}` + (b.migration_pending ? " – Umstellung ausstehend, kommt mit dem nächsten Update" : " – aktuell"),
      B_MIGRATION:b.migration_pending ? "1" : "", B_CHECK:"", B_CHECK_TEXT:"Prüfläufe in dieser App nicht abrufbar"};
  });
  const sec = lib.secrets, srows = (lib.secret_names || []).map(n => { const v = sec == null ? null : sec[n], st = v == null ? "unknown" : v ? "yes" : "no"; return {S_NAME:n, S_STATE:st, S_TEXT:{yes:"hinterlegt", no:"fehlt", unknown:"unbekannt"}[st]}; });
  const d = Object.assign(base(), {LIBRARY_NAME:own + "/" + rp,
    PROGRAM_VERSION_TEXT:`GhostWriter ${prog.version || "?"} · Hauptrepository ${prog.upstream || "?"}`, PROGRAM_UPDATE_TEXT:upd, PROGRAM_BEHIND:"",
    PROGRAM_LAST_UPDATE_TEXT:prog.last_update ? "letzter Update-Lauf am " + deDate(prog.last_update) : "noch kein Update-Lauf",
    PROGRAM_SKIPPED_TEXT:(prog.skipped_workflows || []).length ? "Workflow-Dateien übersprungen (Secret GHOSTWRITER_UPDATE_TOKEN fehlt): " + prog.skipped_workflows.join(", ") : "",
    UI_TEXT:`ghostwriter-ui ${prog.ui_version || "?"} · Commit ${String(prog.ui_commit || "").slice(0, 7)}`, GITHUB_KNOWN:repo || brR ? "1" : "",
    REPO_TEXT:`${vis} · ${sizeText} · ${brText}`, CLEANUP_URL:`https://github.com/${own}/${rp}/actions/workflows/cleanup.yml`, TASKS_URL:`https://github.com/${own}/${rp}/issues?q=is%3Aissue+is%3Aopen+L%C3%B6schaufgaben`, LIMITS_TEXT:"",
    BOOKS:books, SECRETS:srows,
    RUNS:await dataRuns(own, rp)});
  if (upR != null && vcmp(upR, prog.version) > 0) d.PROGRAM_UPDATE_TEXT += " – einspielen mit der Action „GhostWriter aktualisieren“ oder im Chat";
  return d;
}
