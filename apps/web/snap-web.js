/* ---------- Offline-Bestand gelesener Dateien (#744, Teil 2) ----------
   Jede erfolgreich gelesene Textdatei eines Buchs wird auf diesem Gerät abgelegt (IndexedDB, Speicher „files“ der Datenbank „gw-web“). Nur bei einem Netzfehler
   liest getFile (s02-dateien.js) daraus; sonst bleibt alles wie bisher. Abgelegt wird nur Buchtext im Klartext mit Prüfsumme und Commit, nie der Token oder
   Antwort-Köpfe von GitHub. Bilder (Binärdaten) bleiben draußen. Beim Abmelden wird der Bestand gelöscht (clear), die Outbox nicht.
   Schlüssel: „<owner>/<repo>|<ref>|<pfad>“; der zuletzt gelesene Branch je Repository steht unter „<owner>/<repo>|meta“. */
const SNAP_MAX = 4000;   // Dateien je Gerät; ist es mehr, werden die ältesten verworfen
function snapStore(){
  if (typeof indexedDB === "undefined"){   // Rückfall (Tests, sehr alte Browser): nur im Arbeitsspeicher
    const m = new Map();
    return {mem:true, get:async k => m.get(k) || null, put:async e => { m.set(e.key, JSON.parse(JSON.stringify(e))); }, all:async () => [...m.values()], del:async k => { m.delete(k); }, clear:async () => { m.clear(); }};
  }
  const run = (mode, fn) => gwDb().then(d => new Promise((ok, no) => { const t = d.transaction("files", mode), q = fn(t.objectStore("files")); t.oncomplete = () => ok(q && q.result); t.onerror = () => no(t.error); t.onabort = () => no(t.error); }));
  return {mem:false, get:k => run("readonly", s => s.get(k)).then(r => r || null), put:e => run("readwrite", s => s.put(e)), all:() => run("readonly", s => s.getAll()).then(a => a || []), del:k => run("readwrite", s => s.delete(k)), clear:() => run("readwrite", s => s.clear())};
}
const SB = snapStore();
let snapPuts = 0;
async function snapPrune(){   // selten: älteste Dateien über SNAP_MAX hinaus entfernen (Meta-Einträge bleiben)
  const all = (await SB.all()).filter(e => !e.meta); if (all.length <= SNAP_MAX) return;
  all.sort((a, b) => a.t - b.t); for (const e of all.slice(0, all.length - SNAP_MAX)) await SB.del(e.key);
}
GW_PORTS.snap = {
  async put(repo, ref, path, f){
    if (!f || typeof f.text !== "string") return;
    try { await SB.put({key:repo + "|" + (ref || "") + "|" + path, repo, ref:ref || "", path, text:f.text, sha:f.sha || null, commit:f.commit || null, t:Date.now()}); if (++snapPuts % 100 === 0) await snapPrune(); } catch (e) {}
  },
  async get(repo, ref, path){ try { return await SB.get(repo + "|" + (ref || "") + "|" + path); } catch (e) { return null; } },
  async meta(repo){ try { return await SB.get(repo + "|meta"); } catch (e) { return null; } },
  async setMeta(repo, m){ try { await SB.put({key:repo + "|meta", meta:true, branch:m.branch, readRef:m.readRef, t:Date.now()}); } catch (e) {} },
  async clear(){ try { await SB.clear(); } catch (e) {} }
};
