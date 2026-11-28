/* Offline-Bestand (#744): Jede erfolgreich gelesene Datei wird auf dem Gerät abgelegt (GW_PORTS.snap, nur Buchtext, nie der Token). Nur bei einem Netzfehler
   (offline, GitHub nicht erreichbar) und nur für Lesezugriffe (`fresh` nicht gesetzt oder `allowStale` ausdrücklich) kommt der abgelegte Stand zurück,
   mit Zeitpunkt in S.stale. Schreibwege lesen mit `fresh` ohne `allowStale`: ein veralteter Stand gilt dort nie als frisch. */
const gwNetErr = e => !!(e && (e.code === "offline" || e.code === "server_unavailable"));
async function getFile(path, ref, fresh, allowStale){
  const key = (ref || "") + "|" + path, repo = S.owner + "/" + S.repo;
  if (!fresh && S.files.has(key)) return S.files.get(key);
  let f;
  try { f = await GW_PORTS.git.getFile(path, ref); }
  catch (e) {
    const old = gwNetErr(e) && (!fresh || allowStale) && GW_PORTS.snap ? await GW_PORTS.snap.get(repo, ref, path) : null;
    if (!old) throw e;   // nie gelesen oder kein Netzfehler: der Fehler bleibt
    f = {text:old.text, sha:old.sha, commit:old.commit, stale:old.t};
    S.stale = S.stale ? Math.min(S.stale, old.t) : old.t;   // ältester benutzter Stand, für den Hinweis in der Leiste
  }
  if (f.text === null) throw {message:"Datei nicht lesbar: " + path};
  if (!f.stale && GW_PORTS.snap) GW_PORTS.snap.put(repo, ref, path, f);   // nicht warten
  S.files.set(key, f);
  return f;
}
async function pool(items, n, fn){ const out = new Array(items.length); let i = 0; await Promise.all(Array.from({length:Math.min(n, items.length)}, async () => { while (i < items.length){ const k = i++; try { out[k] = await fn(items[k]); } catch (e) { out[k] = null; } } })); return out; }
const workOf = b => b.work_branch || "ghostwriter/" + b.branch;
async function openPR(b){
  const p = (await GW_PORTS.git.listPRs({head:workOf(b), base:b.branch}))[0] || null;
  return p ? {number:p.number, url:p.html_url, head:p.head && p.head.sha} : null;
}
async function prCommits(pr){
  try { pr.list = await GW_PORTS.git.prCommits(pr.number); pr.commits = pr.list.length || 1; } catch (e) { pr.list = []; pr.commits = 1; }
  return pr;
}

