/* ---------- Versionen im Kopf (#735) ----------
   Zeigt die Version dieser App und, sobald ein Repository offen ist, die GhostWriter-Version dieses Repositorys (ghostwriter-manifest.yml → version).
   Weichen beide ab, steht ein ruhiger Hinweis im Tooltip und die Anzeige ist gelb. Das Manifest wird nur gelesen; ist es nicht lesbar (offline, fremdes Repository), steht nur die App-Version da. */
const VER = {repo:"", ver:null};
function verParse(text){ const m = /^version:\s*["']?([0-9][0-9A-Za-z.\-+]*)/m.exec(String(text || "")); return m ? m[1] : null; }
const verMinor = v => String(v || "").split(".").slice(0, 2).join(".");
function verText(app, repo, name){
  const a = `App ${app}`; if (!name) return {text:a, title:`Web-App Version ${app}`, warn:false};
  if (!repo) return {text:`${a} · Repository ?`, title:`Web-App ${app}; GhostWriter-Version von ${name} nicht lesbar`, warn:false};
  const diff = verMinor(app) !== verMinor(repo);
  return {text:`${a} · Repository ${repo}`, title:diff ? `Web-App ${app}, GhostWriter im Repository ${repo}: Die Stände weichen ab. Prüfe, ob ein Update fehlt.` : `Web-App ${app}, GhostWriter im Repository ${repo}`, warn:diff};
}
async function verLoad(){
  const name = S.owner ? S.owner + "/" + S.repo : ""; VER.repo = name;
  if (!name){ VER.ver = null; return verShow(); }
  try { VER.ver = verParse((await GW_PORTS.git.getFile("ghostwriter-manifest.yml")).text); } catch (e) { VER.ver = null; }
  if (VER.repo === name) verShow();
}
function verShow(){
  const el = $("vers"); if (!el) return;
  const v = verText(APP_VERSION, VER.ver, VER.repo); el.textContent = v.text; el.title = v.title; el.classList.toggle("warn", v.warn);
  const g = document.getElementById && document.getElementById("gear"); if (g){ g.classList.toggle("warn", v.warn); if (v.warn) g.title = "Einstellungen · " + v.title; else g.title = "Einstellungen"; }
}
setInterval(() => { const name = S.owner ? S.owner + "/" + S.repo : ""; if (name !== VER.repo) verLoad(); }, 1500);
document.addEventListener("DOMContentLoaded", verShow); verShow();
/* Pfad am Handy: das letzte Glied bleibt sichtbar (vorne kürzen statt umbrechen, #743) */
{ const c = document.getElementById && document.getElementById("crumbs"); if (c && typeof MutationObserver !== "undefined") new MutationObserver(() => { c.scrollLeft = c.scrollWidth; }).observe(c, {childList:true, subtree:true}); }
function verRows(){ const v = verText(APP_VERSION, VER.ver, VER.repo); return [["Version dieser App", esc(APP_VERSION)], ["GhostWriter im Repository", VER.repo ? (VER.ver ? esc(VER.ver) : '<span class="dim">nicht lesbar</span>') : '<span class="dim">kein Repository geöffnet</span>'], ...(v.warn ? [["Hinweis", esc(v.title)]] : [])]; }
