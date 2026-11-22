// Durchlauf der Claude-Web-App in jsdom mit echten Daten einer Bibliothek – ohne zu schreiben.
//
// Liest über `gh api` (eigene Anmeldung), fängt alle schreibenden Connector-Aufrufe ab und prüft,
// welche Dateien ein Commit enthalten würde. Claude selbst wird nachgestellt.
//
//   npm install --prefix /tmp/gw-claude-test jsdom@24 js-yaml@4
//   NODE_PATH=/tmp/gw-claude-test/node_modules GW_REPO=chillyconcane/YAWA [GW_BOOK=buch/…] \
//     node apps/claude/tests/app.test.cjs
//
// Abgefangene Commits landen in $GW_OUT (Vorgabe /tmp/gw-claude-test/out) als JSON zum Nachsehen.
"use strict";
const {JSDOM} = require("jsdom");
const fs = require("fs"), path = require("path"), {execFileSync} = require("child_process");

const APP = path.resolve(__dirname, "..");
const REPO = process.env.GW_REPO || "chillyconcane/YAWA", [OWNER, NAME] = REPO.split("/");
const OUT = process.env.GW_OUT || "/tmp/gw-claude-test/out";
fs.mkdirSync(OUT, {recursive: true});

const gh = p => JSON.parse(execFileSync("gh", ["api", p], {maxBuffer: 1e8, stdio: ["ignore", "pipe", "ignore"]}).toString());
const lib = JSON.parse(Buffer.from(gh(`repos/${REPO}/contents/library.json`).content, "base64").toString());
const BOOK = process.env.GW_BOOK || lib.books[0].branch;

let failed = 0;
const ok = (cond, text) => { console.log((cond ? "  ok   " : "  FEHLT ") + text); if (!cond) failed++; };

const html = fs.readFileSync(path.join(APP, "index.html"), "utf8")
  .replace(/<script src="https:\/\/cdnjs[^"]*js-yaml[^"]*"><\/script>/, () => "<script>" + fs.readFileSync(path.join(path.dirname(require.resolve("js-yaml")), "dist", "js-yaml.min.js"), "utf8") + "</script>")
  .replace('<script src="vendor/gw-lite.js"></script>', () => "<script>" + fs.readFileSync(path.join(APP, "vendor/gw-lite.js"), "utf8") + "</script>")
  // nur im Test: Zustand von außen erreichbar
  .replace("window.sendPrompt = text =>", "window.__S = () => S; window.__rc = () => renderChat(); window.sendPrompt = text =>");

const pushes = [], cache = {}, updates = [];
let staleWork = false;
// Nachgebildete Dateien (Aufträge, Laufdateien) über den echten Daten: Pfad → Text
const fake = {}, fakeBin = {};
const WRITES = ["push_files", "create_or_update_file", "create_pull_request", "create_branch", "merge_pull_request", "update_pull_request_branch"];
const mcp = {callTool: async (srv, tool, input) => {
  if (tool === "get_file_contents"){
    // Arbeits-Branch mit älterer research.yml nachbilden, bis die App ihn auf den Buchstand bringt
    if (staleWork && input.path === ".github/workflows" && /ghostwriter\//.test(input.ref || "")) return {content: [], payload: [{name: "research.yml", sha: "alt"}]};
    let ref = input.ref ? input.ref.replace("refs/heads/", "") : "main";
    if (ref.startsWith("ghostwriter/")) ref = ref.slice("ghostwriter/".length);   // Arbeits-Branch = Buchstand
    if (fakeBin[input.path]) return {content: [{type: "resource", resource: {uri: `repo://x/sha/${"a".repeat(40)}/contents/${input.path}`, mimeType: "image/jpeg", blob: fakeBin[input.path]}}, {type: "text", text: "successfully downloaded binary file (SHA: f)"}]};
    if (fake[input.path] != null) return {content: [{type: "resource", resource: {uri: `repo://x/sha/${"a".repeat(40)}/contents/${input.path}`, text: fake[input.path]}}, {type: "text", text: "successfully downloaded text file (SHA: f)"}]};
    const extra = Object.keys(fake).filter(f => f.startsWith(input.path + "/") && !f.slice(input.path.length + 1).includes("/")).map(f => ({name: f.split("/").pop(), path: f, type: "file", sha: "f"}));
    const key = `${input.owner}/${input.repo}|${ref}|${input.path}`;
    if (!cache[key]){ try { cache[key] = gh(`repos/${input.owner}/${input.repo}/contents/${encodeURI(input.path)}?ref=${encodeURIComponent(ref)}`); } catch (e) { if (!extra.length) throw {code: "tool_error", message: "404 Not Found"}; cache[key] = []; } }
    const j = cache[key];
    if (Array.isArray(j)) return {content: [], payload: j.filter(e => !extra.some(x => x.name === e.name)).concat(extra)};
    return {content: [{type: "resource", resource: {uri: `repo://x/sha/${"a".repeat(40)}/contents/${input.path}`, text: Buffer.from(j.content, "base64").toString("utf8")}}, {type: "text", text: `successfully downloaded text file (SHA: ${j.sha})`}]};
  }
  if (tool === "list_pull_requests" && staleWork) return {content: [], payload: [{number: 1, html_url: "https://example/pull/1", head: {sha: "a"}}]};
  if (tool === "list_pull_requests" || tool === "pull_request_read") return {content: [], payload: []};
  if (tool === "get_me") return {content: [], payload: {login: "test"}};
  if (tool === "search_repositories") return {content: [], payload: {items: [gh(`repos/${REPO}`)]}};
  if (tool === "list_branches") return {content: [], payload: gh(`repos/${input.owner}/${input.repo}/branches?per_page=100&page=${input.page || 1}`)};
  if (tool === "update_pull_request_branch"){ updates.push(input); staleWork = false; return {content: []}; }
  if (WRITES.includes(tool)){ if (tool === "push_files") pushes.push(input); return {content: []}; }
  throw {code: "tool_error", message: "im Test nicht nachgebildet: " + tool};
}};
let suggestPrompt = null;
const sample = async (hist, o) => {
  if (/schlägst Figuren vor/.test((hist[0] || {}).content || "")){   // Figuren aus dem Text: Antwort nachgestellt, Zitat aus dem echten Text
    suggestPrompt = hist[0].content;
    const body = suggestPrompt.split(/TEXT \(Teil[^\n]*\n\n/)[1] || "", mm = /### (\d+\.\d+) [^\n]*\n\n([^\n]{40,})/.exec(body), key = mm ? mm[1] : "1.1", quote = mm ? mm[2].slice(0, 30) : "";
    const t = "```json\n" + JSON.stringify({items: [
      {name: "Anna", aliases: [], role: "main", short: "Andere Zeile", age: "34", traits: [], sections: [key], evidence: [{where: key, quote}]},
      {name: "Clara", aliases: ["Frau K."], role: "supporting", short: "Nachbarin", age: "", traits: ["laut"], relations: [{to: "Anna", kind: "Freundin"}], sections: [key], evidence: [{where: key, quote}, {where: key, quote: "ein erfundenes Zitat, das nirgends steht"}]}]}) + "\n```";
    o.onText({text: t}); return {text: t};
  }
  const t = 'Vorschlag.\n<<<AKTION {"action":"view.project","label":"Zur Übersicht"} AKTION>>>\n<<<AKTION {"action":"approval.confirm","label":"Direkt freigeben"} AKTION>>>';
  o.onText({text: t}); return {text: t};
};

const dom = new JSDOM(html, {runScripts: "dangerously", url: "https://app.example/", beforeParse(w){
  w.claude = {use: async n => n === "mcp" ? mcp : n === "sample" ? sample : null};
  // Bildverarbeitung gibt es in jsdom nicht: Stubs, die Größe und Zuschnitt festhalten
  w.__draws = []; w.URL.createObjectURL = () => "blob:test"; w.URL.revokeObjectURL = () => {};
  w.Image = class { set src(v){ this.naturalWidth = 300; this.naturalHeight = 200; setTimeout(() => this.onload && this.onload(), 0); } };
  w.HTMLCanvasElement.prototype.getContext = function(){ const c = this; return {drawImage: (...a) => w.__draws.push({size: c.width, a})}; };
  w.HTMLCanvasElement.prototype.toDataURL = function(t){ return "data:image/jpeg;base64,STUB" + this.width; };
  w.crypto.subtle = require("crypto").webcrypto.subtle; w.TextEncoder = TextEncoder; w.scrollTo = () => {};
  w.addEventListener("error", e => { console.log("JS-Fehler:", e.message); failed++; });
}});
const w = dom.window, d = w.document, sleep = ms => new Promise(r => setTimeout(r, ms));
const note = () => (d.querySelector("#app .note") || {}).textContent || "";
const until = async (f, n = 400) => { for (let i = 0; i < n && !f(); i++) await sleep(250); return f(); };
const idle = () => until(() => !d.querySelector("#app .spin"));
async function send(prompt){ w.sendPrompt(prompt); await sleep(300); await idle(); await sleep(200); }
const gwa = (action, data) => "Test\n\n```gw\n" + JSON.stringify(Object.assign({action}, data || {})) + "\n```";
function lastPush(label){ const p = pushes[pushes.length - 1]; if (p) fs.writeFileSync(path.join(OUT, label + ".json"), JSON.stringify(p, null, 1)); return p; }
const paths = p => (p ? p.files.map(f => f.path) : []);

(async () => {
  console.log(`Bibliothek ${REPO}, Buch ${BOOK}`);
  await sleep(300);
  d.getElementById("repoIn").value = REPO;
  d.getElementById("fConnect").dispatchEvent(new w.Event("submit", {bubbles: true, cancelable: true}));
  ok(await until(() => d.querySelector("#gw .gw-book")), "Bücherregal");

  await send("x\n\n`gw:view.data`");
  ok(d.querySelector("#gw .gw-d") && /Bücher/.test(d.querySelector("#gw .gw-d").textContent), "Seite „Daten“");

  await send("x\n\n`gw:library.book.open branch=" + BOOK + "`");
  ok(await until(() => d.querySelector("#gw [data-id^='ch-']"), 600), "Projektübersicht");
  const S = w.__S(), chs = S.struct;
  ok(/ganzen Buch/.test((d.querySelector(".claude .ch-head p") || {}).textContent || ""), "Claude-Leiste in der Projektübersicht");

  // Chat: nur sichere Knöpfe
  d.querySelector(".claude .quick button").click(); await sleep(500);
  const btns = [...d.querySelectorAll(".msg.a [data-act=run]")].map(b => b.textContent.trim());
  ok(btns.length === 1 && /Übersicht/.test(btns[0]), "Chat-Knöpfe: nur Ansichten und Formulare (" + btns.join(", ") + ")");

  // Projektdaten: nur das geänderte Feld
  await send("x\n\n`gw:project.edit`");
  const before = pushes.length;
  d.getElementById("gw-author").value = (d.getElementById("gw-author").value || "") + " (Test)";
  d.getElementById("gw-save").click(); await sleep(300); await idle();
  const pp = pushes.length > before && lastPush("projektdaten");
  ok(pp && paths(pp).join() === "ghostwriter.yml", "Projektdaten: ein Commit nur mit ghostwriter.yml");

  // Kapitel anlegen nach Kapitel 1
  let n = pushes.length;
  await send(gwa("chapter.create", {title: "Testkapitel", summary: "Kurz", goal: "", position: 1}));
  const pc = pushes.length > n && lastPush("kapitel-anlegen");
  ok(pc && paths(pc).includes("ghostwriter.yml") && paths(pc).some(p => /\/README\.md$/.test(p)), "Kapitel anlegen: Gliederung und neue Kapitel-README");

  // Abschnitt anlegen am Anfang von Kapitel 1
  n = pushes.length;
  await send(gwa("section.create", {chapter_id: chs[0].id, title: "Test – Abschnitt", goal: "Ziel", summary: "", fact_check: "optional", position: 0}));
  const ps = pushes.length > n && lastPush("abschnitt-anlegen");
  ok(ps && paths(ps).some(p => /sections\/\d+-test-abschnitt\.md$/.test(p)), "Abschnitt anlegen: neue Abschnittsdatei");

  // Schreibfreigabe für den ersten Abschnitt ohne Freigabe
  const all = chs.flatMap(c => c.sections);
  let target = null;
  for (const s of all){ const t = Buffer.from(gh(`repos/${REPO}/contents/${encodeURI(s.path)}?ref=${encodeURIComponent(BOOK)}`).content, "base64").toString(); if (/^\s+writing:\s*false/m.test(t)){ target = s; break; } }
  if (target){
    await send(gwa("approval.open", {kind: "writing", section_id: target.id}));
    ok(d.querySelectorAll(".gw-ck").length > 0, "Freigabe-Formular mit Prüfliste");
    n = pushes.length;
    await send(gwa("approval.confirm", {kind: "writing", section_id: target.id}));
    const pa = pushes.length > n && lastPush("schreiben-erlauben");
    const ap = pa && pa.files.find(f => f.path === "approvals.yml");
    ok(ap && /kind: writing\n\s+id: \S+\n\s+action: granted/.test(ap.content) && paths(pa).includes(target.path), "Schreiben erlauben: Abschnitt und approvals.yml in einem Commit");
  } else console.log("  –    kein Abschnitt ohne Schreibfreigabe, Freigabe nicht geprüft");

  // Kapitelreihenfolge umkehren
  n = pushes.length;
  await send(gwa("chapter.reorder", {order: w.__S().struct.map(c => c.id).reverse()}));
  ok(pushes.length > n && lastPush("reihenfolge"), "Kapitelreihenfolge: ein Commit");

  // Recherche speichern (Claude-Ergebnis nachgestellt)
  const sec = all[0];
  await send("x\n\n`gw:view.section section_id=" + sec.id + "`");
  w.__S().chat.push({role: "user", content: "x", label: "Recherche · Sofort"},
    {role: "assistant", run: {task: "research", section_id: sec.id}, content: "Kurz.\n<<<RECHERCHE\n## Fragestellung und Suchumfang\n\nTest\n\n## Rechercheergebnisse\n\nA\nRECHERCHE>>>"});
  w.__rc();
  n = pushes.length;
  const save = d.querySelector("[data-act=saverun]"); ok(!!save, "Knopf „Recherche speichern“");
  if (save){ save.click(); await sleep(400); await idle(); }
  const pr = pushes.length > n && lastPush("recherche");
  ok(pr && paths(pr).some(p => /\/research\/[^/]+\/run-\d{3}\.md$/.test(p)) && /^Recherche für Abschnitt \d+\.\d+/.test(pr.message), "Recherche: Laufdatei und Commit-Nachricht");

  // Recherche mit Internet (#462): Auswahl, wenn ein Anbieter mit API eingestellt ist (Buch oder Bibliothek)
  const s2 = w.__S(); s2.cfg.ai_providers = {available: ["google"], services: {google: {access: "api", api_key_secret: "GEMINI_API_KEY"}}};
  await send("x\n\n`gw:view.section section_id=" + sec.id + "`"); await sleep(500);
  const card = d.querySelector('.gw-card[data-task="Recherche"]');
  const sch = card && card.querySelector('.gw-opt[data-mode="zeitgesteuert"]'), imm = card && card.querySelector('.gw-opt[data-mode="sofort"]');
  ok(sch && !sch.disabled && /Mit Internet/.test(sch.textContent) && imm && imm.disabled && /ohne Internet/.test(imm.textContent),
     "Abschnittssteuerung: „Mit Internet“ aktiv, „Sofort“ ohne Internet ausgegraut");
  if (sch){ sch.click(); await sleep(300); await idle(); }
  const web = d.querySelector("[data-act=webres]");
  ok(!!web && /Google Gemini/.test(note()) && !d.querySelector("[data-act=offres]"), "Recherche: Rückfrage vor dem Start mit Internet");
  n = pushes.length;
  staleWork = true;
  if (web){ w.__S().cfg.ai_providers = s2.cfg.ai_providers; web.click(); await sleep(400); await idle(); }
  ok(updates.length === 1 && updates[0].pullNumber === 1 && !staleWork, "Recherche mit Internet: veraltetes Änderungspaket wird auf den Buchstand gebracht");
  const pw = pushes.length > n && lastPush("recherche-internet");
  const rq = pw && pw.files.find(f => /\/research\/[^/]+\/request-\d{3}\.yml$/.test(f.path));
  ok(rq && paths(pw).length === 1 && /provider: google/.test(rq.content) && new RegExp("section_id: " + sec.id).test(rq.content) && /in der Warteschlange/.test(note()),
     "Recherche mit Internet: nur der Auftrag in einem Commit");

  // Warteschlange (#483): neues Format, mehrere Aufträge, Zustände, „Trotzdem starten“
  ok(rq && /^type: research$/m.test(rq.content) && /^requested_by: web-app$/m.test(rq.content), "Auftrag im neuen Format (type, requested_by)");
  const dir = rq ? rq.path.replace(/\/request-\d{3}\.yml$/, "") : "";
  const mineName = rq ? rq.path.split("/").pop().replace(".yml", "") : "";
  const checkNow = async () => { const b = d.querySelector("[data-act=webcheck]"); if (b){ b.click(); await sleep(400); await idle(); } return note(); };
  fake[`${dir}/${mineName}.yml`] = rq ? rq.content : "";
  fake[`${dir}/request-090.yml`] = `type: research\nsection_id: ${sec.id}\nrequested_at: "2026-11-22T20:00:00Z"\nwaiting: budget\n`;
  fake[`${dir}/request-091.yml`] = `type: research\nsection_id: ${sec.id}\nrequested_at: "2026-11-22T20:01:00Z"\nerror: Anbieter antwortet mit 404\nfailed_at: "2026-11-22T20:02:00Z"\n`;
  let t1 = await checkNow();
  ok(/Wartet bzw\. läuft/.test(t1) && /Wartet auf deine Bestätigung/.test(t1) && /Fehlgeschlagen:.*404/.test(t1)
     && d.querySelector("[data-act=webreslow]") && d.querySelector("[data-act=offres]"), "Nachsehen: wartet / wartet auf Bestätigung / fehlgeschlagen");
  n = pushes.length;
  const low = d.querySelector("[data-act=webreslow]"); if (low){ low.click(); await sleep(400); await idle(); }
  const pt = pushes.length > n && lastPush("trotzdem-starten");
  const cf = pt && pt.files[0];
  ok(cf && paths(pt).length === 1 && /request-090\.yml$/.test(cf.path) && /confirm_low_budget: true/.test(cf.content) && !/waiting:/.test(cf.content),
     "Trotzdem starten: bestätigt den wartenden Auftrag statt einen neuen anzulegen");
  delete fake[`${dir}/${mineName}.yml`];
  fake[`${dir}/run-099.md`] = `---\nid: run-099\ntype: research\nsection_id: ${sec.id}\nweb_research: true\nsearches: 4\nsources: 7\ncost: 0.01\nrequest: ${mineName}\n---\n\n# Recherchelauf 099\n`;
  t1 = await checkNow();
  ok(/Fertig:.*run-099.*7 Quellen/.test(t1) && /Fehlgeschlagen/.test(t1), "Nachsehen: fertiger Auftrag mit Laufdatei, übrige Zustände bleiben sichtbar");

  // Figuren: die Bibliothek hat (noch) keine, deshalb nachgebildet über den echten ghostwriter.yml
  {
    const realGy = Buffer.from(gh(`repos/${REPO}/contents/ghostwriter.yml?ref=${encodeURIComponent(BOOK)}`).content, "base64").toString();
    const withChars = realGy.replace(/^characters:.*\n(?:(?:[ -].*|)\n)*/m, "").replace(/^structure:/m,
      `characters:\n- id: char-anna\n  name: Anna\n  path: characters/char-anna.md\n- id: char-bruno\n  name: Bruno\n  path: characters/char-bruno.md\nstructure:`);
    const secOne = w.__S().struct[0].sections[0];
    fake["ghostwriter.yml"] = withChars;
    fake["characters/char-anna.md"] = '---\nid: char-anna\nname: Anna\nrole: main\nshort: Erzählerin\ntraits:\n- ruhig\nrelations:\n- to: char-bruno\n  kind: Bruder\n---\n\n# Anna\n\n## Beschreibung\n\nLangtext\n\n## Notizen\n\nNotiz\n';
    fake["characters/char-bruno.md"] = '---\nid: char-bruno\nname: Bruno\nrole: supporting\n---\n\n# Bruno\n\n## Beschreibung\n\n<Wer ist die Figur?>\n\n## Notizen\n';
    fake["reference-images/ref-img-001.yml"] = "id: ref-img-001\nstatus: approved\nfile: anna.jpg\nroles:\n- visual_reference\nlinks:\n- kind: person\n  id: char-anna\n";
    fake["reference-images/ref-img-002.yml"] = "id: ref-img-002\nstatus: draft\nfile: bruno.jpg\nroles:\n- visual_reference\nlinks:\n- kind: person\n  id: char-bruno\n";
    fake["reference-images/anna.jpg"] = "x"; fake["reference-images/bruno.jpg"] = "x"; fakeBin["reference-images/anna.jpg"] = "AAAA";
    await send("x\n\n`gw:library.book.open branch=" + BOOK + "`");
    ok(await until(() => d.querySelector("#gw [data-id^='ch-']"), 600) && !!d.getElementById("gw-chars"), "Projektübersicht: Knopf „Figuren (2)“");
    await send("x\n\n`gw:view.characters`");
    ok(d.querySelectorAll("#gw .gw-ch[data-id]").length === 2 && /Hauptfigur/.test(d.getElementById("gw-figuren").textContent) && /Erzählerin/.test(d.getElementById("gw-figuren").textContent), "Figurenliste mit Rolle und Satz");
    ok(d.querySelectorAll("#gw-figuren img[src^='data:image/jpeg']").length === 1 && /STUB80/.test(d.getElementById("gw-figuren").innerHTML), "Figurenliste: Profilbild nur bei freigegebenem Referenzbild (80 px)");
    ok(w.__draws.length >= 1 && w.__draws[0].a[1] === 50 && w.__draws[0].a[3] === 200, "Profilbild: quadratisch aus der Mitte zugeschnitten");
    await send("x\n\n`gw:view.character character_id=char-anna`");
    ok(/STUB192/.test(d.getElementById("gw-figur").innerHTML), "Figurenformular: Profilbild (192 px)");
    ok(d.getElementById("f-name").value === "Anna" && d.getElementById("f-short").value === "Erzählerin" && /Langtext/.test(d.getElementById("f-desc").value) && d.querySelectorAll(".gw-rel").length === 1, "Figurenformular mit Feldern und Beziehung");
    n = pushes.length;
    d.getElementById("f-short").value = "Neuer Satz";
    d.getElementById("gw-save").click(); await sleep(300); await idle();
    const pf = pushes.length > n && lastPush("figur-bearbeiten");
    const af = pf && pf.files.find(f => f.path === "characters/char-anna.md");
    ok(pf && paths(pf).join() === "characters/char-anna.md" && /short: Neuer Satz/.test(af.content) && /^# Anna$/m.test(af.content) && /## Beschreibung\n\nLangtext\n/.test(af.content) && /kind: Bruder/.test(af.content),
       "Figur speichern: nur die Figurendatei, Beschreibung und Beziehung bleiben");
    n = pushes.length;
    await send(gwa("character.update", {character_id: "char-anna", name: "Anna Neu", role: "main"}));
    const pr2 = pushes.length > n && lastPush("figur-umbenannt");
    const gy2 = pr2 && pr2.files.find(f => f.path === "ghostwriter.yml");
    ok(pr2 && gy2 && /- id: char-anna\n  name: "Anna Neu"\n  path: characters\/char-anna\.md/.test(gy2.content) && /id: char-bruno/.test(gy2.content) && gy2.content.includes(withChars.slice(withChars.indexOf("structure:"))),
       "Figur umbenennen: Name auch in ghostwriter.yml, Gliederung unverändert");
    n = pushes.length;
    await send(gwa("character.create", {name: "Ben Müller", role: "supporting"}));
    const pn = pushes.length > n && lastPush("figur-anlegen");
    const gy3 = pn && pn.files.find(f => f.path === "ghostwriter.yml"), nf = pn && pn.files.find(f => f.path === "characters/char-ben-mueller.md");
    ok(pn && gy3 && nf && /id: char-ben-mueller/.test(gy3.content) && /^role: supporting$/m.test(nf.content) && /^# Ben Müller$/m.test(nf.content), "Figur anlegen: neue Datei und Eintrag in ghostwriter.yml");
    // Figuren aus dem Text vorschlagen und übernehmen
    await send(gwa("character.suggest", {scope: "book"}));
    ok(await until(() => d.getElementById("gw-fv"), 120) && d.querySelectorAll("#gw-fv .card").length === 2, "Vorschlag: zwei Figuren aus dem Text");
    const fv = d.getElementById("gw-fv").textContent; if (process.env.GW_DEBUG) console.log("FV:", fv.replace(/\s+/g, " ").slice(0, 600));
    ok(/schon da: Anna/.test(fv) && [...d.querySelectorAll("#gw-fv .nm")].some(i => i.value === "Clara") && !/erfundenes Zitat/.test(fv), "Vorschlag: bekannte Figur erkannt, nicht belegte Fundstelle verworfen");
    n = pushes.length;
    d.getElementById("gw-apply").click(); await sleep(400); await idle();
    const pv = pushes.length > n && lastPush("figuren-vorschlag");
    const fc = pv && pv.files.find(f => f.path === "characters/char-clara.md"), fa = pv && pv.files.find(f => f.path === "characters/char-anna.md"), gv = pv && pv.files.find(f => f.path === "ghostwriter.yml"), fs1 = pv && pv.files.find(f => /sections\//.test(f.path));
    ok(pv && /\(1 neu, 1 ergänzt\)/.test(pv.message) && fc && /role: supporting/.test(fc.content) && /to: char-anna/.test(fc.content) && /kind: Freundin/.test(fc.content), "Übernehmen: neue Figur mit Beziehung");
    ok(fa && /age: '?34'?/.test(fa.content) && /short: Erzählerin/.test(fa.content) && !/Andere Zeile/.test(fa.content), "Übernehmen: bekannte Figur nur in leeren Feldern ergänzt");
    if (process.env.GW_DEBUG) console.log("PV:", pv && pv.files.map(f => f.path).join(", "));
    ok(gv && /id: char-clara/.test(gv.content) && fs1 && /^characters: \[[^\]]*char-clara[^\]]*\]$/m.test(fs1.content), "Übernehmen: Liste in ghostwriter.yml und Zuordnung im Abschnittskopf");
    n = pushes.length;
    await send(gwa("character.create", {name: "bruno", role: "main"}));
    ok(pushes.length === n && /gibt es schon/.test(note()), "Figur anlegen: doppelter Name wird abgelehnt");
  }

  // Hinweisdurchsicht: nur wenn das Buch eine hat (z. B. GW_BOOK=buch/krimi-sinabelkirchen)
  {
    let rev = []; try { rev = gh(`repos/${REPO}/contents/editorial?ref=${encodeURIComponent(BOOK)}`).filter(f => /^durchsicht-.+\.yml$/.test(f.name)).map(f => f.name); } catch (e) {}
    if (!rev.length) console.log("  –    keine Hinweisdurchsicht im Buch, nicht geprüft");
    else {
      const key = f => { const m = /^durchsicht-(.+?)(?:-(\d+))?\.yml$/.exec(f); return [m[1], +(m[2] || 1)]; };   // wie hinweise.dialog_order
      const file = "editorial/" + rev.sort((a, b) => { const p = key(a), q = key(b); return p[0] < q[0] ? -1 : p[0] > q[0] ? 1 : p[1] - q[1]; }).pop();
      const orig = Buffer.from(gh(`repos/${REPO}/contents/${file}?ref=${encodeURIComponent(BOOK)}`).content, "base64").toString(), yaml = require("js-yaml");
      const ents = dt => [...(dt.ohne_autor || []), ...(dt.autorenentscheidung || [])], od = yaml.load(orig), open = ents(od).filter(e => (e.entscheidung || "offen") === "offen" && !e.umgesetzt); if (process.env.GW_DEBUG) console.log("REVFILE:", file, ents(od).length, open.length);
      await send("x\n\n`gw:library.book.open branch=" + BOOK + "`");
      ok(await until(() => d.querySelector("#gw [data-id^='ch-']"), 600) && await until(() => d.querySelector("[data-act=review]"), 40), "Projektübersicht: Karte „Hinweisdurchsicht“"); if (process.env.GW_DEBUG) console.log("READREF:", w.__S().readRef, (d.querySelector("#app").textContent.match(/Hinweisdurchsicht[^.]*/) || [])[0]);
      d.querySelector("[data-act=review]").click();
      ok(await until(() => d.getElementById("gw-nr"), 120) && d.querySelectorAll("#gw-nr .it").length === ents(od).length, "Hinweisdurchsicht: eine Karte je Eintrag");
      if (open.length >= 2){
        const [e1, e2] = open;
        n = pushes.length;
        await send(gwa("notes_review.decide", {file, entry: e1.id, decision: "ja"}));
        await until(() => pushes.length > n, 40);
        const p1 = pushes.length > n && lastPush("durchsicht-ja"), c1 = p1 && p1.files[0];
        const diff = c1 ? c1.content.split("\n").map((l, i) => l === orig.split("\n")[i] ? null : l).filter(x => x !== null) : [];
        ok(p1 && p1.files.length === 1 && c1.path === file && c1.content.split("\n").length === orig.split("\n").length && diff.length <= 1 && /Hinweisdurchsicht: e-\d+ ja/.test(p1.message), "Entscheidung „ja“: nur die Durchsichtsdatei, höchstens eine Zeile geändert");
        n = pushes.length;
        const neu = "Neuer Satz: mit Doppelpunkt # und Raute – und\nzweiter Zeile.";
        await send(gwa("notes_review.decide", {file, entry: e2.id, decision: "geändert", new: neu}));
        await until(() => pushes.length > n, 40);
        const p2 = pushes.length > n && lastPush("durchsicht-geaendert"), c2 = p2 && p2.files[0], d2 = c2 && yaml.load(c2.content);
        const x1 = d2 && ents(d2).find(e => e.id === e1.id), x2 = d2 && ents(d2).find(e => e.id === e2.id);
        const others = d2 && ents(d2).filter(e => ![e1.id, e2.id].includes(e.id)).every(e => JSON.stringify(e) === JSON.stringify(ents(od).find(o => o.id === e.id)));
        ok(x2 && x2.entscheidung === "geändert" && x2.neu === neu && others, "Entscheidung „geändert“: eigene Fassung gespeichert, alle anderen Einträge unverändert");
        ok(x1 && x1.entscheidung === "ja", "Zweite Entscheidung baut auf der ersten auf (nichts überschrieben)");
        n = pushes.length;
        await send(gwa("notes_review.decide", {file, entry: e1.id, decision: "geändert"}));
        await sleep(300);
        ok(pushes.length === n && /eigene Fassung/.test(note()), "„geändert“ ohne eigene Fassung wird abgelehnt");
      } else console.log("  –    weniger als zwei offene Einträge, Entscheidungen nicht geprüft");
      await send(gwa("notes_review.plan", {file}));
      ok(/Umsetzen prüfen/.test(note()), "Umsetzen prüfen: Hinweise ohne Änderung");
    }
  }

  console.log(failed ? `\n${failed} Prüfung(en) fehlgeschlagen` : "\nAlles in Ordnung", "– Commits zum Nachsehen in", OUT);
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
