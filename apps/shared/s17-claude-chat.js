/* ---------- Claude ---------- */
const QUICK = {
  section:{"Stil und Lesbarkeit prüfen":"Prüf Stil und Lesbarkeit dieses Abschnitts nach den Schreibregeln. Nenne die wichtigsten Stellen mit kurzem Zitat und Verbesserungsvorschlag.",
    "Überarbeitung vorschlagen":"Schlag eine überarbeitete Fassung des Manuskripts vor, die den Schreibregeln folgt, und erkläre kurz die wichtigsten Änderungen.",
    "Anschluss an den vorigen Abschnitt prüfen":"Lies den vorigen Abschnitt und prüf, ob dieser Abschnitt inhaltlich und stilistisch gut daran anschließt (Figuren, Zeit, Ort, Ton). Nenne konkrete Stellen."},
  chapter:{"Was ist in diesem Kapitel offen?":"Was ist in diesem Kapitel noch offen? Sieh dir Bearbeitungsstand, Ziele und offene Marker der Abschnitte an und nenne die nächsten sinnvollen Schritte.",
    "Roten Faden prüfen":"Lies die Abschnitte dieses Kapitels (höchstens die ersten acht) und prüf, ob sie zum Ziel des Kapitels passen und gut aufeinander aufbauen. Nenne konkrete Stellen.",
    "Nächsten Abschnitt vorschlagen":"Welcher Abschnitt dieses Kapitels sollte als Nächstes bearbeitet werden, und warum? Biete ihn mit einem Knopf zum Öffnen an."},
  project:{"Wo stehe ich?":"Fass kurz zusammen, wo das Buch steht: wie viele Abschnitte in welchem Bearbeitungsstand, offenes Änderungspaket, was als Nächstes ansteht.",
    "Was soll ich als Nächstes tun?":"Schlag mir die zwei, drei sinnvollsten nächsten Schritte für dieses Buch vor und biete passende Knöpfe an.",
    "Gliederung prüfen":"Sieh dir die Gliederung an: Passen Reihenfolge und Titel der Kapitel und Abschnitte zueinander? Gibt es Lücken oder Doppelungen? Nur Vorschläge."}
};
const scopeOf = () => String(S.chatKey || "project").split(":")[0];
function skillLine(base){
  const sk = S.skills, names = sk && sk.list.length ? sk.list.map(x => x.dir).join(", ") : "";
  return esc(base) + (names ? `<br>Skills des Buchs: ${esc(names)}` : "") + (sk && sk.warn.length ? `<br><span style="color:var(--text-warning)">${esc(sk.warn.join(" · "))}</span>` : "");
}
function claudePanel(){
  const on = !!S.sample, sc = scopeOf();
  const what = {section:"Arbeitet mit dem geöffneten Abschnitt", chapter:`Arbeitet mit Kapitel ${(S.chap || 0) + 1}`, project:"Arbeitet mit dem ganzen Buch"}[sc];
  return `<aside class="claude" aria-label="Claude"><div class="ch-head"><b>Claude</b><p data-base="${esc(on ? what + " · über dein Claude-Konto" : "Claude ist in dieser Ansicht nicht verfügbar.")}">${skillLine(on ? what + " · über dein Claude-Konto" : "Claude ist in dieser Ansicht nicht verfügbar.")}</p></div>
  <div class="msgs" id="msgs"></div>
  <div class="quick">${Object.keys(QUICK[sc]).map(q => `<button data-q="${esc(q)}" ${on ? "" : "disabled"}>${esc(q)}</button>`).join("")}</div>
  <form class="ask" id="fAsk"><textarea class="in" id="askIn" rows="1" placeholder="Frage an Claude …" ${on ? "" : "disabled"}></textarea><button class="btn pri" aria-label="Senden" ${on ? "" : "disabled"}><i class="ti ti-send"></i></button></form></aside>`;
}
function md(t){
  const lines = esc(t).split("\n"), out = []; let list = null;
  const inl = s => s.replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<i>$2</i>");
  for (const l of lines){
    const li = /^\s*(?:[-*•]|\d+[.)])\s+(.*)/.exec(l);
    if (li){ if (!list){ list = /^\s*\d/.test(l) ? "ol" : "ul"; out.push(`<${list}>`); } out.push(`<li>${inl(li[1])}</li>`); continue; }
    if (list){ out.push(`</${list}>`); list = null; }
    if (/^#{1,6}\s/.test(l)) out.push(`<h4>${inl(l.replace(/^#+\s*/, ""))}</h4>`);
    else if (/^&gt;\s?/.test(l)) out.push(`<blockquote>${inl(l.replace(/^&gt;\s?/, ""))}</blockquote>`);
    else if (l.trim()) out.push(`<p>${inl(l)}</p>`);
  }
  if (list) out.push(`</${list}>`);
  return out.join("");
}
const PROPOSAL = /<<<MANUSKRIPT\n?([\s\S]*?)MANUSKRIPT>>>/;
function renderChat(){
  const box = $("msgs"); if (!box) return;
  box.innerHTML = S.chat.length ? S.chat.map((m, i) => {
    if (m.role === "user") return `<div class="msg u">${esc(m.label || m.content)}</div>`;
    const p = PROPOSAL.exec(m.content), res = /<<<RECHERCHE\n?([\s\S]*?)(RECHERCHE>>>|$)/.exec(m.content);
    let shown = m.content.replace(PROPOSAL, m.run ? "\n*(Entwurf für das Manuskript – mit „Als Entwurf speichern“ übernehmen oder erst ins Formular.)*\n" : "\n*(Vorschlag für das Manuskript – mit dem Knopf unten ins Formular übernehmen.)*\n");
    if (res) shown = shown.replace(/<<<RECHERCHE\n?/, "").replace(/RECHERCHE>>>/, "");
    const done = !S.busy && m.content;
    const runBtn = m.run && done && !m.saved && (m.run.task === "research" ? res && res[2] : p) ? `<button class="btn pri" data-act="saverun" data-i="${i}">${m.run.task === "research" ? "Recherche speichern" : "Als Entwurf speichern"}</button> ` : (m.saved ? '<span class="dim">Gespeichert.</span> ' : "");
    const acts = []; shown = shown.replace(ACTION_RE, (all, json) => { const a = safeAction(json); if (a) acts.push(a); return ""; }).replace(/<<<AKTION[\s\S]*$/, "");
    const actBtns = done ? acts.map(a => `<button class="btn" data-act="run" data-a="${esc(JSON.stringify(a))}"><i class="ti ti-arrow-right"></i> ${esc(a.label)}</button> `).join("") : "";
    return `<div class="msg a">${m.content ? md(shown) : '<span class="dim"><span class="spin"></span>Claude arbeitet …</span>'}${runBtn}${actBtns}${p && done && scopeOf() === "section" ? `<button class="btn" data-act="apply" data-i="${i}">Ins Formular übernehmen</button>` : ""}</div>`;
  }).join("") : `<p class="dim" style="margin:0">${scopeOf() === "section" ? "Frag Claude zum Abschnitt." : scopeOf() === "chapter" ? "Frag Claude zu diesem Kapitel." : "Frag Claude zum Buch – etwa wo du stehst oder was als Nächstes dran ist."} Claude ändert nichts selbst: Es schlägt vor und bietet Knöpfe an; gespeichert wird erst in den Formularen, mit deiner Bestätigung.</p>`;
  box.scrollTop = box.scrollHeight;
}
const ACTION_RE = /<<<AKTION\s*([\s\S]*?)\s*AKTION>>>/g;
const SAFE_ACTIONS = ["view.project", "view.chapter", "view.section", "view.data", "project.edit", "chapter.create.open", "chapter.edit.open", "section.create.open", "chapter.reorder.open", "section.reorder.open", "approval.open", "changes.merge.open", "run.start", "view.characters", "view.character", "character.suggest", "view.notes_review", "view.queue"];
function safeAction(json){
  // nur Ansichten und Formulare öffnen; alles, was schreibt, bestätigt der Benutzer danach im Formular
  let a; try { a = JSON.parse(json); } catch (e) { return null; }
  if (!a || !SAFE_ACTIONS.includes(a.action)) return null;
  if (a.action === "run.start") a.mode = "immediate";
  const ok = id => !id || allSecs().some(v => v.s.id === id) || chapters().some(c => c.id === id);
  if (!ok(a.section_id) || !ok(a.chapter_id)) return null;
  a.label = String(a.label || a.action).slice(0, 60); return a;
}
const ACTION_HELP = `Du kannst dem Benutzer Knöpfe anbieten, die eine Ansicht oder ein Formular öffnen. Schreib dafür je Knopf eine eigene Zeile:
<<<AKTION {"action":"…","label":"kurzer Knopftext", …Daten} AKTION>>>
Erlaubt: view.project; view.notes_review; view.queue; view.characters; view.character {character_id}; character.suggest {scope: book | Kapitelnummer | N.M}; view.chapter {chapter_id}; view.section {section_id}; project.edit; chapter.create.open; chapter.edit.open {chapter_id}; section.create.open {chapter_id}; chapter.reorder.open; section.reorder.open {chapter_id}; approval.open {kind:"writing"|"section", section_id, revoke?} bzw. {kind:"chapter", chapter_id, revoke?}; changes.merge.open; run.start {section_id, task:"research"|"writing"}. IDs nur aus buch_struktur. Knöpfe öffnen nur – gespeichert, freigegeben oder übernommen wird erst nach Bestätigung durch den Benutzer. Höchstens drei Knöpfe.
Will der Benutzer etwas ändern, anlegen, verschieben, freigeben, abschließen, recherchieren oder schreiben lassen, antworte nie nur, dass du das nicht kannst. Sag in einem Satz, dass er es über den Knopf öffnet und dort mit Speichern bestätigt, und biete den passenden Knopf an (für Manuskripttext: run.start mit task "writing" oder den Abschnitt mit view.section öffnen). Gibt es für den Wunsch keinen Knopf, sag das kurz und nenne die Ansicht, in der es am ehesten geht.`;
/* Skills des Buchs (#524, #535): die SKILL.md-Dateien unter .claude/skills als Anleitung für Claude in der App. Gelesen vom Lesestand, sonst vom
   Standard-Branch; gegen ghostwriter-skills.yml abgeglichen. Die App ist kein Chat mit Shell: Schritte mit Skripten oder Git
   führt sie über ihre Knöpfe aus, die Regeln (Skillauswahl, Auswahlfragen, verständliche Ausgaben, Qualitätssicherung, Grenzen) gelten. */
const sha256hex = async t => [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(t)))].map(x => x.toString(16).padStart(2, "0")).join("");
function skillParse(text){
  const m = /^---\n([\s\S]*?)\n---\n?/.exec(text), head = m ? (window.jsyaml.load(m[1]) || {}) : {}, body = m ? text.slice(m[0].length) : text;
  const cut = body.search(/^---\s*\n<p align/m), clean = (cut >= 0 ? body.slice(0, cut) : body).trim();
  const parts = clean.split(/^(?=## )/m), pre = parts[0], secs = parts.slice(1).map(x => ({n:(/^## (\d+)\./.exec(x) || [])[1] || "", text:x.trim()}));
  return {name:head.name || "", description:head.description || "", pre, secs, body:clean};
}
async function loadSkills(){
  const key = S.owner + "/" + S.repo + "|" + S.readRef; if (S.skillsFor === key) return S.skills;
  const out = {list:[], warn:[], personal:""};
  try {
    let dirs = (await listDir(".claude/skills", S.readRef)).filter(e => e.type === "dir").map(e => e.name), ref = S.readRef;
    if (!dirs.length){ dirs = (await listDefault(".claude/skills")).filter(e => e.type === "dir").map(e => e.name); ref = null; }
    const got = await pool(dirs, 4, async n => { const text = (await getFile(`.claude/skills/${n}/SKILL.md`, ref, true)).text; return Object.assign(skillParse(text), {dir:n, text, sha:await sha256hex(text)}); });
    out.list = got.filter(Boolean);
    let source = null; try { source = window.jsyaml.load((await getFile("ghostwriter-skills.yml", ref, true)).text) || null; } catch (e) {}
    if (source && source.skills){ const bad = out.list.filter(x => source.skills[x.dir] && source.skills[x.dir] !== x.sha).map(x => x.dir); if (bad.length) out.warn.push("Weichen von der Quelle ab: " + bad.join(", ")); }
    let prof = null; try { prof = window.jsyaml.load((await getFile("assistant.yml", S.readRef, true).catch(() => getFile("assistant.yml", null, true))).text) || null; } catch (e) {}
    out.personal = prof && prof.skill ? String(prof.skill) : "";
    if (out.personal && !out.list.some(x => x.dir === out.personal)) out.warn.push("Persönlicher Skill fehlt: " + out.personal);
  } catch (e) { /* ohne Skills arbeitet die App mit ihrer eigenen Anleitung */ }
  S.skills = out; S.skillsFor = key; return out;
}
function skillGuide(){
  const sk = S.skills; if (!sk || !sk.list.length) return "";
  const q = String(S.skillQuery || ""), by = n => sk.list.find(x => x.dir === n), used = [], blocks = [];
  const g = by("ghostwriter"), personal = sk.personal && by(sk.personal);
  if (personal){ used.push(personal.dir); blocks.push(`PERSÖNLICHER SKILL „${personal.dir}“ (Autor, Erzählstimme, Vorgaben; geht dem allgemeinen Skill vor)\n${personal.body.slice(0, 6000)}`); }
  if (!g){   // #569: den Skill „ghostwriter“ gibt es im Buch nicht mehr; die in der App geltenden Regeln stehen hier
    used.push("ghostwriter");
    blocks.push(`REGELN FÜR DIE APP (aus START.md)
Skillauswahl: Nenne zu Beginn einer Aufgabe in einem Satz, welchen Skill du verwendest (oder dass keiner passt); der persönliche Skill geht vor.
Auswahlfragen: Biete bei passenden Entscheidungen wenige verständliche Optionen und eine eigene Antwort an; dazwischen sprich frei, keine Durchklickstrecke.
Verständliche Ausgaben: Antworte im einfachen Modus in Alltagssprache und kurz, ohne unnötige Git-Fachbegriffe; Fehler, Risiken und ausstehende Freigaben nie verschweigen.
Qualitätssicherung: Lies vor dem Abschluss einer Schreib- oder Überarbeitungsaufgabe die ganze betroffene Einheit; prüfe Logik, Chronologie, Kontinuität, Perspektive, Ton und Sprache gegen die Projektvorgaben; vermeide KI-typische Muster (kein ankündigender Schlusssatz, keine zusammenfassenden Formeln, keine Moral am Absatzende); kein Pathos, nichts von anderen Autoren oder aus anderen Büchern übernehmen, Figuren in sexuellen Szenen immer eindeutig erwachsen; leite eine Freigabe nie aus einem Prüfergebnis ab.`);
  }
  if (g){
    used.push("ghostwriter");
    const pre = g.pre.split(/\n\n+/).filter(x => /^\*\*(Skillauswahl|Auswahlfragen)/.test(x.trim())).join("\n\n");
    const rest = g.secs.filter(x => ["7", "11"].includes(x.n)).map(x => x.text).join("\n\n");
    blocks.push(`SKILL „ghostwriter“ (nur die Regeln, die in der App gelten)\n${[pre, rest].filter(Boolean).join("\n\n").slice(0, 7000)}`);
  }
  const lek = by("ghostwriter-lektorat"), mem = by("ghostwriter-buchgedaechtnis");
  if (lek && /prüf|lektorat|korrektur|rundum|stil|sprache|struktur|lesbar|überarbeit/i.test(q)){ used.push(lek.dir); blocks.push(`SKILL „${lek.dir}“ (gilt für diese Anfrage)\n${lek.body.slice(0, 4000)}`); }
  if (mem && /kontinuit|widerspr|abgleich|figur|chronolog|fakt|gedächtnis|stimmt|passt zu/i.test(q)){ used.push(mem.dir); blocks.push(`SKILL „${mem.dir}“ (gilt für diese Anfrage)\n${mem.body.slice(0, 3000)}`); }
  return `\nANLEITUNG AUS DEN SKILLS DES BUCHS (verbindlich, geht deinen allgemeinen Gewohnheiten vor)
Du arbeitest in der GhostWriter-App, nicht in einem Chat mit Shell. Wo ein Skill Skripte, Git oder Dateien verlangt, tut die App das über ihre Knöpfe: du schlägst sie nur vor (siehe Knöpfe oben) und nennst keine Datei-, Skript- oder Werkzeugnamen. Die Regeln zu Skillauswahl, Auswahlfragen, verständlichen Ausgaben, Qualitätssicherung, Freigaben und Grenzen gelten unverändert. Nenne zu Beginn jeder Aufgabe in einem Satz, welchen Skill du verwendest (oder dass keiner passt): geladen sind ${sk.list.map(x => x.dir).join(", ")}; für diese Anfrage: ${used.join(", ") || "keiner"}.
${blocks.join("\n\n")}\n`;
}
function context(){
  const p = S.cfg.project || {}, sc = scopeOf();
  if (sc !== "section"){
    const prof = ["Titel: " + (p.title || p.working_title || S.book.title), "Autor: " + (p.author || ""), "Buchtyp: " + (p.book_type || ""), "Zielgruppe: " + (p.target_audience || ""), "Sprache: " + (p.language || "de"), "Beschreibung: " + (p.description || p.description_short || "")].filter(l => !/: $/.test(l)).join("\n");
    const c = sc === "chapter" ? chapters()[S.chap] : null;
    return `Du bist der Assistent in GhostWriter, einem Werkzeug für Buchprojekte auf GitHub. Antworte auf Deutsch, knapp, in Alltagssprache.
Regeln: Nenne keine Datei-, Feld- oder Werkzeugnamen (sag „Bearbeitungsstand“, „abschließen“, „Änderungspaket“). Behaupte nie, etwas gespeichert oder geändert zu haben. Erfinde keine Fakten über das Buch. Gib nie ein ganzes Kapitel oder Buch aus. Bearbeitungsstände: planned geplant, research Recherche, brainstorming Ideensammlung, ready_to_write bereit zum Schreiben, writing Schreiben, revision Überarbeitung, ready_for_approval bereit zum Abschluss, approved abgeschlossen, in_progress in Arbeit.
Mit buch_struktur siehst du die Gliederung (mit IDs), mit abschnitt_lesen liest du einen Abschnitt, mit kapitel_lesen Ziel und Kurzbeschreibung eines Kapitels.
${ACTION_HELP}
${skillGuide()}

BUCHPROFIL
${prof}
Offenes Änderungspaket: ${S.pr ? "#" + S.pr.number + " (noch nicht ins Buch übernommen)" : "keins"}
${c ? `
GEÖFFNETES KAPITEL ${S.chap + 1} „${c.title}“ (ID ${c.id}, Stand ${c.status})
Abschnitte: ${c.sections.map((s, si) => `${S.chap + 1}.${si + 1} ${s.title} [${s.status}] (ID ${s.id})`).join("; ") || "keine"}` : ""}`;
  }
  const t = S.secFile.text, cur = $("gw-ms") ? $("gw-ms").value : msOf(t);
  const prof = ["Titel: " + (p.title || S.book.title), "Buchtyp: " + (p.book_type || ""), "Zielgruppe: " + (p.target_audience || ""), "Sprache: " + (p.language || "de"), "Beschreibung: " + (p.description || "")].filter(l => !/: $/.test(l)).join("\n");
  return `Du bist der Schreibassistent in GhostWriter, einem Werkzeug für Buchprojekte auf GitHub. Antworte auf Deutsch, knapp, in Alltagssprache.
Regeln: Nenne keine Datei-, Feld- oder Werkzeugnamen (sag „Bearbeitungsstand“, „Freigabe“, „Änderungspaket“). Behaupte nie, etwas gespeichert oder geändert zu haben – du schlägst vor, gespeichert wird erst im Formular mit Bestätigung des Benutzers. Erfinde keine Fakten über das Buch; halte dich an Buchprofil, Schreibregeln und Text. Gib nie ein ganzes Kapitel oder Buch aus, höchstens einen Abschnitt.
Wenn du eine vollständige neue Fassung des Manuskripts dieses Abschnitts vorschlägst, setze NUR den Manuskripttext zwischen die Zeilen <<<MANUSKRIPT und MANUSKRIPT>>> (ohne Überschrift). Sonst keine solchen Marker.
Mit abschnitt_lesen kannst du andere Abschnitte lesen, mit buch_struktur die Gliederung sehen.
${ACTION_HELP}
${skillGuide()}

BUCHPROFIL
${prof}

SCHREIBREGELN DES BUCHS
${S.rules || "(keine eigenen Schreibregeln hinterlegt)"}

AKTUELLER ABSCHNITT ${S.secNo} „${S.sec.title}“
Ziel: ${($("gw-goal") && $("gw-goal").value) || part(t, "Ziel des Abschnitts") || "–"}
Kurzbeschreibung: ${($("gw-summary") && $("gw-summary").value) || part(t, "Kurzbeschreibung") || "–"}
Manuskript (Stand im Formular, ggf. noch nicht gespeichert):
${cur.slice(0, 40000)}`;
}
const TOOLS = [
  {name:"buch_struktur", description:"Gliederung des Buchs: Kapitel und Abschnitte mit Nummer, ID, Titel und Bearbeitungsstand.", inputSchema:{type:"object", properties:{}}, execute: async () => chapters().map((c, ci) => ({kapitel:ci + 1, id:c.id, titel:c.title, stand:c.status, abschnitte:(c.sections || []).map((s, si) => ({nummer:`${ci + 1}.${si + 1}`, id:s.id, titel:s.title, stand:s.status}))}))},
  {name:"kapitel_lesen", description:"Kurzbeschreibung und Ziel eines Kapitels, z. B. nummer 2.", inputSchema:{type:"object", properties:{nummer:{type:"number"}}, required:["nummer"]}, execute: async ({nummer}) => {
    const c = chapters()[Number(nummer) - 1]; if (!c) throw new Error("Kapitel " + nummer + " gibt es nicht.");
    const r = (await getFile(c.path + "/README.md", S.readRef).catch(() => ({text:""}))).text; return {nummer, id:c.id, titel:c.title, stand:c.status, kurzbeschreibung:part(r, "Kurzbeschreibung"), ziel:part(r, "Ziel des Kapitels")};
  }},
  {name:"abschnitt_lesen", description:"Liest Ziel, Kurzbeschreibung und Manuskript eines anderen Abschnitts, z. B. nummer \"2.3\".", inputSchema:{type:"object", properties:{nummer:{type:"string"}}, required:["nummer"]}, execute: async ({nummer}) => {
    const [a, b] = String(nummer).split(".").map(Number), c = chapters()[a - 1], s = c && (c.sections || [])[b - 1]; if (!s) throw new Error("Abschnitt " + nummer + " gibt es nicht.");
    const t = (await getFile(s.path, S.readRef)).text; return {nummer, titel:s.title, ziel:part(t, "Ziel des Abschnitts"), kurzbeschreibung:part(t, "Kurzbeschreibung"), manuskript:msOf(t).slice(0, 20000)};
  }}
];
async function chat(q, label){
  if (!S.sample || S.busy || !q.trim()) return;
  S.busy = true; S.skillQuery = q; S.chat.push({role:"user", content:q.trim(), label}); const a = {role:"assistant", content:"", run:S.pendingRun || null}; S.pendingRun = null; S.chat.push(a); renderChat();
  const hist = S.chat.slice(0, -1).map((m, i) => ({role:m.role, content: i === 0 ? context() + "\n\nANFRAGE:\n" + m.content : m.content}));
  try { const r = await S.sample(hist, {tools:TOOLS, cache:false, onText:({text}) => { a.content = text; renderChat(); }}); a.content = r.text || a.content; }
  catch (e) { a.content = e.code === "not_granted" ? "Claude ist für diese App nicht freigegeben." : e.code === "rate_limited" ? "Dein Claude-Kontingent ist gerade ausgeschöpft. Bitte später noch einmal versuchen." : "Claude konnte nicht antworten: " + (e.message || e); }
  S.busy = false; renderChat();
}

