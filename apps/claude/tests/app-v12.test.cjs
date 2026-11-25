// Test der Claude-Web-App (v1.2, #597) mit einem nachgebildeten Repository aus tests/fixtures/adhs – ohne Netz und ohne Schreibzugriff.
// Prüft: Neu-Abschließen (#563), Erneut versuchen (#554/#596), Veraltet-Marken (#510/#592), Stufen der Hinweisdurchsicht (#570/#473).
//
//   npm install --prefix /tmp/gw-claude-test jsdom@24 js-yaml@4
//   NODE_PATH=/tmp/gw-claude-test/node_modules node apps/claude/tests/app-v12.test.cjs
"use strict";
const {JSDOM} = require("jsdom");
const fs = require("fs"), path = require("path"), crypto = require("crypto");

const APP = path.resolve(__dirname, ".."), FIX = path.resolve(APP, "../../tests/fixtures/adhs");
let failed = 0;
const ok = (cond, text) => { console.log((cond ? "  ok   " : "  FEHLT ") + text); if (!cond) failed++; };

// Dateien des Buchs im Speicher
const files = {};
(function walk(dir, rel){ for (const e of fs.readdirSync(dir, {withFileTypes: true})) { const p = rel ? rel + "/" + e.name : e.name; if (e.isDirectory()) walk(path.join(dir, e.name), p); else files[p] = fs.readFileSync(path.join(dir, e.name), "utf8"); } })(FIX, "");
const gy = require("js-yaml").load(files["ghostwriter.yml"]), ch1 = gy.structure.chapters[0], sec1 = ch1.sections[0], sec2 = ch1.sections[1];
files["library.json"] = JSON.stringify({books: [{branch: "main", title: "Test", status: "ready", work_branch: "ghostwriter/main"}]});
const sha = t => crypto.createHash("sha256").update(t).digest("hex");
const msOf = t => (/\n## Manuskript\n\n?([\s\S]*)$/.exec(t) || [, ""])[1].trim();
// Abschnitt 1 abgeschlossen, dann Text geändert -> Drift
files[sec1.path] = files[sec1.path].replace("section: false", "section: true").replace(/^status: .*$/m, "status: approved");
const oldMs = msOf(files[sec1.path]);
files["approvals.yml"] = `entries:\n  - kind: section\n    id: ${sec1.id}\n    action: granted\n    at: '2026-11-01T10:00:00+01:00'\n    by: test\n    commit: ${"b".repeat(40)}\n    note: content_sha256=${sha("anderer Text")}\n`;
// fehlgeschlagener Auftrag
const jobPath = `${ch1.path}/research/${sec2.id}/request-001.yml`;
files[jobPath] = `section_id: ${sec2.id}\nquestion: Wie war das?\nrequested_at: '2026-11-20T10:00:00+00:00'\nerror: Das Modell x ist nicht mehr verfügbar.\nfailed_at: '2026-11-21T10:00:00+00:00'\n`;
// Hinweisdurchsicht mit 14 Einträgen: 1 blockierend, 6 gleiches Muster (Gruppe), 6 einzelne, 1 gering
const ent = (i, o) => Object.assign({id: "H" + String(i).padStart(2, "0"), abschnitt: "1.1", art: "sprache", grund: "Grund " + i, alt: "alt" + i, neu: "neu" + i, entscheidung: "offen", schweregrad: "mittel", section_id: sec1.id}, o || {});
const auto = [ent(1, {schweregrad: "blockierend", neu: ""})];
for (let i = 2; i <= 7; i++) auto.push(ent(i, {muster: "Gleiches Muster"}));
for (let i = 8; i <= 13; i++) auto.push(ent(i, {art: "satzbau", grund: "Anderer Befund " + i + "x".repeat(i)}));
auto.push(ent(14, {schweregrad: "gering", art: "zeichensetzung", grund: "klein"}));
files["editorial/durchsicht-test.yml"] = require("js-yaml").dump({buch: "Test", erstellt: "2026-11-20", ohne_autor: auto, autorenentscheidung: []}, {lineWidth: 100, noArrayIndent: true});

const pushes = [];
const dirOf = p => { const under = Object.keys(files).filter(f => f.startsWith(p + "/")); const names = [...new Set(under.map(f => f.slice(p.length + 1).split("/")[0]))];
  return names.map(n => ({name: n, path: p + "/" + n, type: files[p + "/" + n] != null ? "file" : "dir", sha: "f"})); };
const mcp = {callTool: async (srv, tool, input) => {
  if (tool === "get_file_contents"){
    const p = input.path;
    if (/^[0-9a-f]{40}$/.test(input.ref || "")){ if (p === sec1.path) return {content: [{type: "resource", resource: {uri: `repo://x/sha/${"a".repeat(40)}/contents/${p}`, text: files[p].replace(/\n## Manuskript\n[\s\S]*$/, "\n## Manuskript\n\nEin ganz anderer alter Text.\n")}}]}; throw {message: "404"}; }
    if (files[p] != null) return {content: [{type: "resource", resource: {uri: `repo://x/sha/${"a".repeat(40)}/contents/${p}`, text: files[p]}}, {type: "text", text: "SHA: " + "c".repeat(40)}]};
    const d = dirOf(p); if (d.length) return {content: [], payload: d};
    throw {message: "404 not found"};
  }
  if (tool === "list_pull_requests" || tool === "pull_request_read") return {content: [], payload: []};
  if (tool === "get_me") return {content: [], payload: {login: "test"}};
  if (tool === "list_branches") return {content: [], payload: [{name: "main", commit: {sha: "c".repeat(40)}}]};
  if (tool === "search_repositories") return {content: [], payload: {items: [{default_branch: "main"}]}};
  if (tool === "push_files"){ pushes.push(input); (input.files || []).forEach(f => { files[f.path] = f.content; }); return {content: [], payload: {}}; }
  return {content: [], payload: {number: 1, html_url: "https://example/pull/1", head: {sha: "d".repeat(40)}}};
}};
const html = fs.readFileSync(path.join(APP, "index.html"), "utf8")
  .replace(/<script src="https:\/\/cdnjs[^"]*js-yaml[^"]*"><\/script>/, () => "<script>" + fs.readFileSync(path.join(path.dirname(require.resolve("js-yaml")), "dist", "js-yaml.min.js"), "utf8") + "</script>")
  .replace('<script src="vendor/gw-lite.js"></script>', () => "<script>" + fs.readFileSync(path.join(APP, "vendor/gw-lite.js"), "utf8") + "</script>")
  .replace("window.sendPrompt = text =>", "window.__S = () => S; window.sendPrompt = text =>");
const dom = new JSDOM(html, {runScripts: "dangerously", url: "https://app.example/", beforeParse(w){
  w.claude = {use: async n => n === "mcp" ? mcp : null};
  w.crypto.subtle = crypto.webcrypto.subtle; w.TextEncoder = TextEncoder; w.scrollTo = () => {};
  w.addEventListener("error", e => { console.log("JS-Fehler:", e.message); failed++; });
}});
const w = dom.window, d = w.document, sleep = ms => new Promise(r => setTimeout(r, ms));
const until = async (f, n = 200) => { for (let i = 0; i < n && !f(); i++) await sleep(100); return f(); };
const idle = () => until(() => !d.querySelector("#app .spin"));
const send = async prompt => { w.sendPrompt(prompt); await sleep(200); await idle(); await sleep(150); };
const gwa = (action, data) => "Test\n\n```gw\n" + JSON.stringify(Object.assign({action}, data || {})) + "\n```";
const txt = () => (d.querySelector("#app") || {}).textContent || "";

(async () => {
  await sleep(300);
  d.getElementById("repoIn").value = "t/buch";
  d.getElementById("fConnect").dispatchEvent(new w.Event("submit", {bubbles: true, cancelable: true}));
  ok(await until(() => d.querySelector("#gw [data-id^='ch-']"), 300), "Projektübersicht");

  // #563: geänderten Text neu abschließen
  await send(gwa("approval.open", {kind: "section", section_id: sec1.id}));
  ok(/Geänderten Text neu abschließen/.test(txt()) && !/bereits abgeschlossen/.test(txt()), "Neu abschließen: Titel, kein Hindernis");
  let n = pushes.length;
  await send(gwa("approval.confirm", {kind: "section", section_id: sec1.id}));
  const ap = files["approvals.yml"], acts = [...ap.matchAll(/action: (\w+)/g)].map(m => m[1]);
  ok(pushes.length === n + 1 && acts.slice(-2).join() === "revoked,granted", "Neu abschließen: revoked + granted in einem Commit (" + acts.join() + ")");
  ok(ap.includes("content_sha256=" + sha(oldMs)), "Neu abschließen: neuer Fingerabdruck");

  // #554/#596: erneut versuchen
  await send("x\n\n`gw:view.queue`");
  ok(/Erneut versuchen|Das Modell x/.test(txt()), "Warteschlange zeigt den fehlgeschlagenen Auftrag");
  n = pushes.length;
  await send(gwa("queue.retry", {request: jobPath}));
  ok(pushes.length === n + 1 && !/error:|failed_at:/.test(files[jobPath]) && /question: Wie war das\?/.test(files[jobPath]), "Erneut versuchen: error und failed_at weg, derselbe Auftrag");

  // #510/#592: Veraltet-Marke setzen, anzeigen, entfernen
  await send("x\n\n`gw:view.project`");
  n = pushes.length;
  await send(gwa("section.mark_stale", {section_id: sec2.id, reason: "Zeitzeugin widerspricht"}));
  ok(pushes.length === n + 1 && /^stale:\n  since: \d{4}-\d{2}-\d{2}\n  reason: "Zeitzeugin widerspricht"/m.test(files[sec2.path]) && /section: false/.test(files[sec2.path]), "Markieren: Kopf mit stale, Freigabe unberührt");
  ok(msOf(files[sec2.path]) === msOf(fs.readFileSync(path.join(FIX, sec2.path), "utf8")), "Markieren: Text unverändert");
  await send(gwa("view.project"));
  ok(/veraltet/.test(txt()), "Projektübersicht zeigt „veraltet“");
  await send(gwa("view.chapter", {chapter_id: ch1.id}));
  ok(/veraltet/.test(txt()), "Kapitelansicht zeigt „veraltet“");
  await send(gwa("view.section", {section_id: sec2.id}));
  ok(/Zeitzeugin widerspricht/.test(txt()), "Abschnittsformular nennt den Grund");
  n = pushes.length;
  await send(gwa("section.clear_stale", {section_id: sec2.id}));
  ok(pushes.length === n + 1 && !/^stale:/m.test(files[sec2.path]), "Entfernen: Kopf ohne stale");

  // Erneutes Abschließen entfernt die Marke (#510)
  await send(gwa("section.mark_stale", {section_id: sec1.id, reason: "Neu prüfen"}));
  ok(/^stale:/m.test(files[sec1.path]), "Abschnitt 1.1 markiert");
  files[sec1.path] = files[sec1.path].replace(/\n## Manuskript\n[\s\S]*$/, "\n## Manuskript\n\nNochmals geänderter Text.\n");   // Text weicht wieder ab
  await send(gwa("approval.confirm", {kind: "section", section_id: sec1.id}));
  ok(!/^stale:/m.test(files[sec1.path]) && /section: true/.test(files[sec1.path]), "Erneutes Abschließen entfernt die Veraltet-Marke");
  // Hinweisdurchsicht in Stufen (#570)
  await send(gwa("view.notes_review", {file: "editorial/durchsicht-test.yml"}));
  ok(/Stufe 1 · Blockierendes/.test(txt()) && !/Anderer Befund/.test(txt()), "Durchsicht: Stufe 1 zeigt nur Blockierendes");
  n = pushes.length;
  await send(gwa("notes_review.decide", {file: "editorial/durchsicht-test.yml", entry: "H01", decision: "nein"}));
  if (process.env.GW_DEBUG) console.log(txt().slice(0, 600), (d.querySelector("#app .note") || {}).textContent);
  ok(/Stufe 2 · Gleiche Muster · 1 Gruppen/.test(txt()), "Durchsicht: danach die Gruppe (" + (/Stufe[^·]*·[^·]*·[^·]*/.exec(txt()) || [""])[0] + ")");
  const gid = (/id: "?H02/.test(files["editorial/durchsicht-test.yml"]) && [...d.querySelectorAll("#gw [data-id]")].map(e => e.dataset.id).find(x => /^gruppe:/.test(x))) || "";
  ok(!!gid, "Durchsicht: Gruppenzeile mit gruppe:-ID");
  n = pushes.length;
  await send(gwa("notes_review.decide", {file: "editorial/durchsicht-test.yml", entry: gid, decision: "ja"}));
  const dd = require("js-yaml").load(files["editorial/durchsicht-test.yml"]);
  ok(pushes.length === n + 1 && dd.ohne_autor.slice(1, 7).every(e => e.entscheidung === "ja"), "Gruppe: alle 6 Einträge in einem Commit angenommen");
  ok(!/Stufe/.test(txt()) && /Anderer Befund/.test(txt()), "Durchsicht: unter 12 offenen Einträgen wieder die ganze Liste");
  console.log(failed ? `\n${failed} Fehler` : "\nalles ok");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.log("Abbruch:", e && e.message || e); process.exit(1); });
