/* ---------- Outbox: Änderungen, die nur auf diesem Gerät liegen (#662, #61) ----------
   Ohne Netz wird ein Abschnitt zuerst lokal gesichert (IndexedDB) und später hochgeladen. Nichts wird still überschrieben: Hat sich eine Datei auf GitHub
   inzwischen geändert, bleibt die lokale Fassung liegen und die Leiste meldet einen Konflikt (die Lösung folgt). Die Leiste oben ist nicht wegklickbar,
   solange etwas wartet; beim Verlassen der Seite fragt der Browser nach. Ein Eintrag: {id, repo, book:{branch, work_branch}, files:[{path, content}],
   message, action, seen:{path: Blob-Kennung|null}, created, state:"wartet"|"konflikt"|"fehler", error}. */
const OUTBOX_DAY = 24 * 3600 * 1000;
function outboxStore(){
  if (typeof indexedDB === "undefined"){            // Rückfall (Tests, sehr alte Browser): nur im Arbeitsspeicher, geht beim Neuladen verloren
    const m = new Map(); let n = 0;
    return {mem:true, all:async () => [...m.values()].sort((a, b) => a.id - b.id), put:async e => { if (!e.id) e.id = ++n; m.set(e.id, JSON.parse(JSON.stringify(e))); return e.id; }, del:async id => { m.delete(id); }};
  }
  const db = new Promise((ok, no) => { const r = indexedDB.open("gw-web", 1); r.onupgradeneeded = () => r.result.createObjectStore("outbox", {keyPath:"id", autoIncrement:true}); r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });
  const run = (mode, fn) => db.then(d => new Promise((ok, no) => { const t = d.transaction("outbox", mode), q = fn(t.objectStore("outbox")); t.oncomplete = () => ok(q && q.result); t.onerror = () => no(t.error); t.onabort = () => no(t.error); }));
  return {mem:false, all:() => run("readonly", s => s.getAll()).then(a => (a || []).sort((x, y) => x.id - y.id)), put:e => run("readwrite", s => s.put(e)), del:id => run("readwrite", s => s.delete(id))};
}
const OB = outboxStore();
const obNetDown = () => NET.online === false || NET.github === false;
const obRepo = () => S.owner ? S.owner + "/" + S.repo : "";
async function obMine(){ const r = obRepo(); return (await OB.all()).filter(e => !r || e.repo === r); }
function obPlace(path){   // verständlicher Ort einer Datei: „Abschnitt 2.1 …“, sonst der Pfad
  let hit = ""; try { chapters().forEach((c, ci) => (c.sections || []).forEach((s, si) => { if (s.path === path) hit = `Abschnitt ${ci + 1}.${si + 1} „${s.title}“`; })); } catch (e) {}
  return hit || path;
}
GW_PORTS.outbox = {
  offline: obNetDown,
  async pending(branch){ return (await OB.all()).some(e => e.repo === obRepo() && (!branch || e.book.branch === branch)); },
  async add(e){
    e.created = Date.now(); e.state = "wartet";
    await OB.put(e);
    try { if (navigator.storage && navigator.storage.persist) navigator.storage.persist(); } catch (x) {}   // Browser soll den Speicher nicht von selbst räumen
    await obRender();
    return (await OB.all()).length;
  },
  async overlay(branch){   // lokale Dateien dieses Buchs, ältere zuerst, damit spätere gewinnen
    const out = []; (await OB.all()).filter(e => e.repo === obRepo() && e.book.branch === branch).forEach(e => out.push(...e.files)); return out;
  },
  list: () => OB.all(),
  flush: obFlush
};
let OB_BUSY = false;
async function obFlush(){
  if (OB_BUSY || obNetDown() || !token()) return;
  const run = async () => {
    OB_BUSY = true;
    const home = {owner:S.owner, repo:S.repo, book:S.book}, blocked = new Set(), upPaths = new Set(); let done = 0, bookDone = new Set();
    try {
      for (const e of await OB.all()){
        if (e.state === "spaeter") continue;                                                // zur Klärung auf eigenem Branch abgelegt: hält nichts auf
        const [o, r] = e.repo.split("/");
        if (home.owner && home.owner + "/" + home.repo !== e.repo) continue;               // anderes Repository ist geöffnet: später
        if (blocked.has(e.repo + "|" + e.book.branch)) continue;                           // ein Konflikt hält spätere Änderungen am selben Buch an
        if (!home.owner){ S.owner = o; S.repo = r; }
        try {
          const b = {branch:e.book.branch, work_branch:e.book.work_branch || undefined}, work = await prepareWork(b);
          const todo = []; let conflict = "";
          for (const f of e.files){
            let remote = null; try { remote = await getFile(f.path, work, true); } catch (x) {}
            const was = e.seen[f.path];
            if (remote && remote.text === f.content) continue;                             // liegt schon so auf GitHub (etwa nach einem unklaren Fehler)
            if (was && remote && remote.sha !== was){
              // GitHub hat sich geändert: ohne Überschneidung (andere Absätze) von selbst zusammenführen, sonst Konflikt zur Entscheidung
              const base = e.base && e.base[f.path];
              if (typeof base === "string"){
                const chunks = merge3(base, f.content, remote.text);
                if (!m3Conflicts(chunks)){ f.content = m3Join(chunks, []); e.seen[f.path] = remote.sha; e.base[f.path] = remote.text; e.merged = true; await OB.put(e); todo.push(f); continue; }
              }
              conflict = f.path; e.conflict = {path:f.path, remote:{text:remote.text, sha:remote.sha}}; break;
            }
            todo.push(f);
          }
          if (conflict){ e.state = "konflikt"; e.error = obPlace(conflict); await OB.put(e); blocked.add(e.repo + "|" + e.book.branch); continue; }
          if (todo.length) await GW_PORTS.git.pushFiles(work, todo, e.message + (e.merged ? " (mit dem Stand auf GitHub zusammengeführt)" : ""), e.action);
          if (todo.length && !(await openPR(b))) { try { await GW_PORTS.git.createPR({head:work, base:b.branch, title:`GhostWriter: Änderungen für ${b.branch}`, body:"Angelegt mit " + GW_PORTS.agent + ". Übernahme ins Buch nur nach ausdrücklicher Bestätigung."}); } catch (x) {} }
          await OB.del(e.id); done++; bookDone.add(e.repo + "|" + e.book.branch); e.files.forEach(f => upPaths.add(f.path));
        } catch (err) {
          if (err && (err.code === "offline" || err.code === "server_unavailable" || err.code === "no_token")) break;   // später noch einmal
          e.state = "fehler"; e.error = errText(err); await OB.put(e); blocked.add(e.repo + "|" + e.book.branch);
        } finally { if (!home.owner){ S.owner = ""; S.repo = ""; } }
      }
    } finally { OB_BUSY = false; }
    if (done && home.book && bookDone.has(home.owner + "/" + home.repo + "|" + home.book.branch)){
      try { S.pr = await openPR(home.book).catch(() => S.pr); await loadBookData(S.pr ? workOf(home.book) : home.book.branch);
        // der offene Abschnitt beruht jetzt auf dem hochgeladenen Stand: Ausgangsstand auffrischen (sonst sähe die nächste Prüfung die eigene Änderung als fremd), Eingaben im Formular bleiben
        if (S.secFile && S.sec && upPaths.has(S.sec.path)) S.secFile = await getFile(S.sec.path, S.readRef, true).catch(() => S.secFile);
        if (["project", "chapter", "library"].includes(S.view)) show(S.view, S.view === "chapter" ? S.chap : undefined); } catch (x) {}
    }
    await obRender(done);
  };
  if (navigator.locks && navigator.locks.request) return navigator.locks.request("gw-outbox", {ifAvailable:true}, l => l ? run() : null);   // nur ein Tab lädt hoch
  return run();
}
async function obRender(justUploaded){
  const el = $("unsaved"); if (!el) return;
  const all = await OB.all(), n = all.length, v = typeof voiceCount === "function" ? await voiceCount() : 0;   // Sprachnotizen (voice-web.js): nur lokal, bis sie im Chat abgeschrieben sind
  try { document.title = (n ? `(${n}) ` : "") + "GhostWriter"; } catch (e) {}
  if (!n && !v){ el.hidden = true; el.textContent = ""; if (justUploaded){ const ok = $("net"); if (ok && ok.hidden){ ok.hidden = false; ok.className = "netbar"; ok.textContent = "Hochgeladen: alle Änderungen sind auf GitHub."; setTimeout(() => { if (ok.textContent.startsWith("Hochgeladen")){ ok.hidden = true; ok.textContent = ""; } }, 6000); } } return; }
  const bad = all.filter(e => e.state === "konflikt").length, later = all.filter(e => e.state === "spaeter"), err = all.filter(e => e.state === "fehler").length, old = all.some(e => Date.now() - e.created > OUTBOX_DAY);
  const places = [...new Set(all.flatMap(e => e.files.map(f => obPlace(f.path))))];
  const voiceLine = v ? `🎙 ${v === 1 ? "1 Sprachnotiz wartet" : v + " Sprachnotizen warten"} auf Abschrift – nur auf diesem Gerät. <button class="link" data-act="voice-open">Öffnen</button>` : "";
  const head = n ? `⬆ ${n === 1 ? "1 Änderung" : n + " Änderungen"} nur auf diesem Gerät – noch nicht hochgeladen` : voiceLine;
  const act = !n ? "" : obNetDown() ? " · Hochladen, sobald wieder Netz da ist." : ' · <button class="link" data-act="outbox-flush">Jetzt hochladen</button>';
  const fix = e => ` <button class="link" data-act="outbox-resolve" data-id="${e.id}">Konflikt lösen</button>`;
  const notes = [n ? voiceLine : "", bad ? `⚠ ${bad} ungelöster Konflikt: auf GitHub wurde dieselbe Stelle inzwischen anders geändert; nichts wurde überschrieben.` + all.filter(e => e.state === "konflikt").map(fix).join("") : "",
    later.length ? `⏸ ${later.length} Konflikt später zu lösen (lokaler Stand liegt auf dem Branch ${esc(later[0].branch || "")}).` + later.map(fix).join("") : "",
    err ? `⚠ ${err} nicht hochgeladen: ${esc(all.find(e => e.state === "fehler").error)}` : "",
    old ? "Diese Änderungen liegen seit mehr als 24 Stunden nur lokal. Bitte bald hochladen." : "",
    OB.mem ? "Dieser Browser hat keinen dauerhaften Speicher: Die Änderungen gehen beim Neuladen verloren." : ""].filter(Boolean);
  el.hidden = false; el.className = "unsavedbar";
  el.innerHTML = `<b>${head}</b>${act}${notes.length ? `<div class="sub">${notes.join("<br>")}</div>` : ""}${n ? `<details><summary>Betroffen</summary><ul>${places.map(p => `<li>${esc(p)}</li>`).join("")}</ul></details>` : ""}`;
}
window.addEventListener("beforeunload", ev => { if (document.title.startsWith("(")){ ev.preventDefault(); ev.returnValue = ""; } });
