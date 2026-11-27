/* ---------- GitHub über den Konnektor ---------- */
function errText(e){
  const c = e && e.code, m = (e && e.message) || String(e);
  if (c === "server_not_connected") return "GitHub ist in deinem Claude-Konto nicht verbunden: claude.ai → Einstellungen → Konnektoren → github verbinden, dann die Seite neu laden.";
  if (c === "needs_reauth") return "Die GitHub-Verbindung ist abgelaufen. Verbinde github unter claude.ai → Einstellungen → Konnektoren neu.";
  if (c === "selection_required") return "Du hast mehrere GitHub-Konnektoren. Wähle in der Abfrage von Claude einen aus und versuche es erneut.";
  if (c === "not_in_manifest" || c === "approval_required" || c === "consent_required") return "Diese App darf GitHub noch nicht benutzen. Erlaube den Zugriff in der Abfrage von Claude („Weiter“) und versuche es erneut.";
  if (c === "blocked_by_policy") return "Deine Organisation erlaubt diesen GitHub-Zugriff nicht.";
  if (c === "server_unavailable") return "GitHub antwortet gerade nicht. Bitte gleich noch einmal versuchen.";
  if (/404|not found/i.test(m)) return "Nicht gefunden. Prüfe den Namen des Repositorys. Ist es privat, muss die GitHub-App „Claude Github MCP Connector“ auf dem Konto installiert sein, dem das Repository gehört: github.com/apps/claude-github-mcp-connector → Install → Repository freigeben.";
  if (/403|permission|forbidden/i.test(m)) return "GitHub verweigert den Zugriff. Die GitHub-App braucht Schreibrechte für dieses Repository.";
  return "Fehler: " + m.slice(0, 300);
}
const call = (tool, input) => S.mcp ? S.mcp.callTool(GH, tool, input, {cache:false}) : Promise.reject({code:"server_not_connected", message:"no mcp"});
function fileOf(res){
  let text = null, sha = null, commit = null;
  for (const b of (res && res.content) || []){
    if (b.type === "resource" && b.resource){ if (typeof b.resource.text === "string") text = b.resource.text; const m = /\/sha\/([0-9a-f]{40})\//.exec(b.resource.uri || ""); if (m) commit = m[1]; }
    else if (b.type === "text"){ const m = /SHA:\s*([0-9a-f]{40})/.exec(b.text); if (m) sha = m[1]; else if (text === null) text = b.text; }
  }
  return {text, sha, commit};
}
/* ---------- Anschlüsse (#662): alles, was die App von GitHub und von der KI braucht, geht über GW_PORTS ----------
   Die Ansichten und Abläufe kennen keinen Konnektor. Ein anderer Anschluss (eigene Web-App: GitHub-REST mit Token) liefert dieselben Formen:
   git.getFile(path, ref, {owner, repo}) → {text, sha, commit} · git.getBlob(path, ref) → {b64, mime}|null · git.listDir(path, ref) → [Eintrag]
   git.listPRs({head, base, perPage, owner, repo}) → [PR] (head/base als Branch-Namen) · git.prCommits(nr) → [Commit] · git.createBranch(name, from)
   git.createPR({head, base, title, body}) · git.mergePR(nr, {title, expectedHeadSha}) · git.updatePRBranch(nr) · git.pushFiles(branch, files, message, action)
   git.me() → Login|"" · git.repoInfo(owner, repo, full) → Repository|null · git.listBranches(owner, repo, seite) → [Branch]
   ai: S.sample (oder null) · store: localStorage · agent: Kennung in Commit-Nachrichten · noChat: true blendet die Chat-Seitenleiste aus · outbox (optional, nur die eigene Web-App): Änderungen ohne Netz lokal sichern, siehe apps/web/outbox-web.js */
const refOf = ref => ref ? (/^[0-9a-f]{40}$/.test(ref) ? ref : "refs/heads/" + ref) : "";
const arr = r => Array.isArray(r && r.payload) ? r.payload : [];
const GW_PORTS = {
  agent: "GhostWriter für Claude",
  git: {
    async getFile(path, ref, o){ o = o || {}; const input = {owner:o.owner || S.owner, repo:o.repo || S.repo, path}; if (ref) input.ref = refOf(ref); return fileOf(await call("get_file_contents", input)); },
    async getBlob(path, ref){ return blobOf(await call("get_file_contents", {owner:S.owner, repo:S.repo, path, ref:"refs/heads/" + ref})); },
    async listDir(path, ref){ const input = {owner:S.owner, repo:S.repo, path}; if (ref) input.ref = "refs/heads/" + ref; return arr(await call("get_file_contents", input)); },
    async listPRs(q){ q = q || {}; const o = q.owner || S.owner, input = {owner:o, repo:q.repo || S.repo, state:"open", perPage:q.perPage || 5};
      if (q.head) input.head = o + ":" + q.head; if (q.base) input.base = q.base; return arr(await call("list_pull_requests", input)); },
    async prCommits(nr){ return arr(await call("pull_request_read", {method:"get_commits", owner:S.owner, repo:S.repo, pullNumber:nr, perPage:100})); },
    async createBranch(name, from){ await call("create_branch", {owner:S.owner, repo:S.repo, branch:name, from_branch:from}); },
    async createPR(p){ await call("create_pull_request", {owner:S.owner, repo:S.repo, head:p.head, base:p.base, title:p.title, body:p.body}); },
    async mergePR(nr, o){ o = o || {}; const input = {owner:S.owner, repo:S.repo, pullNumber:nr, merge_method:"merge"};
      if (o.title) input.commit_title = o.title; if (o.expectedHeadSha) input.expectedHeadSha = o.expectedHeadSha; await call("merge_pull_request", input); },
    async updatePRBranch(nr){ await call("update_pull_request_branch", {owner:S.owner, repo:S.repo, pullNumber:nr}); },
    async pushFiles(branch, files, message, action){ await call("push_files", {owner:S.owner, repo:S.repo, branch, files, message:message + "\n\n" + GW_PORTS.agent + (action ? `\nGhostWriter-Aktion: ${action}` : "")}); },
    async me(){ const r = await call("get_me", {}); return (r.payload && r.payload.login) || ""; },
    async repoInfo(owner, repo, full){ const input = {query:`repo:${owner}/${repo}`}; if (full) input.minimal_output = false; const p = (await call("search_repositories", input)).payload;
      return p ? (Array.isArray(p) ? p[0] : (p.items || [])[0]) || null : null; },
    async listBranches(owner, repo, page){ const input = {owner, repo, perPage:100}; if (page) input.page = page; return arr(await call("list_branches", input)); }
  }
};
/* Startseite: wie sich die App mit GitHub verbindet (Claude: Konnektor; die eigene Web-App hat ihre eigene mit Token-Anmeldung) */
function connectView(){
  const warn = !S.ready ? `<p class="dim"><span class="spin"></span>Verbindung zu GitHub wird geprüft …</p>` : !S.mcp ? `<div class="note warn"><b>GitHub-Verbindung nicht verfügbar.</b> Diese App liest und speichert über deinen GitHub-Konnektor in Claude. Verbinde ihn unter claude.ai → Einstellungen → Konnektoren und öffne die App danach erneut.</div>` : "";
  $("app").innerHTML = `<div class="one"><div class="card"><div style="display:flex;gap:10px;align-items:center;margin-bottom:6px"><i class="ti ti-books" style="font-size:22px;color:#e8731c"></i><b style="font-size:20px">GhostWriter öffnen</b></div>
    <p class="dim" style="margin:0 0 14px">Deine GhostWriter-Bibliothek auf GitHub – mit denselben Ansichten wie im Chat. Gelesen und gespeichert wird über deinen GitHub-Konnektor, Claude arbeitet über dein eigenes Claude-Konto. Keine Tokens, keine Schlüssel.</p>
    ${warn}${msgBox()}
    <form id="fConnect" style="display:flex;gap:8px;flex-wrap:wrap"><input class="in" id="repoIn" style="flex:1 1 240px" placeholder="owner/repo, z. B. chillyconcane/YAWA" value="${esc(store.get("gw.repo") || "")}" autocomplete="off"><button class="btn pri" ${S.mcp ? "" : "disabled"}>Öffnen</button></form>
    <details class="dim" style="margin-top:14px"><summary>Einmalig einrichten</summary><ol><li>In claude.ai unter Einstellungen → Konnektoren den Konnektor <b>github</b> verbinden.</li><li>Für private Repositorys auf GitHub die App <a href="https://github.com/apps/claude-github-mcp-connector" target="_blank" rel="noopener">Claude Github MCP Connector</a> auf dem Konto installieren, dem das Repository gehört, und das Repository freigeben. Nur „autorisiert“ reicht nicht.</li><li>Beim ersten Öffnen fragt Claude, ob diese App GitHub benutzen darf – mit „Weiter“ bestätigen.</li></ol></details>
    <p class="dim" style="margin:12px 0 0">Speichern legt Änderungen auf dem Arbeits-Branch ab und öffnet ein Änderungspaket. Ins Buch übernommen wird erst nach deiner Bestätigung.</p></div></div>`;
}
