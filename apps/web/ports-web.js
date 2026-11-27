/* ---------- Anschluss der eigenen Web-App (#662): GitHub-REST mit Fine-grained Token ----------
   Liefert dieselben Formen wie apps/claude/ports-claude.js (siehe dort der Kopfkommentar zu GW_PORTS). Der Token liegt nur in diesem Browser (localStorage),
   gilt für ein Repository und wird nie an etwas anderes als api.github.com gesendet. Fehler kommen als {code, status, message}. */
const API = "https://api.github.com", TOKEN_KEY = "gw.token";
const token = () => store.get(TOKEN_KEY) || "";
const encPath = p => String(p).split("/").map(encodeURIComponent).join("/");
const b64text = b64 => new TextDecoder().decode(Uint8Array.from(atob(String(b64).replace(/\s/g, "")), c => c.charCodeAt(0)));
const MIME = {jpg:"image/jpeg", jpeg:"image/jpeg", png:"image/png", gif:"image/gif", webp:"image/webp", svg:"image/svg+xml"};
const mimeOf = path => MIME[String(path).split(".").pop().toLowerCase()] || "image/jpeg";
function errText(e){
  if (typeof errLog === "function") errLog(e);   // fehler-web.js: bereinigt im Protokoll merken (für „Fehler melden“)
  const c = e && e.code, m = (e && e.message) || String(e);
  if (c === "no_token") return "Du bist nicht angemeldet. Trage einen GitHub-Token ein.";
  if (c === "offline") return "Keine Verbindung zu GitHub. Prüfe das Netz und versuche es noch einmal.";
  if (c === "server_unavailable") return "GitHub antwortet gerade nicht. Bitte gleich noch einmal versuchen.";
  if (c === "http_401") return "Der Token ist ungültig oder abgelaufen. Melde dich mit einem neuen Token an.";
  if (c === "http_403" && /rate limit/i.test(m)) return "GitHub hat die Anfragen für den Moment begrenzt. Bitte in einigen Minuten noch einmal versuchen.";
  if (c === "http_403") return "GitHub verweigert den Zugriff. Der Token braucht für dieses Repository „Contents“ und „Pull requests“ mit Lesen und Schreiben (zum Starten von Läufen zusätzlich „Actions“ mit Lesen und Schreiben).";
  if (c === "http_404") return "Nicht gefunden. Prüfe owner/repo und ob der Token genau dieses Repository enthält.";
  if (c === "http_409" || c === "http_422") return "GitHub hat die Änderung nicht angenommen: " + m.slice(0, 200);
  return "Fehler: " + m.slice(0, 300);
}
async function rest(method, path, body, accept){
  const t = token();
  if (!t) throw {code:"no_token", message:"Nicht angemeldet."};
  let res;
  try {
    res = await fetch(API + path, {method, cache:"no-store", body:body ? JSON.stringify(body) : undefined,
      headers:Object.assign({Authorization:"Bearer " + t, Accept:accept || "application/vnd.github+json", "X-GitHub-Api-Version":"2022-11-28"}, body ? {"Content-Type":"application/json"} : {})});
  } catch (e) { if (typeof netFailed === "function") netFailed(); throw {code:"offline", message:"Keine Verbindung zu GitHub."}; }
  const text = await res.text();
  if (!res.ok){
    let msg = ""; try { msg = (JSON.parse(text) || {}).message || ""; } catch (e) {}
    throw {code:res.status >= 500 ? "server_unavailable" : "http_" + res.status, status:res.status, message:msg || res.statusText || ("HTTP " + res.status), endpoint:typeof errEndpoint === "function" ? errEndpoint(method, path) : ""};
  }
  try { const x = res.headers && res.headers.get && res.headers.get("github-authentication-token-expiration"); if (x && typeof LAST_HDR !== "undefined") LAST_HDR.expires = x; } catch (e) {}
  if (accept && !/json/.test(accept)) return text;       // roher Text (Datei, Commit-Kennung)
  try { return text ? JSON.parse(text) : null; } catch (e) { return text; }
}
const commitMemo = new Map();   // Commit-Kennung je Referenz, wenige Sekunden (spart Anfragen beim Lesen vieler Dateien)
const forgetCommits = () => commitMemo.clear();
function commitOf(owner, repo, ref){
  const key = owner + "/" + repo + "@" + (ref || "HEAD"), hit = commitMemo.get(key);
  if (hit && Date.now() - hit.t < 4000) return hit.p;
  const p = rest("GET", `/repos/${owner}/${repo}/commits/${encPath(ref || "HEAD")}`, null, "application/vnd.github.sha").then(t => String(t).trim() || null).catch(() => null);
  commitMemo.set(key, {t:Date.now(), p});
  return p;
}
const repoBase = (o, r) => `/repos/${o || S.owner}/${r || S.repo}`;
const GW_PORTS = {
  agent: "GhostWriter Web-App",
  noChat: true,   // Stufe 1 (#662): ohne Chat-Seitenleiste
  report: {button: () => typeof errButton === "function" ? errButton() : ""},   // „Fehler melden“ unter Fehlermeldungen
  git: {
    async getFile(path, ref, o){
      o = o || {}; const base = repoBase(o.owner, o.repo), q = ref ? "?ref=" + encodeURIComponent(ref) : "";
      const [meta, commit] = await Promise.all([rest("GET", `${base}/contents/${encPath(path)}${q}`), commitOf(o.owner || S.owner, o.repo || S.repo, ref)]);
      if (!meta || Array.isArray(meta) || meta.type !== "file") throw {message:"Datei nicht lesbar: " + path};
      const text = meta.encoding === "base64" && typeof meta.content === "string" ? b64text(meta.content) : await rest("GET", `${base}/contents/${encPath(path)}${q}`, null, "application/vnd.github.raw+json");
      return {text, sha:meta.sha || null, commit};
    },
    async getBlob(path, ref){
      const base = repoBase(), meta = await rest("GET", `${base}/contents/${encPath(path)}${ref ? "?ref=" + encodeURIComponent(ref) : ""}`);
      if (!meta || Array.isArray(meta) || meta.type !== "file") return null;
      let b64 = meta.encoding === "base64" ? meta.content : "";
      if (!b64 && meta.sha){ const b = await rest("GET", `${base}/git/blobs/${meta.sha}`); b64 = b && b.encoding === "base64" ? b.content : ""; }
      return b64 ? {b64:String(b64).replace(/\s/g, ""), mime:mimeOf(path)} : null;
    },
    async listDir(path, ref){ const r = await rest("GET", `${repoBase()}/contents/${encPath(path)}${ref ? "?ref=" + encodeURIComponent(ref) : ""}`); return Array.isArray(r) ? r : []; },
    async listPRs(q){
      q = q || {}; const o = q.owner || S.owner;
      const r = await rest("GET", `${repoBase(o, q.repo)}/pulls?state=open&per_page=${q.perPage || 5}${q.head ? "&head=" + encodeURIComponent(o + ":" + q.head) : ""}${q.base ? "&base=" + encodeURIComponent(q.base) : ""}`);
      return Array.isArray(r) ? r : [];
    },
    async prCommits(nr){
      const r = await rest("GET", `${repoBase()}/pulls/${nr}/commits?per_page=100`);
      return (Array.isArray(r) ? r : []).map(c => ({sha:c.sha, message:(c.commit || {}).message || "", author:{date:((c.commit || {}).author || {}).date || "", name:((c.commit || {}).author || {}).name || ""}}));
    },
    async createBranch(name, from){
      const ref = await rest("GET", `${repoBase()}/git/ref/heads/${encPath(from)}`);
      await rest("POST", `${repoBase()}/git/refs`, {ref:"refs/heads/" + name, sha:ref.object.sha}); forgetCommits();
    },
    async createPR(p){ await rest("POST", `${repoBase()}/pulls`, {title:p.title, head:p.head, base:p.base, body:p.body}); },
    async mergePR(nr, o){
      o = o || {}; const body = {merge_method:"merge"};
      if (o.title) body.commit_title = o.title; if (o.expectedHeadSha) body.sha = o.expectedHeadSha;
      await rest("PUT", `${repoBase()}/pulls/${nr}/merge`, body); forgetCommits();
    },
    async updatePRBranch(nr){ await rest("PUT", `${repoBase()}/pulls/${nr}/update-branch`, {}); forgetCommits(); },
    async pushFiles(branch, files, message, action){
      const base = repoBase(), msg = message + "\n\n" + GW_PORTS.agent + (action ? `\nGhostWriter-Aktion: ${action}` : "");
      const ref = await rest("GET", `${base}/git/ref/heads/${encPath(branch)}`), head = ref.object.sha;
      const parent = await rest("GET", `${base}/git/commits/${head}`);
      const blobs = await Promise.all(files.map(f => rest("POST", `${base}/git/blobs`, {content:String(f.content), encoding:"utf-8"})));
      const tree = await rest("POST", `${base}/git/trees`, {base_tree:parent.tree.sha, tree:files.map((f, i) => ({path:f.path, mode:"100644", type:"blob", sha:blobs[i].sha}))});
      const commit = await rest("POST", `${base}/git/commits`, {message:msg, tree:tree.sha, parents:[head]});
      try { await rest("PATCH", `${base}/git/refs/heads/${encPath(branch)}`, {sha:commit.sha, force:false}); }
      catch (e) { if (e && e.status === 422) throw {code:"http_422", status:422, message:"Der Branch wurde inzwischen geändert. Lade neu und speichere noch einmal."}; throw e; }
      forgetCommits();
    },
    async me(){ const r = await rest("GET", "/user"); return (r && r.login) || ""; },
    async repoInfo(owner, repo){ return rest("GET", `/repos/${owner}/${repo}`).catch(() => null); },
    async dispatch(file, ref, inputs){ await rest("POST", `${repoBase()}/actions/workflows/${encodeURIComponent(file)}/dispatches`, {ref, inputs:inputs || {}}); },
    async listRuns(file, q){
      q = q || {};
      const r = await rest("GET", `${repoBase()}${file ? "/actions/workflows/" + encodeURIComponent(file) + "/runs" : "/actions/runs"}?per_page=${q.perPage || 15}${q.branch ? "&branch=" + encodeURIComponent(q.branch) : ""}${q.event ? "&event=" + q.event : ""}`);
      return ((r && r.workflow_runs) || []).map(x => ({id:x.id, name:x.name || x.display_title || "", status:x.status, conclusion:x.conclusion, url:x.html_url, created:x.created_at, branch:x.head_branch, event:x.event}));
    },
    async listReleases(n){
      const r = await rest("GET", `${repoBase()}/releases?per_page=${n || 6}`);
      return (Array.isArray(r) ? r : []).map(x => ({name:x.name || x.tag_name, tag:x.tag_name, url:x.html_url, pre:!!x.prerelease, date:x.published_at, assets:(x.assets || []).map(a => ({name:a.name, url:a.browser_download_url, size:a.size}))}));
    },
    async workflowState(file){   // ok | missing (Action fehlt im Buch) | forbidden (Token ohne Recht „Actions“)
      try { await rest("GET", `${repoBase()}/actions/workflows/${encodeURIComponent(file)}`); return "ok"; }
      catch (e) { return e && e.status === 404 ? "missing" : e && e.status === 403 ? "forbidden" : "unknown"; }
    },
    async listBranches(owner, repo, page){ const r = await rest("GET", `/repos/${owner}/${repo}/branches?per_page=100&page=${page || 1}`); return Array.isArray(r) ? r : []; }
  }
};
/* Startseite: Anmeldung mit Token, danach Repository wählen */
function connectView(){
  const t = token();
  const login = `<form id="fToken" style="display:flex;gap:8px;flex-wrap:wrap"><input class="in" id="tokenIn" type="password" style="flex:1 1 240px" placeholder="GitHub-Token (Fine-grained)" autocomplete="off"><button class="btn pri">Anmelden</button></form>
    <details class="dim" style="margin-top:14px" open><summary>Token anlegen</summary><ol><li>Auf GitHub unter <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">Settings → Developer settings → Fine-grained tokens</a> einen Token anlegen.</li><li><b>Repository access:</b> nur das eine Repository mit deinen Büchern.</li><li><b>Repository permissions:</b> „Contents“ und „Pull requests“ jeweils <i>Read and write</i>; zusätzlich „Actions“ <i>Read and write</i>, wenn du Läufe starten willst (Probedruck, Vorabfassung, Auschecken).</li><li>Token kopieren und hier einfügen. Er bleibt nur in diesem Browser gespeichert, unter „Abmelden“ löschst du ihn wieder.</li></ol></details>`;
  const repo = `<p class="dim" style="margin:0 0 10px">Angemeldet. <button class="link" data-act="logout">Abmelden</button></p>
    <form id="fConnect" style="display:flex;gap:8px;flex-wrap:wrap"><input class="in" id="repoIn" style="flex:1 1 240px" placeholder="owner/repo, z. B. chillyconcane/YAWA" value="${esc(store.get("gw.repo") || "")}" autocomplete="off"><button class="btn pri">Öffnen</button></form>`;
  $("app").innerHTML = `<div class="one"><div class="card"><div style="display:flex;gap:10px;align-items:center;margin-bottom:6px"><i class="ti ti-books" style="font-size:22px;color:#e8731c"></i><b style="font-size:20px">GhostWriter öffnen</b></div>
    <p class="dim" style="margin:0 0 14px">Deine GhostWriter-Bibliothek auf GitHub – mit denselben Ansichten wie im Chat, aber ohne Chat. Gelesen und gespeichert wird direkt über GitHub mit deinem Token.</p>
    ${msgBox()}${t ? repo : login}
    <p class="dim" style="margin:12px 0 0">Speichern legt Änderungen auf dem Arbeits-Branch ab und öffnet ein Änderungspaket. Ins Buch übernommen wird erst nach deiner Bestätigung. Fragen an eine KI gehen in dieser App noch nicht; dafür den Chat mit GhostWriter benutzen.</p></div></div>`;
}
