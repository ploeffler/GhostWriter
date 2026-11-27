/* ---------- Fehler melden ohne Chat (#662, Format nach #660) ----------
   Fehler, die die App zeigt (errText) oder die unbehandelt auftreten, landen bereinigt in einem kleinen Protokoll im Browser (letzte 30, nach Fingerabdruck
   zusammengefasst). „Fehler melden“ öffnet ein vorausgefülltes neues Issue im Hauptrepository; der Benutzer sieht den Text bei GitHub und schickt ihn selbst ab.
   Es gehen nur Technisches (Fehlerklasse, Programmversion, Schritt, bereinigte Meldung, Fingerabdruck, grober Browser) – kein Repository-, Branch-, Buchname,
   keine Pfade, keine Texte, keine Secrets. Gerätewerte nur grob und nur auf ausdrücklichen Wunsch. Die Arbeit geht nie verloren (liegt als „nur lokal“ in der Outbox). */
const APP_VERSION = "@@APP_VERSION@@", ERR_KEY = "gw.errors", ERR_MAX = 30, UPSTREAM_DEFAULT = "ploeffler/GhostWriter";
function errUpstream(){
  const u = String((S.lib && S.lib.program && S.lib.program.upstream) || "").split(":")[0];
  return /^[\w.-]+\/[\w.-]+$/.test(u) ? u : UPSTREAM_DEFAULT;
}
function errNames(){   // Namen aus dem geöffneten Repository, die nie in eine Meldung gehören
  const n = new Set([S.owner, S.repo]);
  ((S.lib && S.lib.books) || []).forEach(b => [b.branch, b.work_branch, b.title, b.title_short].forEach(v => v && n.add(v)));
  if (S.book) [S.book.branch, S.book.title, S.book.title_short].forEach(v => v && n.add(v));
  return [...n].filter(v => typeof v === "string" && v.length >= 3).sort((a, b) => b.length - a.length);
}
function errSanitize(t){
  let s = String(t == null ? "" : t);
  s = s.replace(/github_pat_\w+|gh[pousr]_\w+/g, "<token>").replace(/\S+@\S+\.\S+/g, "<e-mail>").replace(/https?:\/\/\S+/g, "<url>");
  errNames().forEach(n => { s = s.split(n).join("<name>"); });
  s = s.replace(/„[^“]*“/g, "„…“").replace(/"[^"]{3,}"/g, '"…"').replace(/«[^»]*»/g, "«…»");
  s = s.replace(/[\w.-]+(?:\/[\w.-]+)+/g, "<pfad>").replace(/[\w-]+\.(?:md|ya?ml|json|txt)\b/gi, "<datei>");
  return s.replace(/\s+/g, " ").trim().slice(0, 240);
}
function errEndpoint(method, path){   // Aufruf ohne Repository, Pfade und Kennungen: „PUT /repos/{o}/{r}/pulls/{n}/merge“
  return method + " " + String(path).split("?")[0].replace(/^\/repos\/[^/]+\/[^/]+/, "/repos/{o}/{r}").replace(/\/contents\/.*/, "/contents/{pfad}")
    .replace(/\/[0-9a-f]{40}\b/g, "/{sha}").replace(/\/(heads|refs\/heads)\/.*/, "/$1/{zweig}").replace(/\/commits\/(?!.*\/)(?!\{)[^/]+$/, "/commits/{ref}").replace(/\/\d+/g, "/{n}");
}
function errClass(e, kind){
  if (kind) return kind;
  const c = e && e.code;
  if (c === "offline") return "netz"; if (c === "server_unavailable") return "github-server"; if (c === "no_token" || c === "http_401") return "token";
  if (c === "http_403") return "rechte"; if (c === "http_404") return "nicht-gefunden"; if (c === "http_409" || c === "http_422") return "github-abgelehnt";
  return "app-fehler";
}
function errBrowser(){
  const u = (typeof navigator !== "undefined" && navigator.userAgent) || "", m = /(Edg|Firefox|Chrome|CriOS|FxiOS|Safari)\/(\d+)/.exec(u) || [];
  const os = /Android/.test(u) ? "Android" : /iPhone|iPad|iOS/.test(u) ? "iOS" : /Windows/.test(u) ? "Windows" : /Mac OS X/.test(u) ? "macOS" : /Linux/.test(u) ? "Linux" : "unbekannt";
  return (({Edg:"Edge", CriOS:"Chrome", FxiOS:"Firefox"})[m[1]] || m[1] || "unbekannt") + (m[2] ? " " + m[2] : "") + " · " + os;
}
function errHash(s){   // cyrb53: kurz und synchron; der Fingerabdruck muss nur gleiche Fehler gleich benennen, nicht kryptographisch sein
  let h1 = 0xdeadbeef, h2 = 0x41c6ce57;
  for (let i = 0; i < s.length; i++){ const c = s.charCodeAt(i); h1 = Math.imul(h1 ^ c, 2654435761); h2 = Math.imul(h2 ^ c, 1597334677); }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909); h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16).padStart(14, "0").slice(0, 12);
}
const errList = () => { try { const l = JSON.parse(store.get(ERR_KEY) || "[]"); return Array.isArray(l) ? l : []; } catch (e) { return []; } };
const errStore = l => { try { store.set(ERR_KEY, JSON.stringify(l.slice(0, ERR_MAX))); } catch (e) {} };
function errLog(e, info){
  info = info || {};
  try {
    const rec = {klasse:errClass(e, info.klasse), schritt:info.schritt || S.view || "start", endpoint:(e && e.endpoint) || info.endpoint || "", status:(e && e.status) || 0, meldung:errSanitize((e && e.message) || e)};
    rec.fp = errHash([rec.klasse, rec.endpoint, rec.status, rec.meldung].join("|"));
    const l = errList(), i = l.findIndex(x => x.fp === rec.fp);
    if (i >= 0){ rec.n = (l[i].n || 1) + 1; rec.erstmals = l[i].erstmals; l.splice(i, 1); } else { rec.n = 1; rec.erstmals = Date.now(); }
    rec.zuletzt = Date.now(); l.unshift(rec); errStore(l);
    return rec;
  } catch (x) { return null; }
}
function errIssueUrl(rec){
  const dev = store.get("gw.reportDevice") === "1" && typeof DEVICE_COARSE !== "undefined" && DEVICE_COARSE ? `\n**Gerät (grob, auf Wunsch):** ${DEVICE_COARSE}` : "";
  const body = `**Fehlerklasse:** ${rec.klasse}\n**Programm:** GhostWriter Web-App ${APP_VERSION}\n**Schritt:** ${rec.schritt}${rec.endpoint ? `\n**Aufruf:** \`${rec.endpoint}\`${rec.status ? " → " + rec.status : ""}` : ""}\n**Meldung:** \`${rec.meldung || "(keine)"}\`\n**Browser:** ${errBrowser()}${dev}\n**Fingerabdruck:** \`${rec.fp}\`\n**Häufigkeit:** ${rec.n}× auf diesem Gerät\n\n_Aus der Web-App erzeugt, ohne Repository-, Buch- oder Textinhalte; vor dem Absenden bitte kurz durchsehen._`;
  const title = `[Web-App] ${rec.klasse}: ${rec.meldung || rec.schritt}`.slice(0, 90);
  return `https://github.com/${errUpstream()}/issues/new?labels=bug&title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
}
function errReport(rec){ if (rec) window.open(errIssueUrl(rec), "_blank", "noopener"); }
/* Hinweis unter einer Fehlermeldung der Ansichten und bei unbehandelten Fehlern */
function errButton(){ const r = errList()[0]; return r ? ` <button class="link" data-act="err-report" data-fp="${esc(r.fp)}">Fehler melden</button>` : ""; }
function errToast(text){
  const el = $("errtoast"); if (!el) return;
  el.innerHTML = `<span>${esc(text)}</span> <button class="link" data-act="err-report-last">Fehler melden</button> <button class="link" data-act="err-close" aria-label="Schließen">×</button>`; el.hidden = false;
  clearTimeout(errToast.t); errToast.t = setTimeout(() => { el.hidden = true; }, 20000);
}
window.addEventListener("error", ev => { if (ev && ev.message){ if (errLog({message:ev.message}, {klasse:"js-fehler"})) errToast("Etwas ist schiefgelaufen. Deine Änderungen bleiben auf diesem Gerät erhalten."); } });
window.addEventListener("unhandledrejection", ev => { const r = ev && ev.reason; if (errLog(r && typeof r === "object" ? r : {message:String(r)}, {klasse:"unbehandelt"})) errToast("Etwas ist schiefgelaufen. Deine Änderungen bleiben auf diesem Gerät erhalten."); });
document.addEventListener("click", ev => {
  const b = ev.target.closest && ev.target.closest("[data-act]"); if (!b) return;
  const a = b.dataset.act;
  if (a === "err-close"){ const el = $("errtoast"); if (el) el.hidden = true; return; }
  if (a === "err-report" || a === "err-report-last"){ ev.preventDefault(); errReport(errList().find(x => x.fp === b.dataset.fp) || errList()[0]); }
});
